# -*- coding: utf-8 -*-
from odoo import fields, models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    lot_id = fields.Many2one(
        'stock.lot',
        string='Serial Number',
        copy=False,
        check_company=True,
    )
    expiration_date = fields.Datetime(
        string='Expiration Date',
        related='lot_id.expiration_date',
        store=True,
        readonly=True,
    )
