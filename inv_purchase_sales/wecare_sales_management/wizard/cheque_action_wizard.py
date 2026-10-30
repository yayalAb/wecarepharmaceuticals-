# -*- coding: utf-8 -*-
from odoo import api, fields, models


class WecareChequeBounceWizard(models.TransientModel):
    _name = 'wecare.cheque.bounce.wizard'
    _description = 'Cheque Bounce Processing Wizard'

    cheque_id = fields.Many2one(
        'wecare.cheque.register',
        string='Cheque',
        required=True,
    )
    cheque_no = fields.Char(related='cheque_id.name', readonly=True)
    partner_id = fields.Many2one(related='cheque_id.partner_id', readonly=True)
    amount = fields.Monetary(related='cheque_id.amount', readonly=True)
    currency_id = fields.Many2one(related='cheque_id.currency_id', readonly=True)
    bounce_date = fields.Date(
        string='Bounce Date',
        required=True,
        default=fields.Date.context_today,
    )
    bounce_reason = fields.Text(
        string='Bounce Reason',
        required=True,
        help='State the specific reason provided by the bank (e.g. Insufficient Funds, Signature Mismatch, Closed Account, etc.)',
    )
    attachment = fields.Binary(
        string='Bank Bounce Notice / Slip',
        attachment=True,
        help='Upload scanned bank bounce memo or notice.',
    )
    attachment_filename = fields.Char(string='Attachment Filename')

    def action_confirm_bounce(self):
        self.ensure_one()
        self.cheque_id._process_bounce(
            bounce_date=self.bounce_date,
            bounce_reason=self.bounce_reason,
            attachment=self.attachment,
            attachment_filename=self.attachment_filename,
        )
        return {'type': 'ir.actions.act_window_close'}


class WecareChequeCancelWizard(models.TransientModel):
    _name = 'wecare.cheque.cancel.wizard'
    _description = 'Cheque Cancellation Wizard'

    cheque_id = fields.Many2one(
        'wecare.cheque.register',
        string='Cheque',
        required=True,
    )
    cheque_no = fields.Char(related='cheque_id.name', readonly=True)
    partner_id = fields.Many2one(related='cheque_id.partner_id', readonly=True)
    amount = fields.Monetary(related='cheque_id.amount', readonly=True)
    currency_id = fields.Many2one(related='cheque_id.currency_id', readonly=True)
    cancel_date = fields.Date(
        string='Cancellation Date',
        required=True,
        default=fields.Date.context_today,
    )
    cancel_reason = fields.Text(
        string='Cancellation Reason',
        required=True,
        help='State the authorized business reason for voiding/cancelling this cheque collection.',
    )

    def action_confirm_cancel(self):
        self.ensure_one()
        self.cheque_id._process_cancel(
            cancel_date=self.cancel_date,
            cancel_reason=self.cancel_reason,
        )
        return {'type': 'ir.actions.act_window_close'}
