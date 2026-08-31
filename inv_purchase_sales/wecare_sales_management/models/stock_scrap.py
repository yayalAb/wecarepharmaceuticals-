# -*- coding: utf-8 -*-
from odoo import models


class StockScrap(models.Model):
    _name = 'stock.scrap'
    _inherit = ['stock.scrap', 'wecare.share.mixin']
