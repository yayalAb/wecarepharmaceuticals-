# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class WecareOriginalDocumentRequest(models.Model):
    _name = 'wecare.original.document.request'
    _description = 'Original Document Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'request_date desc, id desc'

    name = fields.Char(
        string='Request Reference',
        copy=False,
        readonly=True,
        default='New',
        tracking=True,
    )
    sales_order_id = fields.Many2one(
        'sale.order',
        string='Sales Order',
        required=True,
        tracking=True,
        domain="[('state', 'in', ('sale', 'done'))]",
        help='Sales order for which original documents are requested.',
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        related='sales_order_id.partner_id',
        store=True,
        readonly=True,
    )
    customer_reference = fields.Char(
        string='Customer Reference',
        compute='_compute_customer_reference',
        store=True,
        readonly=True,
    )

    @api.depends('sales_order_id', 'sales_order_id.client_order_ref',
                 'sales_order_id.invoice_ids.name', 'sales_order_id.invoice_ids.fs_no',
                 'sales_order_id.invoice_ids.state')
    def _compute_customer_reference(self):
        for req in self:
            so = req.sales_order_id
            if so and so.client_order_ref:
                req.customer_reference = so.client_order_ref
            elif so:
                invoices = so.invoice_ids.filtered(
                    lambda m: m.move_type == 'out_invoice' and m.state != 'cancel'
                )
                posted = invoices.filtered(lambda m: m.state == 'posted')
                inv = (posted or invoices)[:1]
                if inv:
                    fs = (getattr(inv, 'fs_no', False) or getattr(so, 'fs_no', False) or '').strip()
                    if fs == '/':
                        fs = ''
                    inv_no = (inv.name or '').strip()
                    if inv_no == '/':
                        inv_no = ''
                    parts = [p for p in [fs, inv_no] if p]
                    req.customer_reference = ' '.join(parts) if parts else ''
                else:
                    req.customer_reference = ''
            else:
                req.customer_reference = ''
    salesperson_id = fields.Many2one(
        'res.users',
        string='Salesperson',
        related='sales_order_id.user_id',
        store=True,
        readonly=True,
    )
    request_date = fields.Date(
        string='Request Date',
        required=True,
        default=fields.Date.context_today,
        tracking=True,
    )
    status = fields.Selection(
        [
            ('draft', 'Draft'),
            ('submitted', 'Submitted'),
            ('reviewed', 'Reviewed'),
            ('approved', 'Approved'),
            ('cancelled', 'Cancelled'),
        ],
        string='Status',
        default='draft',
        required=True,
        tracking=True,
        copy=False,
        index=True,
    )
    requested_person = fields.Many2one(
        'res.users',
        string='Requested Person',
        required=True,
        default=lambda self: self.env.user,
        tracking=True,
        help='User who requested the original documents.',
    )
    reviewer_id = fields.Many2one(
        'res.users',
        string='Reviewed By',
        readonly=True,
        copy=False,
        tracking=True,
    )
    review_date = fields.Date(
        string='Review Date',
        readonly=True,
        copy=False,
        tracking=True,
    )
    approver_id = fields.Many2one(
        'res.users',
        string='Approved By',
        readonly=True,
        copy=False,
        tracking=True,
    )
    approval_date = fields.Date(
        string='Approval Date',
        readonly=True,
        copy=False,
        tracking=True,
    )
    reason = fields.Text(
        string='Reason for Request',
        required=True,
        tracking=True,
        help='Reason why original documents are needed.',
    )
    notes = fields.Text(string='Internal Notes')
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        tracking=True,
    )

    @api.constrains('reason')
    def _check_reason_required(self):
        for req in self:
            if not req.reason or not req.reason.strip():
                raise ValidationError(self.env._('Reason for Request is required.'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'wecare.original.document.request'
                ) or 'New'
        return super().create(vals_list)

    def unlink(self):
        for req in self:
            if req.status in ('reviewed', 'approved'):
                raise UserError(self.env._(
                    'Requests in status "%s" cannot be deleted. Cancel the request instead.',
                    dict(req._fields['status'].selection).get(req.status)
                ))
        return super().unlink()

    def action_submit(self):
        for req in self:
            if req.status != 'draft':
                raise UserError(self.env._('Only draft requests can be submitted.'))
            req.write({'status': 'submitted'})
            req.message_post(body=self.env._(
                'Document request %s submitted by %s.',
                req.name,
                self.env.user.name,
            ))

    def action_review(self):
        for req in self:
            if req.status != 'submitted':
                raise UserError(self.env._('Only submitted requests can be reviewed.'))
            req.write({
                'status': 'reviewed',
                'reviewer_id': self.env.user.id,
                'review_date': fields.Date.context_today(self),
            })
            req.message_post(body=self.env._(
                'Document request reviewed by %s on %s.',
                self.env.user.name,
                fields.Date.context_today(self),
            ))

    def action_approve(self):
        for req in self:
            if req.status != 'reviewed':
                raise UserError(self.env._('Only reviewed requests can be approved.'))
            req.write({
                'status': 'approved',
                'approver_id': self.env.user.id,
                'approval_date': fields.Date.context_today(self),
            })
            req.message_post(body=self.env._(
                'Document request approved by %s on %s.',
                self.env.user.name,
                fields.Date.context_today(self),
            ))

    def action_reset_draft(self):
        for req in self:
            if req.status not in ('cancelled', 'submitted'):
                raise UserError(self.env._('Only submitted or cancelled requests can be reset to draft.'))
            req.write({
                'status': 'draft',
                'reviewer_id': False,
                'review_date': False,
                'approver_id': False,
                'approval_date': False,
            })
            req.message_post(body=self.env._('Document request reset to draft by %s.', self.env.user.name))

    def action_cancel(self):
        for req in self:
            if req.status == 'approved':
                raise UserError(self.env._('Approved requests cannot be cancelled directly.'))
            req.write({'status': 'cancelled'})
            req.message_post(body=self.env._('Document request cancelled by %s.', self.env.user.name))
