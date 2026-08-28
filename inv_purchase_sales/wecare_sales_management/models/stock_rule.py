# -*- coding: utf-8 -*-
from odoo import models


class StockRule(models.Model):
    _inherit = 'stock.rule'

    def _get_custom_move_fields(self):
        fields = super()._get_custom_move_fields()
        fields.append('location_id')
        return fields

    def _get_stock_move_values(
        self, product_id, product_qty, product_uom, location_dest_id,
        name, origin, company_id, values,
    ):
        move_values = super()._get_stock_move_values(
            product_id, product_qty, product_uom, location_dest_id,
            name, origin, company_id, values,
        )
        location = values.get('location_id')
        if location:
            move_values['location_id'] = location.id if hasattr(location, 'id') else location
        return move_values
