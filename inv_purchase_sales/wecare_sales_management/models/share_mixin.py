# -*- coding: utf-8 -*-
from odoo import models


REPORT_XMLIDS = {
    'sale.order': 'sale.action_report_saleorder',
    'account.move': 'account.account_invoices',
    'stock.picking': 'stock.action_report_picking',
    'purchase.order': 'purchase.action_report_purchase_order',
    'account.payment': False,
    'supplies.rfp': 'purchase_request.action_report_purchase_request',
    'stock.scrap': False,
    'store.request': False,
}


class WecareShareMixin(models.AbstractModel):
    _name = 'wecare.share.mixin'
    _description = 'Share to Media Mixin'

    def action_share_to_media(self):
        self.ensure_one()
        partner = self._wecare_share_partner()
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._('Share to Media'),
            'res_model': 'wecare.share.media.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_res_model': self._name,
                'default_res_id': self.id,
                'default_document_name': self.display_name,
                'default_partner_id': partner.id if partner else False,
                'default_report_xmlid': self._wecare_share_report_xmlid() or False,
            },
        }

    def _wecare_share_partner(self):
        self.ensure_one()
        if 'partner_id' in self._fields and self.partner_id:
            return self.partner_id
        return self.env['res.partner']

    def _wecare_share_report_xmlid(self):
        return REPORT_XMLIDS.get(self._name)
