# -*- coding: utf-8 -*-
from odoo import models


class PurchaseOrder(models.Model):
    _name = 'purchase.order'
    _inherit = ['purchase.order', 'wecare.share.mixin']
