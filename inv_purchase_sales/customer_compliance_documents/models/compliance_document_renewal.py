# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class CustomerComplianceDocumentRenewal(models.Model):
    _name = 'customer.compliance.document.renewal'
    _description = 'Customer Compliance Document Renewal'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'renewal_date desc, id desc'

    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
    )
    document_id = fields.Many2one(
        'customer.compliance.document',
        string='Compliance Document',
        required=True,
        ondelete='cascade',
        index=True,
        tracking=True,
    )
    partner_id = fields.Many2one(
        related='document_id.partner_id',
        store=True,
        readonly=True,
    )
    document_type_id = fields.Many2one(
        related='document_id.document_type_id',
        store=True,
        readonly=True,
    )
    company_id = fields.Many2one(
        related='document_id.company_id',
        store=True,
        readonly=True,
    )
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('submitted', 'Submitted'),
            ('approved', 'Approved'),
            ('cancelled', 'Cancelled'),
        ],
        string='State',
        default='draft',
        required=True,
        copy=False,
        index=True,
        tracking=True,
    )
    renewal_date = fields.Date(
        string='Renewal Date',
        default=fields.Date.context_today,
        required=True,
        tracking=True,
    )
    user_id = fields.Many2one(
        'res.users',
        string='Requested By',
        default=lambda self: self.env.user,
        readonly=True,
    )
    approved_by_id = fields.Many2one('res.users', string='Approved By', readonly=True, copy=False)
    approved_date = fields.Datetime(string='Approved On', readonly=True, copy=False)
    remarks = fields.Text(string='Remarks')

    # Snapshot of the document before renewal (filled on create, kept as history)
    old_document_number = fields.Char(string='Previous Document Number', readonly=True)
    old_issue_date = fields.Date(string='Previous Issue Date', readonly=True)
    old_expiry_date = fields.Date(string='Previous Expiry Date', readonly=True)
    old_attachment = fields.Binary(string='Previous Attachment', attachment=True, readonly=True)
    old_attachment_filename = fields.Char(string='Previous Attachment Filename', readonly=True)

    # New values applied to the document on approval
    new_document_number = fields.Char(string='New Document Number', tracking=True)
    new_issue_date = fields.Date(string='New Issue Date', tracking=True)
    new_expiry_date = fields.Date(string='New Expiry Date', required=True, tracking=True)
    new_attachment = fields.Binary(string='New Attachment', attachment=True)
    new_attachment_filename = fields.Char(string='New Attachment Filename')

    @api.model
    def _snapshot_vals(self, document):
        return {
            'old_document_number': document.document_number,
            'old_issue_date': document.issue_date,
            'old_expiry_date': document.expiry_date,
            'old_attachment': document.attachment,
            'old_attachment_filename': document.attachment_filename,
        }

    @api.onchange('document_id')
    def _onchange_document_id(self):
        for renewal in self:
            if renewal.document_id:
                renewal.update(self._snapshot_vals(renewal.document_id))
                if not renewal.new_document_number:
                    renewal.new_document_number = renewal.document_id.document_number

    @api.model_create_multi
    def create(self, vals_list):
        self._check_group('renew', _('create'))
        Document = self.env['customer.compliance.document']
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'customer.compliance.document.renewal') or _('New')
            document = Document.browse(vals.get('document_id'))
            if document:
                # Readonly fields are not sent by the client: take the snapshot server-side.
                vals.update(self._snapshot_vals(document))
        return super().create(vals_list)

    @api.constrains('new_issue_date', 'new_expiry_date', 'old_expiry_date')
    def _check_dates(self):
        for renewal in self:
            if (renewal.new_issue_date and renewal.new_expiry_date
                    and renewal.new_issue_date > renewal.new_expiry_date):
                raise ValidationError(_('New Issue Date cannot be after New Expiry Date.'))
            if (renewal.old_expiry_date and renewal.new_expiry_date
                    and renewal.new_expiry_date <= renewal.old_expiry_date):
                raise ValidationError(_(
                    'New Expiry Date must be after the current Expiry Date (%(date)s).',
                    date=renewal.old_expiry_date,
                ))

    # ------------------------------------------------------------------
    # Workflow
    # ------------------------------------------------------------------
    def _check_state(self, allowed, action):
        invalid = self.filtered(lambda r: r.state not in allowed)
        if invalid:
            raise UserError(_(
                'You cannot %(action)s renewal(s) in this state: %(refs)s',
                action=action,
                refs=', '.join(invalid.mapped('name')),
            ))

    def _check_group(self, group, action):
        if not self.env.user.has_group('customer_compliance_documents.group_compliance_' + group):
            raise UserError(_('You are not allowed to %(action)s renewals.', action=action))

    def action_submit(self):
        self._check_group('submit', _('submit'))
        self._check_state(('draft',), _('submit'))
        self.write({'state': 'submitted'})

    def action_approve(self):
        """Apply the new values to the original document; this record keeps the history."""
        self._check_group('approve', _('approve'))
        self._check_state(('submitted',), _('approve'))
        for renewal in self:
            document = renewal.document_id
            if document.state not in ('approved', 'renewed'):
                raise UserError(_(
                    'Only approved documents can be renewed: %(doc)s.',
                    doc=document.display_name,
                ))
            # Refresh snapshot so history reflects the document exactly as replaced.
            renewal.write(self._snapshot_vals(document))
            doc_vals = {
                'issue_date': renewal.new_issue_date,
                'expiry_date': renewal.new_expiry_date,
                'state': 'renewed',
            }
            if renewal.new_document_number:
                doc_vals['document_number'] = renewal.new_document_number
            if renewal.new_attachment:
                doc_vals['attachment'] = renewal.new_attachment
                doc_vals['attachment_filename'] = renewal.new_attachment_filename
            document.write(doc_vals)
            document.message_post(body=_(
                'Document renewed by %(ref)s: expiry %(old)s → %(new)s.',
                ref=renewal.name,
                old=renewal.old_expiry_date,
                new=renewal.new_expiry_date,
            ))
            renewal.write({
                'state': 'approved',
                'approved_by_id': self.env.user.id,
                'approved_date': fields.Datetime.now(),
            })

    def action_cancel(self):
        self._check_state(('draft', 'submitted'), _('cancel'))
        self.write({'state': 'cancelled'})

    def action_draft(self):
        self._check_group('reset_draft', _('reset to draft'))
        self._check_state(('submitted', 'cancelled'), _('reset to draft'))
        self.write({'state': 'draft'})

    def unlink(self):
        if self.filtered(lambda r: r.state == 'approved'):
            raise UserError(_('Approved renewals are history and cannot be deleted.'))
        return super().unlink()
