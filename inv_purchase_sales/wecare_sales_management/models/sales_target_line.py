# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError

from .res_partner import CUSTOMER_TYPES

MONTH_FIELDS = [
    'qty_jan', 'qty_feb', 'qty_mar', 'qty_apr', 'qty_may', 'qty_jun',
    'qty_jul', 'qty_aug', 'qty_sep', 'qty_oct', 'qty_nov', 'qty_dec',
]


class WecareSalesTargetLine(models.Model):
    _name = 'wecare.sales.target.line'
    _description = 'Sales Target Line'
    _order = 'salesperson_id, partner_id, product_id'

    plan_id = fields.Many2one(
        'wecare.sales.plan',
        required=True,
        ondelete='cascade',
        index=True,
    )
    company_id = fields.Many2one(
        related='plan_id.company_id',
        store=True,
        index=True,
    )
    currency_id = fields.Many2one(related='plan_id.currency_id')
    salesperson_id = fields.Many2one(
        'res.users',
        string='Salesperson',
        required=True,
        check_company=True,
    )
    territory_id = fields.Many2one(
        'wecare.sales.territory',
        string='Territory',
        check_company=True,
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        domain="[('parent_id', '=', False)]",
        check_company=True,
    )
    customer_type = fields.Selection(
        CUSTOMER_TYPES,
        string='Customer Type',
    )
    categ_id = fields.Many2one(
        'product.category',
        string='Product Category',
    )
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        check_company=True,
    )
    product_uom_id = fields.Many2one(
        'uom.uom',
        string='UoM',
    )
    annual_qty = fields.Float(
        string='Annual Quantity',
        digits='Product Unit of Measure',
    )
    unit_price = fields.Monetary(string='Unit Price')
    annual_revenue = fields.Monetary(
        string='Annual Revenue',
        compute='_compute_annual_revenue',
        store=True,
    )
    monthly_target = fields.Monetary(
        string='Monthly Target',
        compute='_compute_annual_revenue',
        store=True,
    )
    qty_jan = fields.Float(string='Jan', digits='Product Unit of Measure')
    qty_feb = fields.Float(string='Feb', digits='Product Unit of Measure')
    qty_mar = fields.Float(string='Mar', digits='Product Unit of Measure')
    qty_apr = fields.Float(string='Apr', digits='Product Unit of Measure')
    qty_may = fields.Float(string='May', digits='Product Unit of Measure')
    qty_jun = fields.Float(string='Jun', digits='Product Unit of Measure')
    qty_jul = fields.Float(string='Jul', digits='Product Unit of Measure')
    qty_aug = fields.Float(string='Aug', digits='Product Unit of Measure')
    qty_sep = fields.Float(string='Sep', digits='Product Unit of Measure')
    qty_oct = fields.Float(string='Oct', digits='Product Unit of Measure')
    qty_nov = fields.Float(string='Nov', digits='Product Unit of Measure')
    qty_dec = fields.Float(string='Dec', digits='Product Unit of Measure')
    monthly_qty_total = fields.Float(
        string='Monthly Qty Total',
        compute='_compute_monthly_qty_total',
        digits='Product Unit of Measure',
    )
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('submitted', 'Submitted'),
            ('approved', 'Approved'),
            ('closed', 'Closed'),
        ],
        default='draft',
    )
    actual_qty = fields.Float(
        string='Actual Qty',
        compute='_compute_actuals',
        digits='Product Unit of Measure',
    )
    actual_revenue = fields.Monetary(
        string='Actual Revenue',
        compute='_compute_actuals',
    )
    achievement_pct = fields.Float(
        string='Achievement %',
        compute='_compute_actuals',
    )

    @api.depends('annual_qty', 'unit_price')
    def _compute_annual_revenue(self):
        for line in self:
            line.annual_revenue = line.annual_qty * line.unit_price
            line.monthly_target = line.annual_revenue / 12.0 if line.annual_revenue else 0.0

    @api.depends(*MONTH_FIELDS)
    def _compute_monthly_qty_total(self):
        for line in self:
            line.monthly_qty_total = sum(line[field] for field in MONTH_FIELDS)

    @api.depends(
        'salesperson_id', 'partner_id', 'product_id',
        'plan_id.date_start', 'plan_id.date_end', 'plan_id.company_id',
        'annual_revenue',
    )
    def _compute_actuals(self):
        MoveLine = self.env['account.move.line']
        for line in self:
            if not line.plan_id or not line.salesperson_id:
                line.actual_qty = 0.0
                line.actual_revenue = 0.0
                line.achievement_pct = 0.0
                continue
            domain = [
                ('move_id.move_type', '=', 'out_invoice'),
                ('move_id.state', '=', 'posted'),
                ('move_id.invoice_user_id', '=', line.salesperson_id.id),
                ('move_id.company_id', '=', line.company_id.id),
                ('move_id.invoice_date', '>=', line.plan_id.date_start),
                ('move_id.invoice_date', '<=', line.plan_id.date_end),
                ('display_type', '=', 'product'),
                ('product_id', '!=', False),
            ]
            if line.partner_id:
                domain.append(('move_id.partner_id', '=', line.partner_id.id))
            if line.product_id:
                domain.append(('product_id', '=', line.product_id.id))
            elif line.categ_id:
                domain.append(('product_id.categ_id', 'child_of', line.categ_id.id))
            grouped = MoveLine.read_group(
                domain,
                ['quantity:sum', 'price_subtotal:sum'],
                [],
            )
            qty = grouped and grouped[0].get('quantity') or 0.0
            revenue = grouped and grouped[0].get('price_subtotal') or 0.0
            line.actual_qty = qty
            line.actual_revenue = revenue
            line.achievement_pct = (
                (revenue / line.annual_revenue) * 100.0 if line.annual_revenue else 0.0
            )

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            self.customer_type = self.partner_id.wecare_customer_type
            self.territory_id = self.partner_id.wecare_territory_id
            if self.partner_id.user_id:
                self.salesperson_id = self.partner_id.user_id

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.product_uom_id = self.product_id.uom_id
            self.categ_id = self.product_id.categ_id
            self.unit_price = self.product_id.lst_price

    @api.onchange('annual_qty')
    def _onchange_annual_qty_distribute(self):
        if self.annual_qty and not any(self[field] for field in MONTH_FIELDS):
            self._distribute_evenly()

    def action_print_target_vs_actual(self):
        records = self if self else self.search(list(self.env.context.get('active_domain') or []))
        return self.env.ref(
            'wecare_sales_management.action_report_target_vs_actual'
        ).report_action(records)

    def action_distribute_evenly(self):
        for line in self:
            line._distribute_evenly()

    def _distribute_evenly(self):
        self.ensure_one()
        base = self.annual_qty / 12.0 if self.annual_qty else 0.0
        for field in MONTH_FIELDS:
            self[field] = base

    @api.constrains('salesperson_id')
    def _check_salesperson(self):
        for line in self:
            if not line.salesperson_id:
                raise ValidationError(self.env._(
                    'Every sales target must have an assigned salesperson.'
                ))

    @api.depends('salesperson_id', 'partner_id', 'product_id')
    def _compute_display_name(self):
        for line in self:
            parts = [
                line.salesperson_id.name or '',
                line.partner_id.display_name or '',
                line.product_id.display_name or '',
            ]
            line.display_name = ' / '.join(p for p in parts if p) or (line.plan_id.plan_no or str(line.id))
