from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    # Referenced by sale.order form views leftover from Odoo 17 / other modules.
    translated_product_name = fields.Text(
        compute="_compute_translated_product_name",
    )

    @api.depends("product_id", "order_id.partner_id")
    def _compute_translated_product_name(self):
        for line in self:
            if not line.product_id:
                line.translated_product_name = False
                continue
            lang = line.order_id._get_lang() if line.order_id else False
            line.translated_product_name = line.product_id.with_context(
                lang=lang,
            ).display_name


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    currency_id = fields.Many2one(
        readonly=False,
    )

    @api.depends('pricelist_id', 'company_id')
    def _compute_currency_id(self):
        for order in self:
            if order.pricelist_id:
                order.currency_id = (
                    order.pricelist_id.currency_id or order.company_id.currency_id
                )
            elif not order.currency_id:
                order.currency_id = order.company_id.currency_id

    proforma_checked_by_id = fields.Many2one(
        'res.users', string='Proforma Checked By', readonly=True,
    )
    fs_no = fields.Char(string='FS No')
    mrc_no = fields.Char(string='MRC No')
    payment_method = fields.Selection(
        selection=[
            ('cash', 'Cash'),
            ('credit', 'Credit'),
        ],
        string='Payment Method',
    )
    driver_name = fields.Char(string='Driver')
    driver_phone = fields.Char(string='Phone No')

    def _sync_driver_to_pickings(self):
        for order in self:
            pickings = order.picking_ids.filtered(
                lambda p: p.state not in ('done', 'cancel')
            )
            pickings.write({
                'driver_name': order.driver_name,
                'driver_phone': order.driver_phone,
            })

    def write(self, vals):
        res = super().write(vals)
        if {'driver_name', 'driver_phone'} & set(vals):
            self._sync_driver_to_pickings()
        return res

    @api.constrains('order_line')
    def _check_order_line_required(self):
        for order in self:
            if order.state == 'cancel':
                continue
            product_lines = order.order_line.filtered(lambda l: not l.display_type)
            if not product_lines:
                raise ValidationError(_("Please add at least one product line to the sales quotation/order."))

    def action_quotation_submit(self):
        for order in self:
            product_lines = order.order_line.filtered(lambda l: not l.display_type)
            if not product_lines:
                raise ValidationError(_("Please add at least one product line to the sales quotation/order."))
        if hasattr(super(), 'action_quotation_submit'):
            return super().action_quotation_submit()
        return True

    def action_confirm(self):
        for order in self:
            product_lines = order.order_line.filtered(lambda l: not l.display_type)
            if not product_lines:
                raise ValidationError(_("Please add at least one product line to the sales quotation/order."))
        missing = self.filtered(lambda o: not o.payment_method)
        if missing:
            raise UserError(_(
                'Please select a Payment Method before confirming: %s',
                ', '.join(missing.mapped('name')),
            ))
        res = super().action_confirm()
        for order in self:
            if hasattr(order, 'approved_by_id') and not order.approved_by_id:
                order.approved_by_id = self.env.user.id
            if hasattr(order, 'approved_date') and not order.approved_date:
                order.approved_date = fields.Date.today()
        self._sync_driver_to_pickings()
        return res

    def _prepare_invoice(self):
        invoice_vals = super()._prepare_invoice()
        # FS No is assigned by sequence on the invoice; MRC comes from company config.
        invoice_vals.update({
            'mrc_no': self.company_id.invoice_mrc_no or False,
            'payment_method': self.payment_method,
        })
        invoice_vals.pop('fs_no', None)
        return invoice_vals

    def get_proforma_total_discount(self):
        self.ensure_one()
        total_discount = sum(
            line.price_unit * line.product_uom_qty * line.discount / 100
            for line in self.order_line
            if not line.display_type
        )
        return (self.currency_id or self.company_id.currency_id).round(total_discount)

    def get_proforma_amount_in_words(self):
        self.ensure_one()
        total = self.amount_total
        currency = self.currency_id or self.company_id.currency_id
        if not currency or not total:
            return ''
        return currency.amount_to_text(total)

    def get_proforma_prepared_by(self):
        self.ensure_one()
        return getattr(self, 'prepared_by_id', False) or self.create_uid

    def get_proforma_approved_by(self):
        self.ensure_one()
        if getattr(self, 'approved_by_id', False):
            return self.approved_by_id
        if self.state in ('sale', 'done'):
            confirm_subtype = self.env.ref('sale.mt_order_confirmed', raise_if_not_found=False)
            if confirm_subtype:
                confirm_msg = self.message_ids.filtered(lambda m: m.subtype_id == confirm_subtype)[:1]
                if confirm_msg and confirm_msg.author_id and confirm_msg.author_id.user_ids:
                    return confirm_msg.author_id.user_ids[0]
            for msg in self.message_ids:
                for track in msg.tracking_value_ids:
                    if track.field_id.name == 'state' and track.new_value_char in ('Sales Order', 'sale'):
                        if msg.author_id and msg.author_id.user_ids:
                            return msg.author_id.user_ids[0]
            if self.write_uid:
                return self.write_uid
        return False

    def get_proforma_prepared_date(self):
        self.ensure_one()
        if getattr(self, 'prepared_date', False):
            return self.prepared_date
        return self.date_order.date() if self.date_order else False

    def get_proforma_approved_date(self):
        self.ensure_one()
        if getattr(self, 'approved_date', False):
            return self.approved_date
        if self.state == 'sale' and self.write_date:
            return self.write_date.date()
        return False

    def get_proforma_line_remark(self, line):
        return getattr(line, 'report_remark', False) or ''

    def get_proforma_tin(self):
        self.ensure_one()
        if getattr(self, 'partner_tin', False):
            return self.partner_tin
        return self.partner_id.vat or ''

    def get_proforma_term_condition(self):
        self.ensure_one()
        if getattr(self, 'report_remark', False):
            return self.report_remark
        return self.note or ''

    def get_proforma_order_lines(self):
        self.ensure_one()
        return self.order_line.filtered(lambda line: not line.display_type)

    def get_sales_attachment_fs_no(self):
        self.ensure_one()
        return self.fs_no or ''

    def get_sales_attachment_mrc_no(self):
        self.ensure_one()
        return self.mrc_no or ''

    def get_sales_attachment_payment_method(self):
        self.ensure_one()
        return dict(self._fields['payment_method'].selection).get(self.payment_method, '')
