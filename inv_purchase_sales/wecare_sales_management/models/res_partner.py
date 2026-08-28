# -*- coding: utf-8 -*-
from odoo import fields, models

CUSTOMER_TYPES = [
    ('pharmacy', 'Pharmacy'),
    ('hospital', 'Hospital'),
    ('distributor', 'Distributor'),
    ('clinic', 'Clinic'),
    ('ngo', 'NGO'),
]


class ResPartner(models.Model):
    _inherit = 'res.partner'

    wecare_customer_type = fields.Selection(
        CUSTOMER_TYPES,
        string='Customer Type',
        tracking=True,
    )
    wecare_territory_id = fields.Many2one(
        'wecare.sales.territory',
        string='Sales Territory',
        tracking=True,
        check_company=True,
    )
    telegram_username = fields.Char(
        string='Telegram Username',
        help='Telegram username without @, used by Share to Media.',
    )
