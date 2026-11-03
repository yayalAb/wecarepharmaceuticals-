# -*- coding: utf-8 -*-
from odoo import api, fields, models

CUSTOMER_TYPES = [
    ('pharmacy', 'Pharmacy'),
    ('hospital', 'Hospital'),
    ('distributor', 'Wholesales'),
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
        domain="[]",
    )
    telegram_username = fields.Char(
        string='Telegram Username',
        help='Telegram username without @, used by Share to Media.',
    )
    customer_address = fields.Char(
        string='Address',
        compute='_compute_customer_address',
        store=True,
        readonly=False,
        help='Full address of the customer.',
    )
    contact_name = fields.Char(
        string='Contact Name',
        compute='_compute_contact_person',
        store=True,
        readonly=False,
        help='Name of the primary contact person for this customer.',
    )
    contact_phone = fields.Char(
        string='Contact Phone',
        compute='_compute_contact_person',
        store=True,
        readonly=False,
        help='Phone number of the primary contact person.',
    )

    @api.depends('street', 'street2', 'city', 'state_id', 'country_id')
    def _compute_customer_address(self):
        for partner in self:
            parts = [
                partner.street,
                partner.street2,
                partner.city,
                partner.state_id.name if partner.state_id else False,
                partner.country_id.name if partner.country_id else False,
            ]
            addr = ', '.join([p.strip() for p in parts if p and p.strip()])
            if addr:
                partner.customer_address = addr
            elif not partner.customer_address:
                partner.customer_address = ''

    @api.depends('child_ids', 'child_ids.name', 'child_ids.phone', 'child_ids.mobile', 'child_ids.type',
                 'is_company', 'name', 'phone', 'mobile')
    def _compute_contact_person(self):
        for partner in self:
            if partner.is_company:
                contacts = partner.child_ids.filtered(
                    lambda c: c.type == 'contact') or partner.child_ids
                if contacts:
                    first = contacts[0]
                    partner.contact_name = first.name or ''
                    partner.contact_phone = first.phone or first.mobile or ''
                else:
                    if not partner.contact_name:
                        partner.contact_name = ''
                    if not partner.contact_phone:
                        partner.contact_phone = ''
            else:
                if not partner.contact_name:
                    partner.contact_name = partner.name or ''
                if not partner.contact_phone:
                    partner.contact_phone = partner.phone or partner.mobile or ''

    @api.onchange('street', 'street2', 'city', 'state_id', 'country_id')
    def _onchange_address_fields(self):
        parts = [
            self.street,
            self.street2,
            self.city,
            self.state_id.name if self.state_id else False,
            self.country_id.name if self.country_id else False,
        ]
        addr = ', '.join([p.strip() for p in parts if p and p.strip()])
        if addr:
            self.customer_address = addr

    @api.onchange('child_ids')
    def _onchange_child_ids_contact(self):
        if self.is_company:
            contacts = self.child_ids.filtered(
                lambda c: c.type == 'contact') or self.child_ids
            if contacts:
                self.contact_name = contacts[0].name or ''
                self.contact_phone = contacts[0].phone or contacts[0].mobile or ''
