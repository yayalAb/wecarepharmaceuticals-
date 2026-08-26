# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    invoice_mrc_no = fields.Char(
        string='MRC No',
        help='Fixed MRC number applied to customer sales invoices.',
    )


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    invoice_mrc_no = fields.Char(
        related='company_id.invoice_mrc_no',
        readonly=False,
        string='MRC No',
    )
