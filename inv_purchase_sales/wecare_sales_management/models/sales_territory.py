# -*- coding: utf-8 -*-
from odoo import fields, models


class WecareSalesTerritory(models.Model):
    _name = 'wecare.sales.territory'
    _description = 'Sales Territory'
    _order = 'name'

    name = fields.Char(required=True)
    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
    )
    salesperson_ids = fields.Many2many(
        'res.users',
        string='Salespersons',
    )
    active = fields.Boolean(default=True)
