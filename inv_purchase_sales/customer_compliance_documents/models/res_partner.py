# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    compliance_document_ids = fields.One2many(
        'customer.compliance.document',
        'partner_id',
        string='Compliance Documents',
    )
    compliance_document_count = fields.Integer(
        string='Compliance Documents',
        compute='_compute_compliance_document_count',
    )
    compliance_status = fields.Selection(
        [
            ('ok', 'Compliant'),
            ('warning', 'Expiring Soon'),
            ('blocked', 'Non-Compliant'),
            ('none', 'No Documents'),
        ],
        string='Compliance Status',
        compute='_compute_compliance_status',
        store=True,
    )
    # Compatibility stubs for stale partner-form views left in the database
    # (migrations / uninstalled modules). Prefer deactivation via pre_init_hook.
    duplicate_bank_partner_ids = fields.Many2many(
        'res.partner',
        compute='_compute_duplicate_bank_partner_ids',
        string='Partners with same bank',
    )
    available_peppol_eas = fields.Char(
        string='Available Peppol EAS',
        compute='_compute_available_peppol_eas',
    )

    def _compute_duplicate_bank_partner_ids(self):
        for partner in self:
            other_partners = self.env['res.partner']
            if hasattr(partner, '_get_duplicated_bank_accounts'):
                other_partners = (
                    partner._get_duplicated_bank_accounts().mapped('partner_id')
                    - partner
                )
            partner.duplicate_bank_partner_ids = other_partners

    def _compute_available_peppol_eas(self):
        for partner in self:
            partner.available_peppol_eas = False

    @api.depends('compliance_document_ids')
    def _compute_compliance_document_count(self):
        for partner in self:
            partner.compliance_document_count = len(partner.compliance_document_ids)

    @api.depends(
        'compliance_document_ids',
        'compliance_document_ids.status',
        'compliance_document_ids.document_type_id',
        'compliance_document_ids.document_type_id.is_required',
    )
    def _compute_compliance_status(self):
        for partner in self:
            docs = partner.compliance_document_ids
            if not docs:
                partner.compliance_status = 'none'
                continue
            if partner._get_compliance_issues(for_blocking=False):
                partner.compliance_status = 'blocked'
            elif any(d.status == 'expiring_soon' for d in docs):
                partner.compliance_status = 'warning'
            else:
                partner.compliance_status = 'ok'

    def _commercial_partner_for_compliance(self):
        """Use the commercial entity for compliance checks."""
        self.ensure_one()
        return self.commercial_partner_id or self

    def _get_compliance_issues(self, for_blocking=True):
        """Return list of human-readable compliance blockers for this partner."""
        self.ensure_one()
        partner = self._commercial_partner_for_compliance()
        company = self.env.company
        docs = partner.compliance_document_ids

        if for_blocking and not company.compliance_block_sale_orders:
            return []

        issues = []
        required_types = self.env['customer.compliance.document.type'].search([
            ('is_required', '=', True),
            ('active', '=', True),
            '|',
            ('company_id', '=', False),
            ('company_id', '=', company.id),
        ])

        if required_types:
            for doc_type in required_types:
                matching = docs.filtered(
                    lambda d, t=doc_type: d.document_type_id == t and d.is_acceptable_for_sales()
                )
                if not matching:
                    issues.append(_(
                        'Missing or expired required document: %s',
                        doc_type.name,
                    ))
        elif not docs:
            issues.append(_('No compliance documents on file.'))
        elif not any(d.is_acceptable_for_sales() for d in docs):
            issues.append(_('All compliance documents are expired.'))

        return issues

    def action_view_compliance_documents(self):
        self.ensure_one()
        partner = self._commercial_partner_for_compliance()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Compliance Documents'),
            'res_model': 'customer.compliance.document',
            'view_mode': 'list,form',
            'domain': [('partner_id', '=', partner.id)],
            'context': {
                'default_partner_id': partner.id,
            },
        }
