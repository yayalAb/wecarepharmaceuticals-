# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    invoice_mrc_no = fields.Char(
        related='company_id.invoice_mrc_no',
        readonly=False,
        string='MRC No',
    )
