# -*- coding: utf-8 -*-
from odoo import api, fields, models


class SaleOrder(models.Model):
    _name = 'sale.order'
    _inherit = ['sale.order', 'wecare.share.mixin']

    stock_location_id = fields.Many2one(
        'stock.location',
        string='Stock Location',
        domain="[('usage', '=', 'internal'), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
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

    @api.onchange('stock_location_id')
    def _onchange_stock_location_id(self):
        if self.stock_location_id:
            for line in self.order_line.filtered(lambda l: not l.display_type):
                line.stock_location_id = self.stock_location_id

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
