# -*- coding: utf-8 -*-
from odoo import api, fields, models


class WecareKpiWizard(models.TransientModel):
    _name = 'wecare.kpi.wizard'
    _description = 'WeCare Management KPIs'

    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(related='company_id.currency_id')
    date_from = fields.Date(required=True)
    date_to = fields.Date(required=True)
    sales_target = fields.Monetary(readonly=True)
    actual_sales = fields.Monetary(readonly=True)
    achievement_pct = fields.Float(string='Achievement %', readonly=True)
    customer_collection = fields.Monetary(readonly=True)
    current_deposited = fields.Monetary(readonly=True)
    previous_deposited = fields.Monetary(readonly=True)
    bounce_amount = fields.Monetary(readonly=True)
    outstanding_collection = fields.Monetary(readonly=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        today = fields.Date.context_today(self)
        res.setdefault('date_from', fields.Date.start_of(today, 'week'))
        res.setdefault('date_to', fields.Date.end_of(today, 'week'))
        return res

    @api.onchange('company_id', 'date_from', 'date_to')
    def _onchange_compute(self):
        if self.date_from and self.date_to:
            self._compute_kpis()

    def action_compute(self):
        self._compute_kpis()
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def _compute_kpis(self):
        for wiz in self:
            if not wiz.date_from or not wiz.date_to:
                continue
            plans = self.env['wecare.sales.plan'].search([
                ('company_id', '=', wiz.company_id.id),
                ('state', '=', 'approved'),
                ('date_start', '<=', wiz.date_to),
                ('date_end', '>=', wiz.date_from),
            ])
            wiz.sales_target = sum(plans.mapped('total_annual_revenue'))
            invoices = self.env['account.move'].search([
                ('company_id', '=', wiz.company_id.id),
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
                ('invoice_date', '>=', wiz.date_from),
                ('invoice_date', '<=', wiz.date_to),
            ])
            wiz.actual_sales = sum(invoices.mapped('amount_untaxed_signed'))
            wiz.achievement_pct = (
                (wiz.actual_sales / wiz.sales_target) * 100.0 if wiz.sales_target else 0.0
            )
            collections = self.env['wecare.cheque.register'].search([
                ('company_id', '=', wiz.company_id.id),
                ('payment_type', '=', 'inbound'),
                ('received_date', '>=', wiz.date_from),
                ('received_date', '<=', wiz.date_to),
            ])
            wiz.customer_collection = sum(collections.mapped('amount'))
            deposited = self.env['wecare.cheque.register'].search([
                ('company_id', '=', wiz.company_id.id),
                ('payment_type', '=', 'inbound'),
                ('deposit_date', '>=', wiz.date_from),
                ('deposit_date', '<=', wiz.date_to),
            ])
            current = previous = 0.0
            for cheque in deposited:
                klass = cheque.classify_for_period(wiz.date_from, wiz.date_to)
                if klass == 'current':
                    current += cheque.amount
                elif klass == 'previous':
                    previous += cheque.amount
            wiz.current_deposited = current
            wiz.previous_deposited = previous
            bounced = self.env['wecare.cheque.register'].search([
                ('company_id', '=', wiz.company_id.id),
                ('payment_type', '=', 'inbound'),
                ('state', '=', 'bounced'),
                ('bounce_date', '>=', wiz.date_from),
                ('bounce_date', '<=', wiz.date_to),
            ])
            wiz.bounce_amount = sum(bounced.mapped('amount'))
            outstanding = self.env['account.move'].search([
                ('company_id', '=', wiz.company_id.id),
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
                ('payment_state', 'in', ('not_paid', 'partial')),
            ])
            wiz.outstanding_collection = sum(outstanding.mapped('amount_residual'))
