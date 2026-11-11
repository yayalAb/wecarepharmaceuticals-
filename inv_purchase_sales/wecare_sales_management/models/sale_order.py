# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.osv import expression


class SaleOrder(models.Model):
    _name = 'sale.order'
    _inherit = ['sale.order', 'wecare.share.mixin', 'wecare.sales.voucher.mixin']

    @api.depends('name', 'invoice_ids.name', 'invoice_ids.fs_no', 'invoice_ids.state', 'invoice_ids.move_type')
    def _compute_display_name(self):
        super()._compute_display_name()
        for order in self:
            invoices = order.invoice_ids.filtered(
                lambda m: m.move_type == 'out_invoice' and m.state != 'cancel'
            )
            posted = invoices.filtered(lambda m: m.state == 'posted')
            target = posted or invoices
            inv_labels = []
            for inv in target[:2]:
                inv_no = (inv.name or '').strip()
                if inv_no == '/':
                    inv_no = ''
                fs = (getattr(inv, 'fs_no', False) or getattr(order, 'fs_no', False) or '').strip()
                if fs == '/':
                    fs = ''
                if inv_no and fs:
                    inv_labels.append(f"{inv_no} - {fs}")
                elif inv_no:
                    inv_labels.append(inv_no)
                elif fs:
                    inv_labels.append(fs)
            if not inv_labels and getattr(order, 'fs_no', False):
                fs = str(order.fs_no).strip()
                if fs and fs != '/':
                    inv_labels.append(fs)
            if inv_labels:
                base_name = order.name or order.display_name or ''
                order.display_name = f"{base_name} ({', '.join(inv_labels)})"

    @api.model
    def _name_search(self, name='', domain=None, operator='ilike', limit=100, order=None):
        domain = list(domain or [])
        if name:
            name_domain = ['|', '|', '|',
                ('name', operator, name),
                ('client_order_ref', operator, name),
                ('invoice_ids.name', operator, name),
                ('invoice_ids.fs_no', operator, name),
            ]
            domain = expression.AND([domain, name_domain])
            return super()._name_search(name='', domain=domain, operator=operator, limit=limit, order=order)
        return super()._name_search(name=name, domain=domain, operator=operator, limit=limit, order=order)

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
    original_doc_request_ids = fields.One2many(
        'wecare.original.document.request',
        'sales_order_id',
        string='Original Document Requests',
    )
    original_doc_request_count = fields.Integer(
        string='Doc Request Count',
        compute='_compute_original_doc_request_count',
    )

    def _compute_original_doc_request_count(self):
        for order in self:
            order.original_doc_request_count = len(order.original_doc_request_ids)

    def action_view_original_doc_requests(self):
        self.ensure_one()
        return {
            'name': self.env._('Original Document Requests'),
            'type': 'ir.actions.act_window',
            'res_model': 'wecare.original.document.request',
            'view_mode': 'list,form',
            'domain': [('sales_order_id', '=', self.id)],
            'context': {
                'default_sales_order_id': self.id,
                'default_requested_person': self.env.user.id,
            },
        }

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
        salesperson_phone = (
            salesperson.partner_id.phone
            or salesperson.partner_id.mobile
            or getattr(salesperson, 'phone', False)
            or getattr(salesperson, 'mobile', False)
            or ''
        ) if salesperson else ''
        salesperson_phone_str = f"Tel. {salesperson_phone}" if salesperson_phone else ''
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
            'salesperson': salesperson.name or '' if salesperson else '',
            'salesperson_phone': salesperson_phone_str,
            'source': salesperson.name or '' if salesperson else '',
            'source_tin': '',
            'source_address': salesperson_phone_str,
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
