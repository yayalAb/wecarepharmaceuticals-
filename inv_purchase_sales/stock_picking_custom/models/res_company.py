# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    invoice_mrc_no = fields.Char(
        string='MRC No',
        help='Fixed MRC number applied to customer sales invoices.',
    )
