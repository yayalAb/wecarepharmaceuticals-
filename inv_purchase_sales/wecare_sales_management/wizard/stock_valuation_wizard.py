# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import api, fields, models


class WecareStockValuationWizard(models.TransientModel):
    _name = 'wecare.stock.valuation.wizard'
    _description = 'Stock Valuation / Expiry Report'

    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
    )
    date_from = fields.Date(required=True)
    date_to = fields.Date(required=True)
    location_id = fields.Many2one(
        'stock.location',
        domain="[('usage', '=', 'internal')]",
    )
    product_id = fields.Many2one('product.product')
    report_type = fields.Selection(
        [
            ('valuation', 'Stock Valuation (invoice-time moves)'),
            ('expiry', 'Expiry Date'),
        ],
        required=True,
        default='valuation',
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        today = fields.Date.context_today(self)
        res.setdefault('date_from', today.replace(month=1, day=1))
        res.setdefault('date_to', today)
        return res

    def get_valuation_data(self):
        self.ensure_one()
        domain = [
            ('company_id', '=', self.company_id.id),
            ('create_date', '>=', fields.Datetime.to_datetime(self.date_from)),
            ('create_date', '<=', fields.Datetime.to_datetime(self.date_to) + timedelta(days=1, seconds=-1)),
        ]
        if self.product_id:
            domain.append(('product_id', '=', self.product_id.id))
        layers = self.env['stock.valuation.layer'].search(domain, order='create_date, id')
        lines = []
        for layer in layers:
            move = layer.stock_move_id
            if self.location_id and move and move.location_id != self.location_id \
                    and move.location_dest_id != self.location_id:
                continue
            lot = self.env['stock.lot']
            if move:
                lot = move.move_line_ids.mapped('lot_id')[:1]
            location = False
            if move:
                location = move.location_id if move.picking_code == 'outgoing' else move.location_dest_id
            lines.append({
                'date': layer.create_date,
                'product': layer.product_id.display_name,
                'qty': layer.quantity,
                'location': location.display_name if location else '',
                'lot': lot.name if lot else '',
                'expiry': lot.expiration_date if lot else False,
                'value': layer.value,
                'reference': move.picking_id.name or move.origin or layer.description or '',
            })
        return {
            'title': self.env._('Stock Valuation Report'),
            'lines': lines,
            'total_qty': sum(l['qty'] for l in lines),
            'total_value': sum(l['value'] for l in lines),
            'company': self.company_id,
            'date_from': self.date_from,
            'date_to': self.date_to,
        }

    def get_expiry_data(self):
        self.ensure_one()
        lots = self.env['stock.lot'].search([
            ('company_id', '=', self.company_id.id),
            ('expiration_date', '!=', False),
        ], order='expiration_date')
        if self.product_id:
            lots = lots.filtered(lambda l: l.product_id == self.product_id)
        lots = lots.filtered(lambda l: l.product_qty > 0)
        lines = []
        for lot in lots:
            lines.append({
                'product': lot.product_id.display_name,
                'lot': lot.name,
                'expiry': lot.expiration_date,
                'qty': lot.product_qty,
            })
        return {
            'title': self.env._('Stock Expiry Report'),
            'lines': lines,
            'company': self.company_id,
            'date_from': self.date_from,
            'date_to': self.date_to,
        }

    def action_print(self):
        if self.report_type == 'expiry':
            return self.env.ref(
                'wecare_sales_management.action_report_stock_expiry'
            ).report_action(self)
        return self.env.ref(
            'wecare_sales_management.action_report_stock_valuation'
        ).report_action(self)
