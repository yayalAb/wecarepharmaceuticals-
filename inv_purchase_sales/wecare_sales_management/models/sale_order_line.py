# -*- coding: utf-8 -*-
from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    stock_location_id = fields.Many2one(
        'stock.location',
        string='Stock Location',
        domain="[('usage', '=', 'internal'), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        check_company=True,
    )

    @api.onchange('product_id')
    def _onchange_product_id_stock_location(self):
        if not self.stock_location_id and self.order_id.stock_location_id:
            self.stock_location_id = self.order_id.stock_location_id

    def _prepare_procurement_values(self, group_id=False):
        values = super()._prepare_procurement_values(group_id=group_id)
        if self.stock_location_id:
            values['location_id'] = self.stock_location_id.id
        return values

    def _prepare_invoice_line(self, **optional_values):
        res = super()._prepare_invoice_line(**optional_values)
        if self.stock_location_id:
            res['stock_location_id'] = self.stock_location_id.id
        return res
