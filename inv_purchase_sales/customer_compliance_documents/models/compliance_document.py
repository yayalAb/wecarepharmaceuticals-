# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class CustomerComplianceDocument(models.Model):
    _name = 'customer.compliance.document'
    _description = 'Customer Compliance Document'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'expiry_date desc, id desc'
    _rec_name = 'display_name'

    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True,
        ondelete='cascade',
        index=True,
        tracking=True,
    )
    document_type_id = fields.Many2one(
        'customer.compliance.document.type',
        string='Document Type',
        required=True,
        tracking=True,
    )
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('submitted', 'Submitted'),
            ('approved', 'Approved'),
            ('cancelled', 'Cancelled'),
            ('renewed', 'Renewed'),
        ],
        string='State',
        default='draft',
        required=True,
        copy=False,
        index=True,
        tracking=True,
    )
    previous_document_id = fields.Many2one(
        'customer.compliance.document',
        string='Renewal Of',
        copy=False,
        readonly=True,
        ondelete='set null',
    )
    renewal_document_ids = fields.One2many(
        'customer.compliance.document',
        'previous_document_id',
        string='Renewals',
    )
    document_number = fields.Char(string='Document Number', tracking=True)
    issue_date = fields.Date(string='Issue Date', tracking=True)
    expiry_date = fields.Date(string='Expiry Date', required=True, tracking=True)
    status = fields.Selection(
        [
            ('valid', 'Valid'),
            ('expiring_soon', 'Expiring Soon'),
            ('expired', 'Expired'),
        ],
        string='Status',
        compute='_compute_status',
        store=True,
        index=True,
    )
    attachment = fields.Binary(string='Attachment', attachment=True)
    attachment_filename = fields.Char(string='Attachment Filename')
    remarks = fields.Text(string='Remarks')
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        related='partner_id.company_id',
        store=True,
        readonly=True,
    )
    display_name = fields.Char(compute='_compute_display_name', store=True)

    @api.depends('document_type_id', 'document_number', 'partner_id')
    def _compute_display_name(self):
        for doc in self:
            parts = []
            if doc.document_type_id:
                parts.append(doc.document_type_id.name)
            if doc.document_number:
                parts.append(doc.document_number)
            if doc.partner_id:
                parts.append(doc.partner_id.display_name)
            doc.display_name = ' - '.join(parts) if parts else _('Compliance Document')

    @api.depends('expiry_date')
    def _compute_status(self):
        today = fields.Date.context_today(self)
        for doc in self:
            if not doc.expiry_date:
                doc.status = 'expired'
                continue
            warning_days = doc._get_expiring_soon_days()
            threshold = today + relativedelta(days=warning_days)
            if doc.expiry_date < today:
                doc.status = 'expired'
            elif doc.expiry_date <= threshold:
                doc.status = 'expiring_soon'
            else:
                doc.status = 'valid'

    def _get_expiring_soon_days(self):
        self.ensure_one()
        company = self.company_id or self.env.company
        return company.compliance_expiring_soon_days or 30

    @api.constrains('issue_date', 'expiry_date')
    def _check_dates(self):
        for doc in self:
            if doc.issue_date and doc.expiry_date and doc.issue_date > doc.expiry_date:
                raise ValidationError(_(
                    'Issue Date cannot be after Expiry Date for document %(doc)s.',
                    doc=doc.display_name or doc.document_number or '',
                ))

    def is_acceptable_for_sales(self):
        """Approved Valid / Expiring Soon documents are acceptable for Sales Orders."""
        self.ensure_one()
        return self.state == 'approved' and self.status in ('valid', 'expiring_soon')

    # ------------------------------------------------------------------
    # Workflow
    # ------------------------------------------------------------------
    def _check_state(self, allowed, action):
        invalid = self.filtered(lambda d: d.state not in allowed)
        if invalid:
            raise UserError(_(
                'You cannot %(action)s document(s) in this state: %(docs)s',
                action=action,
                docs=', '.join(invalid.mapped('display_name')),
            ))

    def action_submit(self):
        self._check_state(('draft',), _('submit'))
        self.write({'state': 'submitted'})

    def action_approve(self):
        if not self.env.user.has_group('sales_team.group_sale_manager'):
            raise UserError(_('Only Sales Managers can approve compliance documents.'))
        self._check_state(('submitted',), _('approve'))
        self.write({'state': 'approved'})
        previous = self.mapped('previous_document_id').filtered(
            lambda d: d.state == 'approved')
        if previous:
            previous.write({'state': 'renewed'})

    def action_cancel(self):
        self._check_state(('draft', 'submitted', 'approved'), _('cancel'))
        self.write({'state': 'cancelled'})

    def action_draft(self):
        self._check_state(('submitted', 'cancelled'), _('reset to draft'))
        self.write({'state': 'draft'})

    def action_renew(self):
        """Open a new draft document; this one becomes Renewed once the new one is approved."""
        self.ensure_one()
        self._check_state(('approved',), _('renew'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Renew Compliance Document'),
            'res_model': 'customer.compliance.document',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_partner_id': self.partner_id.id,
                'default_document_type_id': self.document_type_id.id,
                'default_previous_document_id': self.id,
            },
        }

    @api.model
    def _cron_recompute_status(self):
        """Daily job so Valid → Expiring Soon → Expired flips with the calendar."""
        docs = self.search([])
        docs._compute_status()
        docs.mapped('partner_id')._compute_compliance_status()
