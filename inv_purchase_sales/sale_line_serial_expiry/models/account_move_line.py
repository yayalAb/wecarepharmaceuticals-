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
        compute='_compute_lot_ids',
        store=True,
        readonly=False,
        precompute=True,
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

    @api.depends('sale_line_ids.lot_ids', 'sale_line_ids.move_ids.move_line_ids.lot_id', 'sale_line_ids.move_ids.state')
    def _compute_lot_ids(self):
        for line in self:
            if not line.lot_ids and line.sale_line_ids and (not line.move_id or line.move_id.state == 'draft'):
                # 1. From sales order line
                lots = line.sale_line_ids.lot_ids
                # 2. From delivered stock moves
                if not lots:
                    done_moves = line.sale_line_ids.move_ids.filtered(lambda m: m.state == 'done')
                    lots = done_moves.move_line_ids.lot_id
                # 3. From active reserved stock moves
                if not lots:
                    active_moves = line.sale_line_ids.move_ids.filtered(lambda m: m.state not in ('cancel', 'done'))
                    lots = active_moves.move_line_ids.lot_id or active_moves.restrict_lot_ids
                if lots:
                    line.lot_ids = lots
            elif not line.lot_ids:
                line.lot_ids = False

    @api.onchange('product_id')
    def _onchange_product_id_lot(self):
        if self.product_id and self.sale_line_ids and not self.lot_ids:
            lots = self.sale_line_ids.lot_ids
            if not lots:
                done_moves = self.sale_line_ids.move_ids.filtered(lambda m: m.state == 'done')
                lots = done_moves.move_line_ids.lot_id
            if not lots:
                active_moves = self.sale_line_ids.move_ids.filtered(lambda m: m.state not in ('cancel', 'done'))
                lots = active_moves.move_line_ids.lot_id or active_moves.restrict_lot_ids
            if lots:
                self.lot_ids = lots

    @api.depends('lot_ids')
    def _compute_lot_id(self):
        for line in self:
            line.lot_id = line.lot_ids[:1]

    @api.depends('lot_ids.expiration_date')
    def _compute_expiration_date(self):
        for line in self:
            dates = [d for d in line.lot_ids.mapped('expiration_date') if d]
            line.expiration_date = min(dates) if dates else False
