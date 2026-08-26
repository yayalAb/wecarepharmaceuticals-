# -*- coding: utf-8 -*-
from odoo import fields, models


class StockMove(models.Model):
    _inherit = 'stock.move'

    restrict_lot_id = fields.Many2one(
        'stock.lot',
        string='Restrict Lot/Serial',
        index=True,
        help='When set (from the sales order line), reservation must use this lot/serial.',
    )

    def _update_reserved_quantity(
        self, need, location_id, lot_id=None, package_id=None, owner_id=None, strict=True,
    ):
        if self.restrict_lot_id and not lot_id:
            lot_id = self.restrict_lot_id
        return super()._update_reserved_quantity(
            need,
            location_id,
            lot_id=lot_id,
            package_id=package_id,
            owner_id=owner_id,
            strict=strict,
        )
