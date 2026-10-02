# -*- coding: utf-8 -*-
from odoo import api, fields, models


class SaleOrder(models.Model):
    _name = 'sale.order'
    _inherit = ['sale.order', 'wecare.share.mixin', 'wecare.sales.voucher.mixin']

    stock_location_id = fields.Many2one(
        'stock.location',
        string='Stock Location',
        domain="[('usage', '=', 'internal'), ('warehouse_id', '=?', warehouse_id), "
               "'|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        check_company=True,
        compute='_compute_stock_location_id',
        store=True,
        readonly=False,
        precompute=True,
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

    @api.depends('warehouse_id')
    def _compute_stock_location_id(self):
        # Default = main stock of the order's warehouse; a location chosen by hand is kept
        # as long as it belongs to that warehouse.
        for order in self:
            warehouse = order.warehouse_id
            if warehouse and order.stock_location_id.warehouse_id != warehouse:
                order.stock_location_id = warehouse.lot_stock_id
            else:
                order.stock_location_id = order.stock_location_id

    def _wecare_voucher_header(self):
        self.ensure_one()
        prepared = self.get_proforma_prepared_by()
        approved = self.get_proforma_approved_by()
        salesperson = self.user_id
        salesperson_phone = salesperson.partner_id.phone or salesperson.partner_id.mobile
        return {
            'title': 'Sales Quotation' if self.state in ('draft', 'sent') else 'Sales Order',
            'to': self.partner_id.display_name or '',
            'tin': self.get_proforma_tin(),
            'address': self._wecare_partner_address(self.partner_id),
            'fs_no': self.fs_no or '',
            'mrc_no': self.mrc_no or '',
            'remark': self.note,
            'voucher_no': self.name,
            'date': self._wecare_fmt_date(self.date_order, with_time=True),
            'store': self.warehouse_id.name or '',
            'payment': self.get_sales_attachment_payment_method(),
            'source': salesperson.name or '',
            'source_tin': '',
            'source_address': f'Tel. {salesperson_phone}' if salesperson_phone else '',
            'prepared_by': prepared.name or '',
            'prepared_on': self._wecare_fmt_date(self.create_date, with_time=True),
            'approved_by': approved.name if approved else '',
            'issued_by': '',
            'received_by': '',
        }

    def _wecare_voucher_lines(self):
        self.ensure_one()
        lines = []
        for line in self.order_line.filtered(lambda l: not l.display_type):
            product = line.product_id
            lines.append({
                'code': product.default_code or '',
                'name': product.name or line.name or '',
                'lots': self._wecare_lot_lines(product, line.lot_ids, line.move_ids),
                'qty': line.product_uom_qty,
                'uom': line.product_uom.name or '',
                'price': line.price_unit,
                'subtotal': line.price_subtotal,
                'taxed': bool(line.tax_id),
                'discount': line.price_unit * line.product_uom_qty * (line.discount or 0.0) / 100,
            })
        return lines

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
