# -*- coding: utf-8 -*-
from odoo import models


class StockPicking(models.Model):
    _name = 'stock.picking'
    _inherit = ['stock.picking', 'wecare.share.mixin']

    def _wecare_share_report_xmlid(self):
        if self.picking_type_code == 'outgoing':
            return 'stock.action_report_delivery'
        return 'stock.action_report_picking'

    def _wecare_set_quantities_to_done(self):
        """Mark reserved quantities as picked so invoice posting can validate the DO."""
        for picking in self:
            moves = picking.move_ids.filtered(lambda m: m.state not in ('done', 'cancel'))
            for move in moves:
                if not move.quantity:
                    move.quantity = move.product_uom_qty
                move.picked = True
                move.move_line_ids.picked = True
