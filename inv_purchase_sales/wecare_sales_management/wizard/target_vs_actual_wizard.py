# -*- coding: utf-8 -*-
from odoo import api, fields, models


class WecareTargetActualWizard(models.TransientModel):
    _name = 'wecare.target.actual.wizard'
    _description = 'Target vs Actual Sales'

    plan_id = fields.Many2one('wecare.sales.plan', string='Sales Plan')
    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
    )
    date_from = fields.Date(required=True)
    date_to = fields.Date(required=True)
    salesperson_id = fields.Many2one('res.users')
    product_id = fields.Many2one('product.product')
    line_ids = fields.One2many(
        'wecare.target.actual.line',
        'wizard_id',
        string='Lines',
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        today = fields.Date.context_today(self)
        if 'date_from' in fields_list and not res.get('date_from'):
            res['date_from'] = today.replace(month=1, day=1)
        if 'date_to' in fields_list and not res.get('date_to'):
            res['date_to'] = today
        return res

    @api.onchange('plan_id')
    def _onchange_plan_id(self):
        if self.plan_id:
            self.date_from = self.plan_id.date_start
            self.date_to = self.plan_id.date_end
            self.company_id = self.plan_id.company_id

    def action_compute(self):
        self.ensure_one()
        self.line_ids.unlink()
        domain = [('company_id', '=', self.company_id.id)]
        if self.plan_id:
            domain.append(('plan_id', '=', self.plan_id.id))
        else:
            domain += [
                ('plan_id.date_start', '<=', self.date_to),
                ('plan_id.date_end', '>=', self.date_from),
                ('plan_id.state', '=', 'approved'),
            ]
        if self.salesperson_id:
            domain.append(('salesperson_id', '=', self.salesperson_id.id))
        if self.product_id:
            domain.append(('product_id', '=', self.product_id.id))
        targets = self.env['wecare.sales.target.line'].search(domain)
        lines = []
        for target in targets:
            lines.append((0, 0, {
                'salesperson_id': target.salesperson_id.id,
                'partner_id': target.partner_id.id,
                'product_id': target.product_id.id,
                'target_qty': target.annual_qty,
                'actual_qty': target.actual_qty,
                'target_revenue': target.annual_revenue,
                'actual_revenue': target.actual_revenue,
                'achievement_pct': target.achievement_pct,
            }))
        self.line_ids = lines
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_print(self):
        if not self.line_ids:
            self.action_compute()
        return self.env.ref(
            'wecare_sales_management.action_report_target_vs_actual'
        ).report_action(self)


class WecareTargetActualLine(models.TransientModel):
    _name = 'wecare.target.actual.line'
    _description = 'Target vs Actual Line'

    wizard_id = fields.Many2one(
        'wecare.target.actual.wizard',
        ondelete='cascade',
    )
    salesperson_id = fields.Many2one('res.users', string='Salesperson')
    partner_id = fields.Many2one('res.partner', string='Customer')
    product_id = fields.Many2one('product.product')
    target_qty = fields.Float(string='Target Qty', digits='Product Unit of Measure')
    actual_qty = fields.Float(string='Actual Qty', digits='Product Unit of Measure')
    currency_id = fields.Many2one(related='wizard_id.company_id.currency_id')
    target_revenue = fields.Monetary()
    actual_revenue = fields.Monetary()
    achievement_pct = fields.Float(string='Achievement %')
