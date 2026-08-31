# -*- coding: utf-8 -*-
from odoo import models


class SuppliesRfp(models.Model):
    _name = 'supplies.rfp'
    _inherit = ['supplies.rfp', 'wecare.share.mixin']

    def _wecare_share_report_xmlid(self):
        return 'purchase_request.action_report_purchase_request'
