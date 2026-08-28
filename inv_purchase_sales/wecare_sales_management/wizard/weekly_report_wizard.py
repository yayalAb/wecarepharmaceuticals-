# -*- coding: utf-8 -*-
from collections import defaultdict

from odoo import fields, models
from odoo.exceptions import UserError


class WecareWeeklyReportWizard(models.TransientModel):
    _name = 'wecare.weekly.report.wizard'
    _description = 'Weekly Collection / Bank Deposit Report'

    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
    )
    date_from = fields.Date(
        string='From Date',
        required=True,
        default=lambda self: fields.Date.start_of(fields.Date.context_today(self), 'week'),
    )
    date_to = fields.Date(
        string='To Date',
        required=True,
        default=lambda self: fields.Date.end_of(fields.Date.context_today(self), 'week'),
    )
    reporting_date = fields.Date(
        string='Reporting Date',
        required=True,
        default=fields.Date.context_today,
    )
    salesperson_id = fields.Many2one('res.users', string='Salesperson')
    partner_id = fields.Many2one('res.partner', string='Customer')
    journal_id = fields.Many2one(
        'account.journal',
        string='Bank',
        domain="[('type', '=', 'bank')]",
    )
    cheque_state = fields.Selection(
        [
            ('received', 'Received'),
            ('deposited', 'Deposited'),
            ('cleared', 'Cleared'),
            ('bounced', 'Bounced'),
        ],
        string='Cheque Status',
    )
    classification = fields.Selection(
        [
            ('current', 'Current'),
            ('previous', 'Previous'),
            ('bounce', 'Bounce'),
        ],
        string='Classification',
    )
    credit_only = fields.Boolean(
        string='Credit Sales Only',
        default=True,
    )

    def _cheque_domain(self, date_field):
        self.ensure_one()
        domain = [
            ('company_id', '=', self.company_id.id),
            ('payment_type', '=', 'inbound'),
            (date_field, '>=', self.date_from),
            (date_field, '<=', self.date_to),
        ]
        if self.salesperson_id:
            domain.append(('salesperson_id', '=', self.salesperson_id.id))
        if self.partner_id:
            domain.append(('partner_id', '=', self.partner_id.id))
        if self.journal_id:
            domain.append(('journal_id', '=', self.journal_id.id))
        if self.cheque_state:
            domain.append(('state', '=', self.cheque_state))
        if self.credit_only:
            domain.append(('is_credit_sale', '=', True))
        return domain

    def _get_cheques(self, date_field='received_date'):
        return self.env['wecare.cheque.register'].search(
            self._cheque_domain(date_field),
            order='salesperson_id, received_date, name',
        )

    def _group_by_salesperson(self, cheques, amount_fn=None):
        groups = []
        buckets = defaultdict(list)
        for cheque in cheques:
            buckets[cheque.salesperson_id].append(cheque)
        for salesperson, recs in buckets.items():
            subtotal = sum((amount_fn(c) if amount_fn else c.amount) for c in recs)
            groups.append({
                'salesperson': salesperson,
                'salesperson_name': salesperson.name if salesperson else self.env._('Undefined'),
                'lines': recs,
                'subtotal': subtotal,
            })
        groups.sort(key=lambda g: g['salesperson_name'])
        return groups

    def get_collection_data(self):
        self.ensure_one()
        cheques = self._get_cheques('received_date')
        groups = self._group_by_salesperson(cheques)
        return {
            'groups': groups,
            'grand_total': sum(g['subtotal'] for g in groups),
            'company': self.company_id,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'reporting_date': self.reporting_date,
        }

    def get_bank_deposit_data(self):
        self.ensure_one()
        deposited = self.env['wecare.cheque.register'].search(
            self._cheque_domain('deposit_date'),
            order='salesperson_id, deposit_date, name',
        )
        bounced = self.env['wecare.cheque.register'].search(
            self._cheque_domain('bounce_date'),
            order='salesperson_id, bounce_date, name',
        )
        seen = set()
        rows = []
        for cheque in deposited | bounced:
            if cheque.id in seen:
                continue
            seen.add(cheque.id)
            klass = cheque.classify_for_period(self.date_from, self.date_to)
            if self.classification and klass != self.classification:
                continue
            if not klass:
                continue
            rows.append({
                'cheque': cheque,
                'classification': klass,
                'current': cheque.amount if klass == 'current' else 0.0,
                'previous': cheque.amount if klass == 'previous' else 0.0,
                'bounce': cheque.amount if klass == 'bounce' else 0.0,
            })
        buckets = defaultdict(list)
        for row in rows:
            buckets[row['cheque'].salesperson_id].append(row)
        groups = []
        for salesperson, recs in buckets.items():
            groups.append({
                'salesperson': salesperson,
                'salesperson_name': salesperson.name if salesperson else self.env._('Undefined'),
                'lines': recs,
                'subtotal_current': sum(r['current'] for r in recs),
                'subtotal_previous': sum(r['previous'] for r in recs),
                'subtotal_bounce': sum(r['bounce'] for r in recs),
            })
        groups.sort(key=lambda g: g['salesperson_name'])
        existing_bounce = self.env['wecare.cheque.register'].search([
            ('company_id', '=', self.company_id.id),
            ('payment_type', '=', 'inbound'),
            ('state', '=', 'bounced'),
            ('outstanding', '=', True),
        ])
        if self.salesperson_id:
            existing_bounce = existing_bounce.filtered(
                lambda c: c.salesperson_id == self.salesperson_id
            )
        return {
            'groups': groups,
            'total_current': sum(g['subtotal_current'] for g in groups),
            'total_previous': sum(g['subtotal_previous'] for g in groups),
            'total_bounce': sum(g['subtotal_bounce'] for g in groups),
            'existing_bounce': sum(existing_bounce.mapped('amount')),
            'company': self.company_id,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'reporting_date': self.reporting_date,
        }

    def action_print_collection(self):
        self._check_dates()
        return self.env.ref(
            'wecare_sales_management.action_report_weekly_collection'
        ).report_action(self)

    def action_print_bank_deposit(self):
        self._check_dates()
        return self.env.ref(
            'wecare_sales_management.action_report_weekly_bank_deposit'
        ).report_action(self)

    def action_view_cheques(self):
        self._check_dates()
        cheques = self._get_cheques('received_date') | self._get_cheques('deposit_date')
        if self.classification:
            cheques = cheques.filtered(
                lambda c: c.classify_for_period(self.date_from, self.date_to) == self.classification
            )
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._('Cheques'),
            'res_model': 'wecare.cheque.register',
            'view_mode': 'list,form',
            'domain': [('id', 'in', cheques.ids)],
        }

    def _check_dates(self):
        self.ensure_one()
        if self.date_to < self.date_from:
            raise UserError(self.env._('To Date must be on or after From Date.'))
