# -*- coding: utf-8 -*-
from odoo import api, fields, models


class SaleOrder(models.Model):
    _name = 'sale.order'
    _inherit = ['sale.order', 'wecare.share.mixin']

    stock_location_id = fields.Many2one(
        'stock.location',
        string='Stock Location',
        domain="[('usage', '=', 'internal'), ('warehouse_id', '=?', warehouse_id), "
               "'|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        check_company=True,
        help='Source location carried to order lines, invoice and delivery. '
             'Stock is deducted from this location when the invoice is validated.',
    )
    share_history_count = fields.Integer(compute='_compute_share_history_count')

    def _compute_share_history_count(self):
        History = self.env['wecare.share.history']
        for order in self:
            order.share_history_count = History.search_count([
                ('res_model', '=', 'sale.order'),
                ('res_id', '=', order.id),
            ])

    @api.onchange('warehouse_id')
    def _onchange_warehouse_id_stock_location(self):
        # Default line location = main stock of the selected warehouse; move lines that
        # point to a location outside the warehouse.
        warehouse = self.warehouse_id
        if not warehouse:
            return
        if self.stock_location_id.warehouse_id != warehouse:
            self.stock_location_id = warehouse.lot_stock_id
        for line in self.order_line.filtered(lambda l: not l.display_type):
            if line.stock_location_id.warehouse_id != warehouse:
                line.stock_location_id = warehouse.lot_stock_id

    def action_view_share_history(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._('Share History'),
            'res_model': 'wecare.share.history',
            'view_mode': 'list,form',
            'domain': [('res_model', '=', 'sale.order'), ('res_id', '=', self.id)],
            'context': {'default_res_model': 'sale.order', 'default_res_id': self.id},
        }
