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
            ('ok', 'Valid'),
            ('warning', 'Expiring Soon'),
            ('blocked', 'Expired'),
            ('none', 'Missing'),
        ],
        string='Compliance Status',
        compute='_compute_compliance_status',
        store=True,
    )
    # Compatibility stubs for stale partner-form views left in the database.
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
        'compliance_document_ids.expiry_date',
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
        self.ensure_one()
        return self.commercial_partner_id or self

    def _get_compliance_issues(self, for_blocking=True):
        """Return human-readable compliance blockers (matches Wecare warning style)."""
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
                type_docs = docs.filtered(lambda d, t=doc_type: d.document_type_id == t)
                acceptable = type_docs.filtered(lambda d: d.is_acceptable_for_sales())
                if acceptable:
                    continue
                expired = type_docs.filtered(lambda d: d.status == 'expired').sorted(
                    'expiry_date', reverse=True
                )
                if expired:
                    expiry = fields.Date.to_string(expired[0].expiry_date)
                    # Format like 31-Dec-2025
                    try:
                        expiry = expired[0].expiry_date.strftime('%d-%b-%Y')
                    except Exception:
                        pass
                    issues.append(_(
                        'Customer compliance document has expired. '
                        '%(doc_type)s expired on %(expiry)s.',
                        doc_type=doc_type.name,
                        expiry=expiry,
                    ))
                else:
                    issues.append(_(
                        'Customer compliance document is missing: %(doc_type)s.',
                        doc_type=doc_type.name,
                    ))
        elif not docs:
            issues.append(_('Customer compliance documents are missing.'))
        elif not any(d.is_acceptable_for_sales() for d in docs):
            expired = docs.filtered(lambda d: d.status == 'expired').sorted(
                'expiry_date', reverse=True
            )
            if expired:
                try:
                    expiry = expired[0].expiry_date.strftime('%d-%b-%Y')
                except Exception:
                    expiry = fields.Date.to_string(expired[0].expiry_date)
                issues.append(_(
                    'Customer compliance document has expired. '
                    '%(doc_type)s expired on %(expiry)s.',
                    doc_type=expired[0].document_type_id.name or _('Document'),
                    expiry=expiry,
                ))
            else:
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
