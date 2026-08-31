# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    stock_location_id = fields.Many2one(
        'stock.location',
        string='Stock Location',
        check_company=True,
        copy=False,
    )
    wecare_salesperson_id = fields.Many2one(
        related='move_id.invoice_user_id',
        store=True,
        string='Salesperson',
    )
    wecare_invoice_date = fields.Date(
        related='move_id.invoice_date',
        store=True,
        string='Invoice Date',
    )

    def _records_for_print(self):
        if self:
            return self
        return self.search(list(self.env.context.get('active_domain') or []))

    def _wecare_sales_analysis_data(self, group_by='customer'):
        from collections import defaultdict
        buckets = defaultdict(lambda: {'qty': 0.0, 'amount': 0.0})
        for line in self:
            key = line.partner_id if group_by == 'customer' else line.product_id
            buckets[key]['qty'] += line.quantity
            buckets[key]['amount'] += line.price_subtotal
        lines = []
        for rec, vals in buckets.items():
            lines.append({
                'name': rec.display_name if rec else self.env._('Undefined'),
                **vals,
            })
        lines.sort(key=lambda l: l['name'] or '')
        dates = [d for d in self.mapped('wecare_invoice_date') if d]
        today = fields.Date.context_today(self)
        return {
            'title': self.env._('Customer Sales Report') if group_by == 'customer'
            else self.env._('Product Sales Report'),
            'group_label': self.env._('Customer') if group_by == 'customer' else self.env._('Product'),
            'lines': lines,
            'total_qty': sum(l['qty'] for l in lines),
            'total_amount': sum(l['amount'] for l in lines),
            'company': self[:1].company_id or self.env.company,
            'date_from': min(dates) if dates else today,
            'date_to': max(dates) if dates else today,
        }

    def action_print_customer_sales(self):
        return self.env.ref(
            'wecare_sales_management.action_report_sales_analysis'
        ).with_context(wecare_sales_group='customer').report_action(
            self._records_for_print()
        )

    def action_print_product_sales(self):
        return self.env.ref(
            'wecare_sales_management.action_report_sales_analysis'
        ).with_context(wecare_sales_group='product').report_action(
            self._records_for_print()
        )
