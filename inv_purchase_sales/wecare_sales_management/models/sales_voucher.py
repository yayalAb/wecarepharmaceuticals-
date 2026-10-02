# -*- coding: utf-8 -*-
from odoo import fields, models

COPY_DISTRIBUTION = (
    'Original Copy - Customer , 1st Copy - Accountant , 2nd Copy - Store Manager , '
    '3rd Copy - FMHACA , 4th Copy - Z Report'
)


class WecareSalesVoucherMixin(models.AbstractModel):
    """Data for the "Sales Voucher" print shared by sales orders and customer invoices.

    Each document implements ``_wecare_voucher_header()`` and ``_wecare_voucher_lines()``;
    the QWeb template ``wecare_sales_management.sales_voucher_body`` only renders the dict
    returned by ``_wecare_voucher_values()``.
    """
    _name = 'wecare.sales.voucher.mixin'
    _description = 'WeCare Sales Voucher Print'

    # ------------------------------------------------------------------ helpers
    def _wecare_fmt_date(self, value, with_time=False):
        if not value:
            return ''
        if with_time:
            value = fields.Datetime.context_timestamp(self, value)
            return value.strftime('%d-%b-%y %I:%M:%S %p')
        return value.strftime('%d-%b-%y')

    def _wecare_lot_text(self, product, lot_name, expiry):
        label = 'Serial No' if product.tracking == 'serial' else 'Batch No'
        text = f'[{label} : {lot_name}]'
        if expiry:
            text += f' [Exp. Date : {expiry:%d-%b-%y}]'
        return text

    def _wecare_lot_lines(self, product, lots, moves):
        """Lot lines for one document line: the lots chosen on the line, otherwise the
        lots actually picked on the related stock moves."""
        if lots:
            return [self._wecare_lot_text(product, lot.name, lot.expiration_date) for lot in lots]
        lines = []
        for move in moves.filtered(lambda m: m.state != 'cancel'):
            for text in move.get_report_lot_lines():
                if text not in lines:
                    lines.append(text)
        return lines

    def _wecare_partner_address(self, partner):
        parts = [partner.contact_address_complete or '']
        phone = partner.phone or partner.mobile
        if phone:
            parts.append(f'Tel. {phone}')
        return ' '.join(p for p in parts if p)

    def _wecare_tax_rows(self, lines):
        """(label, base, tax) rows below Sub Total: one per tax group, plus
        "Not Taxable" for the lines without taxes."""
        rows = []
        for subtotal in (self.tax_totals or {}).get('subtotals', []):
            for group in subtotal.get('tax_groups', []):
                rows.append((
                    group.get('group_name'),
                    group.get('display_base_amount_currency', group.get('base_amount_currency', 0.0)),
                    group.get('tax_amount_currency', 0.0),
                ))
        untaxed = sum(line['subtotal'] for line in lines if not line['taxed'])
        if untaxed or not rows:
            rows.append(('Not Taxable', untaxed, 0.0))
        return rows

    # --------------------------------------------------------------- interface
    def _wecare_voucher_header(self):
        raise NotImplementedError

    def _wecare_voucher_lines(self):
        raise NotImplementedError

    def _wecare_voucher_values(self):
        self.ensure_one()
        currency = self.currency_id or self.company_id.currency_id
        lines = self._wecare_voucher_lines()
        values = {
            'currency': currency,
            'lines': lines,
            'subtotal': self.amount_untaxed,
            'discount': sum(line['discount'] for line in lines),
            'tax_rows': self._wecare_tax_rows(lines),
            'grand_total': self.amount_total,
            'copy_distribution': COPY_DISTRIBUTION,
            'company_tin': self.company_id.vat or '',
            'company_vat': '',
            'cart': '',
            'distribution': '',
        }
        values.update(self._wecare_voucher_header())
        return values
