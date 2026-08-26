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
        """Block Sales Order when mandatory customer documents are missing/expired."""
        for order in self:
            partner = order.partner_id.commercial_partner_id
            if not order.company_id.compliance_block_sale_orders:
                continue
            if (
                order.company_id.compliance_require_company_only
                and not partner.is_company
            ):
                continue
            issues = partner._get_compliance_issues()
            if issues:
                raise UserError(_(
                    '%(issues)s\n'
                    'Please update the customer document before confirming this Sales Order.',
                    issues='\n'.join(issues),
                ))

    def action_confirm(self):
        self._check_customer_compliance()
        return super().action_confirm()

    def action_open_customer_compliance_documents(self):
        self.ensure_one()
        partner = self.partner_id.commercial_partner_id
        return partner.action_view_compliance_documents()
