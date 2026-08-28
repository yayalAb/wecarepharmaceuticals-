# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class WecareSalesPlan(models.Model):
    _name = 'wecare.sales.plan'
    _description = 'Sales Plan'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_start desc, id desc'
    _rec_name = 'plan_no'

    plan_no = fields.Char(
        string='Sales Plan No.',
        copy=False,
        readonly=True,
        default='New',
        tracking=True,
    )
    name = fields.Char(
        string='Sales Plan Name',
        required=True,
        tracking=True,
    )
    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
        tracking=True,
    )
    currency_id = fields.Many2one(
        related='company_id.currency_id',
        store=True,
    )
    fiscal_year = fields.Char(
        string='Fiscal Year',
        compute='_compute_fiscal_year',
        store=True,
    )
    plan_period = fields.Selection(
        [
            ('annual', 'Annual'),
            ('quarterly', 'Quarterly'),
            ('monthly', 'Monthly'),
        ],
        string='Plan Period',
        default='annual',
        required=True,
        tracking=True,
    )
    date_start = fields.Date(
        string='Start Date',
        required=True,
        tracking=True,
    )
    date_end = fields.Date(
        string='End Date',
        required=True,
        tracking=True,
    )
    team_id = fields.Many2one(
        'crm.team',
        string='Sales Team',
        tracking=True,
        check_company=True,
    )
    manager_id = fields.Many2one(
        'res.users',
        string='Sales Manager',
        tracking=True,
    )
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('submitted', 'Submitted'),
            ('approved', 'Approved'),
            ('closed', 'Closed'),
        ],
        default='draft',
        required=True,
        tracking=True,
        copy=False,
    )
    remarks = fields.Text()
    target_line_ids = fields.One2many(
        'wecare.sales.target.line',
        'plan_id',
        string='Sales Targets',
        copy=True,
    )
    target_count = fields.Integer(compute='_compute_totals')
    total_annual_qty = fields.Float(
        string='Total Annual Qty',
        compute='_compute_totals',
        digits='Product Unit of Measure',
    )
    total_annual_revenue = fields.Monetary(
        string='Total Annual Target',
        compute='_compute_totals',
    )
    total_actual_revenue = fields.Monetary(
        string='Actual Revenue',
        compute='_compute_totals',
    )
    achievement_pct = fields.Float(
        string='Achievement %',
        compute='_compute_totals',
    )

    @api.depends('date_start')
    def _compute_fiscal_year(self):
        for plan in self:
            plan.fiscal_year = str(plan.date_start.year) if plan.date_start else False

    @api.depends(
        'target_line_ids.annual_qty',
        'target_line_ids.annual_revenue',
        'target_line_ids.actual_revenue',
    )
    def _compute_totals(self):
        for plan in self:
            lines = plan.target_line_ids
            plan.target_count = len(lines)
            plan.total_annual_qty = sum(lines.mapped('annual_qty'))
            plan.total_annual_revenue = sum(lines.mapped('annual_revenue'))
            plan.total_actual_revenue = sum(lines.mapped('actual_revenue'))
            plan.achievement_pct = (
                (plan.total_actual_revenue / plan.total_annual_revenue) * 100.0
                if plan.total_annual_revenue
                else 0.0
            )

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for plan in self:
            if plan.date_start and plan.date_end and plan.date_end < plan.date_start:
                raise ValidationError(self.env._(
                    'End Date must be on or after Start Date.'
                ))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('plan_no') or vals.get('plan_no') == 'New':
                vals['plan_no'] = self.env['ir.sequence'].next_by_code(
                    'wecare.sales.plan'
                ) or 'New'
        return super().create(vals_list)

    def action_submit(self):
        for plan in self:
            if not plan.target_line_ids:
                raise UserError(self.env._(
                    'Add at least one sales target line before submitting.'
                ))
            plan.state = 'submitted'
            plan.target_line_ids.filtered(lambda l: l.state == 'draft').write(
                {'state': 'submitted'}
            )

    def action_approve(self):
        self.write({'state': 'approved'})
        self.target_line_ids.write({'state': 'approved'})

    def action_reset_draft(self):
        self.write({'state': 'draft'})
        self.target_line_ids.write({'state': 'draft'})

    def action_close(self):
        self.write({'state': 'closed'})
        self.target_line_ids.write({'state': 'closed'})

    def action_print_plan(self):
        self.ensure_one()
        return self.env.ref(
            'wecare_sales_management.action_report_sales_plan'
        ).report_action(self)

    def action_open_target_vs_actual(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._('Target vs Actual'),
            'res_model': 'wecare.target.actual.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_plan_id': self.id,
                'default_date_from': self.date_start,
                'default_date_to': self.date_end,
                'default_company_id': self.company_id.id,
            },
        }
