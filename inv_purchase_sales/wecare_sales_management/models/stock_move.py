# -*- coding: utf-8 -*-
from odoo import models


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _prepare_move_line_vals(self, quantity=None, reserved_quant=None):
        vals = super()._prepare_move_line_vals(
            quantity=quantity,
            reserved_quant=reserved_quant,
        )
        sale_line = self.sale_line_id
        if sale_line and sale_line.stock_location_id and not reserved_quant:
            vals['location_id'] = sale_line.stock_location_id.id
        return vals
