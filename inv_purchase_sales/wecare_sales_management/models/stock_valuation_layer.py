# -*- coding: utf-8 -*-
from odoo import fields, models


class StockValuationLayer(models.Model):
    _inherit = 'stock.valuation.layer'

    def _records_for_print(self):
        if self:
            return self
        return self.search(list(self.env.context.get('active_domain') or []))

    def _wecare_valuation_report_data(self):
        lines = []
        for layer in self:
            move = layer.stock_move_id
            lot = move.move_line_ids.mapped('lot_id')[:1] if move else self.env['stock.lot']
            location = False
            if move:
                location = (
                    move.location_id
                    if move.picking_code == 'outgoing'
                    else move.location_dest_id
                )
            lines.append({
                'date': layer.create_date,
                'product': layer.product_id.display_name,
                'qty': layer.quantity,
                'location': location.display_name if location else '',
                'lot': lot.name if lot else '',
                'expiry': lot.expiration_date if lot else False,
                'value': layer.value,
                'reference': (
                    move.picking_id.name or move.origin or layer.description or ''
                    if move else (layer.description or '')
                ),
            })
        dates = [l.create_date.date() for l in self if l.create_date]
        today = fields.Date.context_today(self)
        return {
            'title': self.env._('Stock Valuation Report'),
            'lines': lines,
            'total_qty': sum(l['qty'] for l in lines),
            'total_value': sum(l['value'] for l in lines),
            'company': self[:1].company_id or self.env.company,
            'date_from': min(dates) if dates else today,
            'date_to': max(dates) if dates else today,
        }

    def action_print_stock_valuation(self):
        return self.env.ref(
            'wecare_sales_management.action_report_stock_valuation'
        ).report_action(self._records_for_print())
