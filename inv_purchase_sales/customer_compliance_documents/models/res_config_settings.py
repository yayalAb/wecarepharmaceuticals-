# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    compliance_block_sale_orders = fields.Boolean(
        related='company_id.compliance_block_sale_orders',
        readonly=False,
    )
    compliance_expiring_soon_days = fields.Integer(
        related='company_id.compliance_expiring_soon_days',
        readonly=False,
    )
    compliance_require_company_only = fields.Boolean(
        related='company_id.compliance_require_company_only',
        readonly=False,
    )
