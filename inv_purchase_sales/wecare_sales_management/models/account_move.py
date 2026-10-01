# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _name = 'account.move'
    _inherit = ['account.move', 'wecare.share.mixin']

    wecare_warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Warehouse',
        check_company=True,
        compute='_compute_wecare_warehouse_location',
        store=True,
        readonly=False,
        help='Warehouse carried from the quotation / sales order.',
    )
    stock_location_id = fields.Many2one(
        'stock.location',
        string='Stock Location',
        domain="[('usage', '=', 'internal'), ('warehouse_id', '=?', wecare_warehouse_id), "
               "'|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        check_company=True,
        compute='_compute_wecare_warehouse_location',
        store=True,
        readonly=False,
        help='Default source location for the invoice lines. '
             'Stock is deducted from the line locations when the invoice is validated.',
    )

    @api.depends('invoice_line_ids.sale_line_ids')
    def _compute_wecare_warehouse_location(self):
        # Carry the warehouse / location selected on the quotation / sales order.
        for move in self:
            orders = move.invoice_line_ids.sale_line_ids.order_id
            if not orders:
                move.wecare_warehouse_id = move.wecare_warehouse_id
                move.stock_location_id = move.stock_location_id
                continue
            order = orders[:1]
            move.wecare_warehouse_id = order.warehouse_id or move.wecare_warehouse_id
            move.stock_location_id = (
                order.stock_location_id
                or move.invoice_line_ids.sale_line_ids.stock_location_id[:1]
                or order.warehouse_id.lot_stock_id
                or move.stock_location_id
            )

    @api.onchange('wecare_warehouse_id')
    def _onchange_wecare_warehouse_id(self):
        warehouse = self.wecare_warehouse_id
        if warehouse and self.stock_location_id.warehouse_id != warehouse:
            self.stock_location_id = warehouse.lot_stock_id

    @api.onchange('stock_location_id')
    def _onchange_stock_location_id(self):
        # Apply the header location to every product line, as on the sales order.
        if not self.stock_location_id:
            return
        for line in self.invoice_line_ids.filtered(lambda l: l.display_type == 'product'):
            line.stock_location_id = self.stock_location_id

    def action_post(self):
        res = super().action_post()
        self._wecare_deduct_stock_on_invoice()
        return res

    def _wecare_deduct_stock_on_invoice(self):
        """Deduct stock when the customer invoice is validated, not when the DO is clicked.

        Related outgoing pickings are confirmed, reserved and validated automatically.
        """
        invoices = self.filtered(
            lambda m: m.move_type == 'out_invoice'
            and m.company_id.wecare_deduct_stock_on_invoice
        )
        for invoice in invoices:
            orders = invoice.invoice_line_ids.sale_line_ids.order_id
            pickings = orders.picking_ids.filtered(
                lambda p: p.picking_type_code == 'outgoing'
                and p.state not in ('done', 'cancel')
            )
            invoice._wecare_sync_locations_to_pickings(pickings)
            for picking in pickings:
                invoice._wecare_validate_picking(picking)

    def _wecare_sync_locations_to_pickings(self, pickings):
        """Deduct from the location selected on the invoice line.

        A location changed on the draft invoice is written back to the sales order line and
        to the pending delivery moves, so the delivery takes stock from the same location.
        """
        self.ensure_one()
        for line in self.invoice_line_ids.filtered(
            lambda l: l.display_type == 'product' and l.stock_location_id
        ):
            location = line.stock_location_id
            sale_lines = line.sale_line_ids.filtered(lambda sl: sl.stock_location_id != location)
            if not sale_lines:
                continue
            sale_lines.stock_location_id = location
            moves = pickings.move_ids.filtered(
                lambda m: m.sale_line_id in sale_lines
                and m.state not in ('done', 'cancel')
                and m.location_id != location
            )
            if moves:
                moves._do_unreserve()
                moves.write({'location_id': location.id})

    def _wecare_validate_picking(self, picking):
        self.ensure_one()
        try:
            if picking.state == 'draft':
                picking.action_confirm()
            picking.action_assign()
            picking._wecare_set_quantities_to_done()
            picking.with_context(
                skip_immediate=True,
                skip_backorder=True,
                skip_sms=True,
                cancel_backorder=True,
            ).button_validate()
        except UserError as err:
            raise UserError(self.env._(
                'Cannot deduct stock for invoice %(invoice)s from delivery %(picking)s:\n%(error)s',
                invoice=self.name,
                picking=picking.display_name,
                error=err,
            )) from err
