from odoo import _, api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.depends('order_line.price_unit', 'order_line.product_uom_qty', 'order_line.discount', 'order_line.tax_id')
    def _compute_tax_totals(self):
        super()._compute_tax_totals()
        for order in self:
            if not order.tax_totals:
                continue

            currency = order.currency_id or order.company_id.currency_id
            company = order.company_id
            date = order.date_order or fields.Date.context_today(order)
            company_currency = company.currency_id

            gross_amount = sum(
                line.price_unit * line.product_uom_qty
                for line in order.order_line
                if not line.display_type
            )
            total_discount = sum(
                line.price_unit * line.product_uom_qty * (line.discount or 0.0) / 100.0
                for line in order.order_line
                if not line.display_type
            )

            if currency:
                gross_amount = currency.round(gross_amount)
                total_discount = currency.round(total_discount)

            if currency and company_currency:
                comp_gross = currency._convert(gross_amount, company_currency, company, date)
                comp_discount = currency._convert(total_discount, company_currency, company, date)
            else:
                comp_gross = gross_amount
                comp_discount = total_discount

            orig_tax_groups = []
            for sub in order.tax_totals.get('subtotals', []):
                orig_tax_groups.extend(sub.get('tax_groups', []))

            # Clean group names: rename "Not Taxable 0%" or "0%" to "Not Taxable"
            for g in orig_tax_groups:
                g_name = (g.get('group_name') or '').strip()
                if 'not taxable' in g_name.lower() or g_name == '0%':
                    g['group_name'] = _('Not Taxable')

            # Ensure any untaxed lines have a "Not Taxable" group if not already present
            has_not_taxable = any('not taxable' in (g.get('group_name') or '').lower() for g in orig_tax_groups)
            lines_without_taxes = order.order_line.filtered(lambda l: not l.display_type and not l.tax_id)
            if lines_without_taxes and not has_not_taxable:
                untaxed_base = sum(l.price_subtotal for l in lines_without_taxes)
                comp_untaxed_base = currency._convert(untaxed_base, company_currency, company, date) if currency and company_currency else untaxed_base
                orig_tax_groups.append({
                    'id': 0,
                    'group_name': _('Not Taxable'),
                    'tax_amount_currency': 0.0,
                    'tax_amount': 0.0,
                    'base_amount_currency': untaxed_base,
                    'base_amount': comp_untaxed_base,
                    'display_base_amount_currency': untaxed_base,
                    'display_base_amount': comp_untaxed_base,
                    'group_label': False,
                })

            order.tax_totals['total_label'] = _('Grand Total')

            if total_discount:
                order.tax_totals['subtotals'] = [
                    {
                        'name': _('Sub Total'),
                        'base_amount_currency': gross_amount,
                        'base_amount': comp_gross,
                        'tax_amount_currency': 0.0,
                        'tax_amount': 0.0,
                        'tax_groups': [],
                    },
                    {
                        'name': _('Discount'),
                        'base_amount_currency': total_discount,
                        'base_amount': comp_discount,
                        'tax_amount_currency': order.tax_totals.get('tax_amount_currency', 0.0),
                        'tax_amount': order.tax_totals.get('tax_amount', 0.0),
                        'tax_groups': orig_tax_groups,
                    },
                ]
            else:
                order.tax_totals['subtotals'] = [
                    {
                        'name': _('Sub Total'),
                        'base_amount_currency': gross_amount,
                        'base_amount': comp_gross,
                        'tax_amount_currency': order.tax_totals.get('tax_amount_currency', 0.0),
                        'tax_amount': order.tax_totals.get('tax_amount', 0.0),
                        'tax_groups': orig_tax_groups,
                    },
                ]
