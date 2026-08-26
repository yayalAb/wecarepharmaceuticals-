# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    # purchase_mrp restricts this field to mrp.group_mrp_user, which makes the
    # purchase form crash in OWL for users who can create POs but not MOs.
    mrp_production_count = fields.Integer(
        string="Count of MO Source",
        compute="_compute_mrp_production_count",
        groups="",
    )

    @api.depends("order_line.move_dest_ids.group_id.mrp_production_ids")
    def _compute_mrp_production_count(self):
        for purchase in self:
            if hasattr(purchase, "_get_mrp_productions"):
                purchase.mrp_production_count = len(purchase._get_mrp_productions())
            else:
                purchase.mrp_production_count = 0

    def action_view_mrp_productions(self):
        self.ensure_one()
        productions = (
            self._get_mrp_productions()
            if hasattr(self, "_get_mrp_productions")
            else self.env["mrp.production"]
        )
        action = {
            "res_model": "mrp.production",
            "type": "ir.actions.act_window",
        }
        if len(productions) == 1:
            action.update({
                "view_mode": "form",
                "res_id": productions.id,
            })
        else:
            action.update({
                "name": _("Manufacturing Source of %s", self.name),
                "domain": [("id", "in", productions.ids)],
                "view_mode": "list,form",
            })
        return action
