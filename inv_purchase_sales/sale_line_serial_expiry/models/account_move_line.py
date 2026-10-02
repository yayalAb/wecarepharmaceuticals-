# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    lot_ids = fields.Many2many(
        'stock.lot',
        'account_move_line_stock_lot_rel',
        'account_move_line_id',
        'stock_lot_id',
        string='Serial Numbers',
        copy=False,
        check_company=True,
    )
    # First lot, kept for code and reports that expect a single lot.
    lot_id = fields.Many2one(
        'stock.lot',
        string='Serial Number',
        compute='_compute_lot_id',
        store=True,
        check_company=True,
    )
    expiration_date = fields.Datetime(
        string='Expiration Date',
        compute='_compute_expiration_date',
        store=True,
        help='Earliest expiration date of the lots.',
    )

    @api.depends('lot_ids')
    def _compute_lot_id(self):
        for line in self:
            line.lot_id = line.lot_ids[:1]

    @api.depends('lot_ids.expiration_date')
    def _compute_expiration_date(self):
        for line in self:
            dates = [d for d in line.lot_ids.mapped('expiration_date') if d]
            line.expiration_date = min(dates) if dates else False
