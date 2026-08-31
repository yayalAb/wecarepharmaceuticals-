# -*- coding: utf-8 -*-
from odoo import api, fields, models


class WecareSalesAnalysisWizard(models.TransientModel):
    _name = 'wecare.sales.analysis.wizard'
    _description = 'Customer / Product Sales Report'

    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
    )
    date_from = fields.Date(required=True)
    date_to = fields.Date(required=True)
    salesperson_id = fields.Many2one('res.users')
    partner_id = fields.Many2one('res.partner', string='Customer')
    product_id = fields.Many2one('product.product')
    report_type = fields.Selection(
        [
            ('customer', 'Customer Sales'),
            ('product', 'Product Sales'),
        ],
        required=True,
        default='customer',
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        today = fields.Date.context_today(self)
        res.setdefault('date_from', today.replace(month=1, day=1))
        res.setdefault('date_to', today)
        return res

    def _invoice_line_domain(self):
        domain = [
            ('move_id.move_type', '=', 'out_invoice'),
            ('move_id.state', '=', 'posted'),
            ('move_id.company_id', '=', self.company_id.id),
            ('move_id.invoice_date', '>=', self.date_from),
            ('move_id.invoice_date', '<=', self.date_to),
            ('display_type', '=', 'product'),
            ('product_id', '!=', False),
        ]
        if self.salesperson_id:
            domain.append(('move_id.invoice_user_id', '=', self.salesperson_id.id))
        if self.partner_id:
            domain.append(('move_id.partner_id', '=', self.partner_id.id))
        if self.product_id:
            domain.append(('product_id', '=', self.product_id.id))
        return domain

    def get_report_data(self):
        self.ensure_one()
        groupby = ['partner_id'] if self.report_type == 'customer' else ['product_id']
        grouped = self.env['account.move.line'].read_group(
            self._invoice_line_domain(),
            ['quantity:sum', 'price_subtotal:sum'],
            groupby,
        )
        lines = []
        for row in grouped:
            name = False
            if self.report_type == 'customer':
                name = row['partner_id'][1] if row.get('partner_id') else self.env._('Undefined')
            else:
                name = row['product_id'][1] if row.get('product_id') else self.env._('Undefined')
            lines.append({
                'name': name,
                'qty': row.get('quantity') or 0.0,
                'amount': row.get('price_subtotal') or 0.0,
            })
        lines.sort(key=lambda l: l['name'] or '')
        return {
            'title': self.env._('Customer Sales Report') if self.report_type == 'customer'
            else self.env._('Product Sales Report'),
            'lines': lines,
            'total_qty': sum(l['qty'] for l in lines),
            'total_amount': sum(l['amount'] for l in lines),
            'company': self.company_id,
            'date_from': self.date_from,
            'date_to': self.date_to,
        }

    def action_print(self):
        return self.env.ref(
            'wecare_sales_management.action_report_sales_analysis'
        ).report_action(self)
