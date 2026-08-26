# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import float_compare


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    lot_id = fields.Many2one(
        'stock.lot',
        string='Serial Number',
        domain="[('product_id', '=', product_id)]",
        check_company=True,
        copy=False,
        help='Lot or serial number to deliver for this sales line.',
    )
    expiration_date = fields.Datetime(
        string='Expiration Date',
        related='lot_id.expiration_date',
        store=True,
        readonly=True,
    )
    product_tracking = fields.Selection(
        related='product_id.tracking',
        string='Tracking',
    )

    @api.onchange('product_id')
    def _onchange_product_id_clear_lot(self):
        if self.lot_id and self.lot_id.product_id != self.product_id:
            self.lot_id = False

    @api.onchange('lot_id')
    def _onchange_lot_id_serial_qty(self):
        """Serial-tracked products must be sold as quantity 1 per line."""
        if (
            self.lot_id
            and self.product_id.tracking == 'serial'
            and float_compare(
                self.product_uom_qty,
                1.0,
                precision_rounding=self.product_uom.rounding if self.product_uom else 0.01,
            ) != 0
        ):
            self.product_uom_qty = 1.0

    @api.constrains('lot_id', 'product_id', 'product_uom_qty')
    def _check_lot_matches_product(self):
        for line in self:
            if not line.lot_id:
                continue
            if line.lot_id.product_id != line.product_id:
                raise ValidationError(_(
                    'Serial/Lot "%(lot)s" does not belong to product "%(product)s".',
                    lot=line.lot_id.display_name,
                    product=line.product_id.display_name,
                ))
            if (
                line.product_id.tracking == 'serial'
                and float_compare(
                    line.product_uom_qty,
                    1.0,
                    precision_rounding=line.product_uom.rounding if line.product_uom else 0.01,
                ) != 0
            ):
                raise ValidationError(_(
                    'Serial-tracked product "%(product)s" must have Quantity = 1 '
                    'when a Serial Number is selected.',
                    product=line.product_id.display_name,
                ))

    def _prepare_procurement_values(self, group_id=False):
        values = super()._prepare_procurement_values(group_id=group_id)
        if self.lot_id:
            values['restrict_lot_id'] = self.lot_id.id
        return values

    def _prepare_invoice_line(self, **optional_values):
        res = super()._prepare_invoice_line(**optional_values)
        if self.lot_id:
            res['lot_id'] = self.lot_id.id
        return res
