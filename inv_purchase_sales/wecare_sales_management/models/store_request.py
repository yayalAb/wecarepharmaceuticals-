# -*- coding: utf-8 -*-
from odoo import models


class StoreRequest(models.Model):
    _name = 'store.request'
    _inherit = ['store.request', 'wecare.share.mixin']
