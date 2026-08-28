# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    wecare_deduct_stock_on_invoice = fields.Boolean(
        string='Deduct Stock on Invoice Validation',
        default=True,
        help='Validate related delivery orders when a customer invoice is posted, '
             'so stock is deducted at invoice confirmation instead of waiting for DO validation.',
    )
    wecare_expiry_notify_days = fields.Integer(
        string='Expiry Notification Days',
        default=90,
        help='Notify stock users when a lot/batch expires within this many days.',
    )
