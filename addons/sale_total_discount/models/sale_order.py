from odoo import _, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _compute_tax_totals(self):
        super()._compute_tax_totals()
        for order in self:
            if not order.tax_totals:
                continue

            total_discount = sum(
                line.price_unit * line.product_uom_qty * line.discount / 100
                for line in order.order_line
                if not line.display_type
            )
            total_discount = order.currency_id.round(total_discount)
            company_discount = order.currency_id._convert(
                total_discount,
                order.company_id.currency_id,
                order.company_id,
                order.date_order or fields.Date.context_today(order),
            )
            order.tax_totals['subtotals'].append({
                'name': _('Total Discount'),
                'base_amount_currency': total_discount,
                'base_amount': company_discount,
                'tax_amount_currency': 0.0,
                'tax_amount': 0.0,
                'tax_groups': [],
            })
