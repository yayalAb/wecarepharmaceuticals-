# -*- coding: utf-8 -*-
from odoo import _, fields, models
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    compliance_status = fields.Selection(
        related='partner_id.commercial_partner_id.compliance_status',
        string='Customer Compliance',
        readonly=True,
    )

    def _check_customer_compliance(self):
        """Block Sales Order confirmation when customer compliance is invalid."""
        for order in self:
            partner = order.partner_id.commercial_partner_id
            if not order.company_id.compliance_block_sale_orders:
                continue
            # Skip purely individual contacts that are not commercial customers
            # if company setting requires documents only for companies.
            if (
                order.company_id.compliance_require_company_only
                and not partner.is_company
            ):
                continue
            issues = partner._get_compliance_issues()
            if issues:
                raise UserError(_(
                    'Cannot confirm Sales Order %(order)s for customer %(customer)s.\n\n'
                    '%(issues)s\n\n'
                    'Please update Customer → Compliance Documents before proceeding.',
                    order=order.name or _('New'),
                    customer=partner.display_name,
                    issues='\n'.join(f'- {msg}' for msg in issues),
                ))

    def action_confirm(self):
        self._check_customer_compliance()
        return super().action_confirm()

    def action_open_customer_compliance_documents(self):
        self.ensure_one()
        partner = self.partner_id.commercial_partner_id
        return partner.action_view_compliance_documents()
