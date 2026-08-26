# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.osv import expression


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _requires_registration_fields(self):
        """Top-level customer/vendor records (not child contacts or addresses)."""
        self.ensure_one()
        return not self.parent_id

    # Odoo 16/17 → 18 / orphaned-module compatibility stubs.
    duplicate_bank_partner_ids = fields.Many2many(
        'res.partner',
        compute='_compute_duplicate_bank_partner_ids',
        string='Partners with same bank',
    )
    available_peppol_eas = fields.Char(
        string='Available Peppol EAS',
        compute='_compute_available_peppol_eas',
    )
    # From missing module account_add_gln (was installed, code not on disk).
    global_location_number = fields.Char(
        string='GLN',
        help='Global Location Number (compatibility field).',
    )

    def _compute_duplicate_bank_partner_ids(self):
        PartnerBank = self.env['res.partner.bank']
        for partner in self:
            others = self.env['res.partner']
            if partner.bank_ids:
                domains = [
                    [('acc_number', '=', bank.acc_number), ('partner_id', '!=', partner.id)]
                    for bank in partner.bank_ids
                ]
                if domains:
                    others = PartnerBank.search(expression.OR(domains)).mapped('partner_id')
            partner.duplicate_bank_partner_ids = others

    def _compute_available_peppol_eas(self):
        for partner in self:
            partner.available_peppol_eas = False

    @api.constrains('vat', 'phone', 'parent_id')
    def _check_registration_required_fields(self):
        for partner in self:
            if not partner._requires_registration_fields():
                continue
            if not (partner.vat or '').strip():
                raise ValidationError(_(
                    'Tax ID is required when registering a customer or vendor.'
                ))
            if not (partner.phone or '').strip():
                raise ValidationError(_(
                    'Phone is required when registering a customer or vendor.'
                ))
