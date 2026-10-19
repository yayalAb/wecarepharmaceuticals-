# -*- coding: utf-8 -*-
from odoo import api, fields, models

from .cheque_register import CHEQUE_METHODS


class AccountPayment(models.Model):
    _name = 'account.payment'
    _inherit = ['account.payment', 'wecare.share.mixin']

    cheque_register_id = fields.Many2one(
        'wecare.cheque.register',
        string='Cheque Register',
        copy=False,
        tracking=True,
    )
    wecare_salesperson_id = fields.Many2one(
        'res.users',
        string='Salesperson',
        compute='_compute_wecare_salesperson_id',
        store=True,
        readonly=False,
    )
    wecare_collection_method = fields.Selection(
        [
            ('cash', 'Cash'),
            ('bank_transfer', 'Bank Transfer'),
            ('cheque', 'Cheque / PDC'),
            ('telebirr', 'Telebirr / Mobile Money'),
            ('other', 'Other'),
        ],
        string='Collection Method',
        compute='_compute_wecare_collection_method',
        store=True,
    )

    @api.depends('journal_id', 'payment_method_line_id', 'cheque_register_id')
    def _compute_wecare_collection_method(self):
        for pay in self:
            code = (pay.payment_method_code or '').lower()
            journal_type = pay.journal_id.type
            if pay.cheque_register_id or code in CHEQUE_METHODS:
                pay.wecare_collection_method = 'cheque'
            elif journal_type == 'cash' or 'cash' in code:
                pay.wecare_collection_method = 'cash'
            elif 'tele' in (pay.journal_id.name or '').lower() or 'tele' in code:
                pay.wecare_collection_method = 'telebirr'
            elif journal_type == 'bank':
                pay.wecare_collection_method = 'bank_transfer'
            else:
                pay.wecare_collection_method = 'other'

    @api.depends('reconciled_invoice_ids.invoice_user_id', 'partner_id.user_id')
    def _compute_wecare_salesperson_id(self):
        for pay in self:
            invoices = pay.reconciled_invoice_ids
            sp = invoices[:1].invoice_user_id or pay.partner_id.user_id
            pay.wecare_salesperson_id = sp or pay.create_uid


    def action_post(self):
        res = super().action_post()
        self._wecare_sync_cheque_register()
        return res

    def _wecare_is_cheque_method(self):
        self.ensure_one()
        code = (self.payment_method_code or '').lower()
        return code in CHEQUE_METHODS

    def _wecare_sync_cheque_register(self):
        Cheque = self.env['wecare.cheque.register']
        for payment in self:
            if not payment._wecare_is_cheque_method():
                continue
            cheque_no = (payment.check_transfer_no or '').strip()
            if not cheque_no:
                continue
            invoices = payment.reconciled_invoice_ids
            salesperson = (
                invoices[:1].invoice_user_id
                or payment.partner_id.user_id
                or payment.create_uid
            )
            vals = {
                'name': cheque_no,
                'partner_id': payment.partner_id.id,
                'salesperson_id': salesperson.id if salesperson else False,
                'invoice_ids': [(6, 0, invoices.ids)],
                'payment_id': payment.id,
                'company_id': payment.company_id.id,
                'amount': payment.amount,
                'cheque_date': payment.maturity_date or payment.date,
                'received_date': payment.date,
                'journal_id': payment.journal_id.id if payment.journal_id.type == 'bank' else False,
                'partner_bank_id': payment.partner_bank_id.id,
                'collection_type': 'cheque',
                'payment_type': payment.payment_type,
                'state': 'received',
            }
            if payment.cheque_register_id:
                payment.cheque_register_id.write({
                    key: val for key, val in vals.items()
                    if key not in ('name', 'state')
                })
            else:
                existing = Cheque.search([
                    ('payment_id', '=', payment.id),
                ], limit=1)
                cheque = existing or Cheque.create(vals)
                payment.cheque_register_id = cheque
