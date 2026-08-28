# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    wecare_deduct_stock_on_invoice = fields.Boolean(
        related='company_id.wecare_deduct_stock_on_invoice',
        readonly=False,
    )
    wecare_expiry_notify_days = fields.Integer(
        related='company_id.wecare_expiry_notify_days',
        readonly=False,
    )
