# -*- coding: utf-8 -*-
from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    stock_location_id = fields.Many2one(
        'stock.location',
        string='Stock Location',
        domain="[('usage', '=', 'internal'), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        check_company=True,
        compute='_compute_stock_location_id',
        store=True,
        readonly=False,
        precompute=True,
    )

    @api.depends('order_id.stock_location_id', 'order_id.warehouse_id', 'display_type')
    def _compute_stock_location_id(self):
        # Line location defaults to the order location; a line location chosen by hand is
        # kept as long as it belongs to the order's warehouse.
        for line in self:
            order = line.order_id
            location = line.stock_location_id
            if line.display_type:
                location = False
            elif not location or (order.warehouse_id and location.warehouse_id != order.warehouse_id):
                location = order.stock_location_id or order.warehouse_id.lot_stock_id
            line.stock_location_id = location

    def _get_lot_source_location(self):
        # Offer only lots stocked in the line's own location.
        return self.stock_location_id or super()._get_lot_source_location()

    @api.depends('product_id', 'order_id.warehouse_id', 'stock_location_id')
    def _compute_available_lot_ids(self):
        return super()._compute_available_lot_ids()

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
