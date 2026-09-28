from odoo import _, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _get_total_discount_amount(self):
        """Sum of line discounts (price before discount - price after), in invoice currency."""
        self.ensure_one()
        total_discount = sum(
            line.price_unit * line.quantity * line.discount / 100
            for line in self.invoice_line_ids
            if line.display_type == 'product'
        )
        return self.currency_id.round(total_discount)

    def _compute_tax_totals(self):
        super()._compute_tax_totals()
        for move in self:
            if not move.tax_totals or not move.is_sale_document(include_receipts=True):
                continue

            total_discount = move._get_total_discount_amount()
            company_discount = move.currency_id._convert(
                total_discount,
                move.company_id.currency_id,
                move.company_id,
                move.invoice_date or fields.Date.context_today(move),
            )
            move.tax_totals['subtotals'].append({
                'name': _('Total Discount'),
                'base_amount_currency': total_discount,
                'base_amount': company_discount,
                'tax_amount_currency': 0.0,
                'tax_amount': 0.0,
                'tax_groups': [],
            })
