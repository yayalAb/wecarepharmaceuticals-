# -*- coding: utf-8 -*-
from odoo import fields, models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    stock_location_id = fields.Many2one(
        'stock.location',
        string='Stock Location',
        check_company=True,
        copy=False,
    )
