# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import float_compare


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    lot_ids = fields.Many2many(
        'stock.lot',
        'sale_order_line_stock_lot_rel',
        'sale_order_line_id',
        'stock_lot_id',
        string='Serial Numbers',
        domain="[('product_id', '=', product_id)]",
        check_company=True,
        copy=False,
        help='Lots / serial numbers to deliver for this sales line.',
    )
    # First selected lot, kept for code and reports that expect a single lot.
    lot_id = fields.Many2one(
        'stock.lot',
        string='Serial Number',
        compute='_compute_lot_id',
        store=True,
        check_company=True,
    )
    expiration_date = fields.Datetime(
        string='Expiration Date',
        compute='_compute_expiration_date',
        store=True,
        help='Earliest expiration date of the selected lots.',
    )
    product_tracking = fields.Selection(
        related='product_id.tracking',
        string='Tracking',
    )
    available_lot_ids = fields.Many2many(
        'stock.lot',
        string='Available Lots',
        compute='_compute_available_lot_ids',
        help='Lots / serials with free stock in the location the line ships from.',
    )

    @api.depends('lot_ids')
    def _compute_lot_id(self):
        for line in self:
            line.lot_id = line.lot_ids[:1]

    @api.depends('lot_ids.expiration_date')
    def _compute_expiration_date(self):
        for line in self:
            dates = [d for d in line.lot_ids.mapped('expiration_date') if d]
            line.expiration_date = min(dates) if dates else False

    def _get_lot_source_location(self):
        """Location the line will be delivered from (whole warehouse by default)."""
        self.ensure_one()
        return self.order_id.warehouse_id.view_location_id

    @api.depends('product_id', 'order_id.warehouse_id')
    def _compute_available_lot_ids(self):
        Quant = self.env['stock.quant']
        for line in self:
            location = line._get_lot_source_location() if line.product_id else False
            if not location or line.product_id.tracking == 'none':
                line.available_lot_ids = line.lot_ids
                continue
            quants = Quant.search([
                ('product_id', '=', line.product_id.id),
                ('location_id', 'child_of', location.id),
                ('lot_id', '!=', False),
                ('quantity', '>', 0),
            ])
            free_lots = quants.filtered(lambda q: q.quantity > q.reserved_quantity).lot_id
            # Keep the lots already on the line selectable (e.g. reserved by this order).
            line.available_lot_ids = free_lots | line.lot_ids

    @api.onchange('product_id')
    def _onchange_product_id_clear_lot(self):
        if self.lot_ids:
            self.lot_ids = self.lot_ids.filtered(lambda lot: lot.product_id == self.product_id)

    @api.onchange('lot_ids')
    def _onchange_lot_ids_serial_qty(self):
        """Serial-tracked products: quantity = number of selected serials."""
        if self.lot_ids and self.product_id.tracking == 'serial':
            self.product_uom_qty = len(self.lot_ids)

    @api.constrains('lot_ids', 'product_id', 'product_uom_qty')
    def _check_lot_matches_product(self):
        for line in self:
            if not line.lot_ids:
                continue
            wrong = line.lot_ids.filtered(lambda lot: lot.product_id != line.product_id)
            if wrong:
                raise ValidationError(_(
                    'Serial/Lot "%(lot)s" does not belong to product "%(product)s".',
                    lot=', '.join(wrong.mapped('display_name')),
                    product=line.product_id.display_name,
                ))
            if (
                line.product_id.tracking == 'serial'
                and float_compare(
                    line.product_uom_qty,
                    len(line.lot_ids),
                    precision_rounding=line.product_uom.rounding if line.product_uom else 0.01,
                ) != 0
            ):
                raise ValidationError(_(
                    'Serial-tracked product "%(product)s": Quantity (%(qty)s) must equal '
                    'the number of selected Serial Numbers (%(count)s).',
                    product=line.product_id.display_name,
                    qty=line.product_uom_qty,
                    count=len(line.lot_ids),
                ))

    def write(self, vals):
        res = super().write(vals)
        if 'lot_ids' in vals:
            self._sync_lot_to_moves_and_invoices()
        return res

    def _sync_lot_to_moves_and_invoices(self):
        """Push serials changed on a confirmed order to its open delivery moves and
        draft invoice lines, so delivery and invoice keep matching the sales order."""
        for line in self:
            moves = line.move_ids.filtered(
                lambda m: m.state not in ('done', 'cancel')
                and m.restrict_lot_ids != line.lot_ids
            )
            if moves:
                moves._do_unreserve()
                moves.write({'restrict_lot_ids': [fields.Command.set(line.lot_ids.ids)]})
                moves.filtered(lambda m: m.state in ('confirmed', 'partially_available'))._action_assign()
            draft_invoice_lines = line.invoice_lines.filtered(
                lambda l: l.move_id.state == 'draft' and l.lot_ids != line.lot_ids
            )
            if draft_invoice_lines:
                draft_invoice_lines.write({'lot_ids': [fields.Command.set(line.lot_ids.ids)]})

    def _get_delivered_lots(self):
        """Lots actually delivered for this line."""
        self.ensure_one()
        return self.move_ids.filtered(lambda m: m.state == 'done').move_line_ids.lot_id

    def _prepare_procurement_values(self, group_id=False):
        values = super()._prepare_procurement_values(group_id=group_id)
        if self.lot_ids:
            values['restrict_lot_ids'] = [fields.Command.set(self.lot_ids.ids)]
        return values

    def _prepare_invoice_line(self, **optional_values):
        res = super()._prepare_invoice_line(**optional_values)
        # Serials from the sales order line; otherwise the lots that were delivered.
        lots = self.lot_ids or self._get_delivered_lots()
        if lots:
            res['lot_ids'] = [fields.Command.set(lots.ids)]
        return res
