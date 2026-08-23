# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    compliance_block_sale_orders = fields.Boolean(
        string='Block Sales Orders on Non-Compliance',
        default=True,
        help='Prevent confirming Sales Orders when the customer is missing '
             'required or valid compliance documents.',
    )
    compliance_expiring_soon_days = fields.Integer(
        string='Expiring Soon (Days)',
        default=30,
        help='Documents that expire within this many days are marked Expiring Soon.',
    )
    compliance_require_company_only = fields.Boolean(
        string='Require Compliance for Companies Only',
        default=True,
        help='When enabled, only company customers are checked. Individual contacts are skipped.',
    )

    def write(self, vals):
        res = super().write(vals)
        if 'compliance_expiring_soon_days' in vals:
            self.env['customer.compliance.document'].search([])._cron_recompute_status()
        return res
