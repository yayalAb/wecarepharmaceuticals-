# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

CHEQUE_METHODS = ('cheque', 'pdc', 'check_printing', 'check')


class WecareChequeRegister(models.Model):
    _name = 'wecare.cheque.register'
    _description = 'Cheque Register'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'received_date desc, id desc'

    collection_no = fields.Char(
        string='Collection No.',
        copy=False,
        readonly=True,
        default='New',
        tracking=True,
    )
    name = fields.Char(
        string='Cheque No.',
        required=True,
        tracking=True,
        copy=False,
        index=True,
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True,
        tracking=True,
        check_company=True,
    )
    salesperson_id = fields.Many2one(
        'res.users',
        string='Salesperson',
        tracking=True,
        check_company=True,
    )
    invoice_ids = fields.Many2many(
        'account.move',
        'wecare_cheque_invoice_rel',
        'cheque_id',
        'invoice_id',
        string='Invoices',
        domain="[('move_type', 'in', ('out_invoice', 'in_invoice')), ('partner_id', '=', partner_id)]",
    )
    payment_id = fields.Many2one(
        'account.payment',
        string='Payment',
        copy=False,
        tracking=True,
    )
    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
        tracking=True,
    )
    currency_id = fields.Many2one(
        related='company_id.currency_id',
        store=True,
    )
    amount = fields.Monetary(
        required=True,
        tracking=True,
    )
    cheque_date = fields.Date(
        string='Cheque Date',
        required=True,
        tracking=True,
    )
    received_date = fields.Date(
        string='Received Date',
        required=True,
        default=fields.Date.context_today,
        tracking=True,
    )
    deposit_date = fields.Date(
        string='Deposit Date',
        tracking=True,
    )
    journal_id = fields.Many2one(
        'account.journal',
        string='Bank',
        domain="[('type', '=', 'bank')]",
        check_company=True,
        tracking=True,
    )
    partner_bank_id = fields.Many2one(
        'res.partner.bank',
        string='Bank Account',
        check_company=True,
    )
    collection_type = fields.Selection(
        [
            ('cheque', 'Cheque'),
            ('cash', 'Cash'),
            ('cpo', 'CPO'),
            ('tele_birr', 'Tele Birr'),
        ],
        default='cheque',
        required=True,
        tracking=True,
    )
    payment_type = fields.Selection(
        [
            ('inbound', 'Customer Collection'),
            ('outbound', 'Vendor Payment'),
        ],
        default='inbound',
        required=True,
        tracking=True,
    )
    state = fields.Selection(
        [
            ('received', 'Received'),
            ('deposited', 'Deposited'),
            ('cleared', 'Cleared'),
            ('bounced', 'Bounced'),
        ],
        default='received',
        required=True,
        tracking=True,
        copy=False,
        index=True,
    )
    bounce_date = fields.Date(tracking=True)
    bounce_reason = fields.Text(tracking=True)
    redeposit_date = fields.Date(string='Re-deposit Date', tracking=True)
    original_cheque_id = fields.Many2one(
        'wecare.cheque.register',
        string='Original Cheque',
        copy=False,
        tracking=True,
        help='Original bounced cheque when this record is a re-deposit.',
    )
    redeposit_ids = fields.One2many(
        'wecare.cheque.register',
        'original_cheque_id',
        string='Re-deposits',
    )
    remarks = fields.Text()
    is_credit_sale = fields.Boolean(
        string='Credit Sale',
        compute='_compute_is_credit_sale',
        store=True,
    )
    outstanding = fields.Boolean(
        string='Open Bounce',
        compute='_compute_outstanding',
        store=True,
    )

    @api.depends('invoice_ids.payment_method')
    def _compute_is_credit_sale(self):
        for cheque in self:
            invoices = cheque.invoice_ids.filtered(
                lambda inv: inv.move_type == 'out_invoice'
            )
            if not invoices:
                cheque.is_credit_sale = cheque.payment_type == 'inbound'
                continue
            methods = invoices.mapped('payment_method')
            cheque.is_credit_sale = any(m == 'credit' for m in methods) or not any(methods)

    @api.depends('state', 'redeposit_ids.state')
    def _compute_outstanding(self):
        for cheque in self:
            if cheque.state != 'bounced':
                cheque.outstanding = False
            else:
                cheque.outstanding = not any(
                    r.state in ('deposited', 'cleared') for r in cheque.redeposit_ids
                )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('collection_no') or vals.get('collection_no') == 'New':
                vals['collection_no'] = self.env['ir.sequence'].next_by_code(
                    'wecare.cheque.register'
                ) or 'New'
        return super().create(vals_list)

    @api.constrains('name', 'company_id', 'original_cheque_id')
    def _check_duplicate_cheque_no(self):
        for cheque in self:
            if not cheque.name:
                continue
            domain = [
                ('name', '=', cheque.name),
                ('company_id', '=', cheque.company_id.id),
                ('id', '!=', cheque.id),
                ('original_cheque_id', '=', False),
            ]
            if cheque.original_cheque_id:
                domain.append(('id', '!=', cheque.original_cheque_id.id))
            if self.search_count(domain):
                raise ValidationError(self.env._(
                    'Cheque number "%s" already exists. Duplicate cheque numbers are not allowed.',
                    cheque.name,
                ))

    @api.constrains('amount', 'cheque_date')
    def _check_amount_date(self):
        for cheque in self:
            if cheque.amount <= 0:
                raise ValidationError(self.env._('Cheque amount must be greater than zero.'))
            if not cheque.cheque_date:
                raise ValidationError(self.env._('Every cheque must contain a cheque date.'))

    def action_deposit(self):
        for cheque in self:
            if cheque.state != 'received':
                raise UserError(self.env._('Only received cheques can be deposited.'))
            cheque.write({
                'state': 'deposited',
                'deposit_date': cheque.deposit_date or fields.Date.context_today(cheque),
            })

    def action_clear(self):
        for cheque in self:
            if cheque.state != 'deposited':
                raise UserError(self.env._('Only deposited cheques can be cleared.'))
            cheque.state = 'cleared'

    def action_bounce(self):
        for cheque in self:
            if cheque.state not in ('received', 'deposited'):
                raise UserError(self.env._(
                    'Only received or deposited cheques can be marked as bounced.'
                ))
            cheque.write({
                'state': 'bounced',
                'bounce_date': cheque.bounce_date or fields.Date.context_today(cheque),
            })

    def action_redeposit(self):
        """Create a new cheque linked to the bounced original. Never delete the bounce."""
        self.ensure_one()
        if self.state != 'bounced':
            raise UserError(self.env._('Only bounced cheques can be re-deposited.'))
        new_cheque = self.copy({
            'name': self.name,
            'state': 'deposited',
            'deposit_date': fields.Date.context_today(self),
            'redeposit_date': fields.Date.context_today(self),
            'original_cheque_id': self.id,
            'bounce_date': False,
            'bounce_reason': False,
            'payment_id': False,
            'collection_no': 'New',
            'remarks': self.env._('Re-deposit of bounced cheque %s', self.name),
        })
        self.redeposit_date = fields.Date.context_today(self)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'wecare.cheque.register',
            'res_id': new_cheque.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def unlink(self):
        bounced = self.filtered(lambda c: c.state == 'bounced')
        if bounced:
            raise UserError(self.env._(
                'A bounced cheque should not be deleted; keep it with status Bounced.'
            ))
        return super().unlink()

    def classify_for_period(self, date_from, date_to):
        """Return current / previous / bounce for the selected reporting period.

        Current: cheque date (or received date) and deposit date are both in the period.
        Previous: cheque originated earlier, but was deposited in this period.
        Bounce: bounced during the period (or bounced and still open).
        """
        self.ensure_one()
        if self.state == 'bounced':
            bounce_day = self.bounce_date or self.deposit_date or self.received_date
            if bounce_day and date_from <= bounce_day <= date_to:
                return 'bounce'
            if self.outstanding and self.bounce_date and self.bounce_date <= date_to:
                return 'bounce'
        origin = self.cheque_date or self.received_date
        deposit = self.deposit_date
        if deposit and date_from <= deposit <= date_to:
            if origin and origin < date_from:
                return 'previous'
            return 'current'
        if not deposit and self.received_date and date_from <= self.received_date <= date_to:
            if origin and origin < date_from:
                return 'previous'
            return 'current'
        return False

    def action_open_payment(self):
        self.ensure_one()
        if not self.payment_id:
            return False
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'res_id': self.payment_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
