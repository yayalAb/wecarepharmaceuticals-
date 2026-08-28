# -*- coding: utf-8 -*-
from odoo import fields, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _name = 'account.move'
    _inherit = ['account.move', 'wecare.share.mixin']

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
            for picking in pickings:
                invoice._wecare_validate_picking(picking)

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
