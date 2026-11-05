# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    company_stamp = fields.Binary(
        string='Company Stamp',
        help='Company Stamp for the company, used in outgoing letters and reports.')
