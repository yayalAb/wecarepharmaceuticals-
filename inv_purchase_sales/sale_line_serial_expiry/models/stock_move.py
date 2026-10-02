# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.tools import float_compare


class StockMove(models.Model):
    _inherit = 'stock.move'

    restrict_lot_ids = fields.Many2many(
        'stock.lot',
        'stock_move_restrict_lot_rel',
        'move_id',
        'lot_id',
        string='Restrict Lots/Serials',
        help='When set (from the sales order line), reservation only uses these lots/serials.',
    )
    # First restricted lot, kept for views / code that expect a single lot.
    restrict_lot_id = fields.Many2one(
        'stock.lot',
        string='Restrict Lot/Serial',
        compute='_compute_restrict_lot_id',
        store=True,
        index=True,
    )
    restrict_lot_expiration_date = fields.Datetime(
        string='Expiration Date',
        compute='_compute_lot_display',
    )
    lot_display = fields.Char(
        string='Serial / Lot',
        compute='_compute_lot_display',
        help='Serials from the sales order line, otherwise the lots reserved / picked.',
    )
    lot_expiration_display = fields.Datetime(
        string='Expiration Date',
        compute='_compute_lot_display',
    )

    @api.depends('restrict_lot_ids')
    def _compute_restrict_lot_id(self):
        for move in self:
            move.restrict_lot_id = move.restrict_lot_ids[:1]

    @api.depends('restrict_lot_ids', 'move_line_ids.lot_id', 'move_line_ids.lot_name')
    def _compute_lot_display(self):
        for move in self:
            lots = move.restrict_lot_ids or move.move_line_ids.lot_id
            names = lots.mapped('name') or [n for n in move.move_line_ids.mapped('lot_name') if n]
            move.lot_display = ', '.join(dict.fromkeys(names))
            dates = [d for d in lots.mapped('expiration_date') if d]
            move.lot_expiration_display = min(dates) if dates else False
            restrict_dates = [d for d in move.restrict_lot_ids.mapped('expiration_date') if d]
            move.restrict_lot_expiration_date = min(restrict_dates) if restrict_dates else False

    def _prepare_move_line_vals(self, quantity=None, reserved_quant=None):
        vals = super()._prepare_move_line_vals(quantity=quantity, reserved_quant=reserved_quant)
        # Lines created without a reserved quant (manual pick, auto-fill on invoice
        # validation) still get the serial chosen on the sales order line, when it is
        # unambiguous (a single lot selected).
        if (
            len(self.restrict_lot_ids) == 1
            and not vals.get('lot_id')
            and self.product_id.tracking != 'none'
        ):
            vals['lot_id'] = self.restrict_lot_ids.id
        return vals

    def _update_reserved_quantity(
        self, need, location_id, lot_id=None, package_id=None, owner_id=None, strict=True,
    ):
        if not self.restrict_lot_ids or lot_id:
            return super()._update_reserved_quantity(
                need, location_id, lot_id=lot_id, package_id=package_id,
                owner_id=owner_id, strict=strict,
            )
        # Reserve from the selected lots, in the order they were chosen, until the
        # need is covered.
        rounding = self.product_id.uom_id.rounding
        taken = 0.0
        for lot in self.restrict_lot_ids:
            remaining = need - taken
            if float_compare(remaining, 0.0, precision_rounding=rounding) <= 0:
                break
            taken += super()._update_reserved_quantity(
                remaining, location_id, lot_id=lot, package_id=package_id,
                owner_id=owner_id, strict=strict,
            )
        return taken
