# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

CHEQUE_METHODS = ('cheque', 'pdc', 'check_printing', 'check')


class WecareChequeRegister(models.Model):
    _name = 'wecare.cheque.register'
    _description = 'Cheque Register'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'received_date desc, id desc'

    collection_no = fields.Char(
        string='Collection No.',
        copy=False,
        readonly=True,
        default='New',
        tracking=True,
    )
    name = fields.Char(
        string='Cheque No.',
        required=True,
        tracking=True,
        copy=False,
        index=True,
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True,
        tracking=True,
        check_company=True,
    )
    salesperson_id = fields.Many2one(
        'res.users',
        string='Salesperson',
        tracking=True,
        check_company=True,
    )
    invoice_ids = fields.Many2many(
        'account.move',
        'wecare_cheque_invoice_rel',
        'cheque_id',
        'invoice_id',
        string='Invoices',
        domain="[('move_type', 'in', ('out_invoice', 'in_invoice')), ('partner_id', '=', partner_id)]",
    )
    payment_id = fields.Many2one(
        'account.payment',
        string='Payment',
        copy=False,
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
    amount = fields.Monetary(
        required=True,
        tracking=True,
    )
    cheque_date = fields.Date(
        string='Cheque Date',
        required=True,
        tracking=True,
    )
    received_date = fields.Date(
        string='Received Date',
        required=True,
        default=fields.Date.context_today,
        tracking=True,
    )
    deposit_date = fields.Date(
        string='Deposit Date',
        tracking=True,
    )
    journal_id = fields.Many2one(
        'account.journal',
        string='Bank',
        domain="[('type', '=', 'bank')]",
        check_company=True,
        tracking=True,
    )
    partner_bank_id = fields.Many2one(
        'res.partner.bank',
        string='Bank Account',
        check_company=True,
    )
    collection_type = fields.Selection(
        [
            ('cheque', 'Cheque'),
            ('cash', 'Cash'),
            ('cpo', 'CPO'),
            ('tele_birr', 'Tele Birr'),
        ],
        default='cheque',
        required=True,
        tracking=True,
    )
    payment_type = fields.Selection(
        [
            ('inbound', 'Customer Collection'),
            ('outbound', 'Vendor Payment'),
        ],
        default='inbound',
        required=True,
        tracking=True,
    )
    state = fields.Selection(
        [
            ('received', 'Received'),
            ('deposited', 'Deposited'),
            ('cleared', 'Cleared'),
            ('bounced', 'Bounced'),
        ],
        default='received',
        required=True,
        tracking=True,
        copy=False,
        index=True,
    )
    bounce_date = fields.Date(tracking=True)
    bounce_reason = fields.Text(tracking=True)
    redeposit_date = fields.Date(string='Re-deposit Date', tracking=True)
    original_cheque_id = fields.Many2one(
        'wecare.cheque.register',
        string='Original Cheque',
        copy=False,
        tracking=True,
        help='Original bounced cheque when this record is a re-deposit.',
    )
    redeposit_ids = fields.One2many(
        'wecare.cheque.register',
        'original_cheque_id',
        string='Re-deposits',
    )
    remarks = fields.Text()
    is_credit_sale = fields.Boolean(
        string='Credit Sale',
        compute='_compute_is_credit_sale',
        store=True,
    )
    outstanding = fields.Boolean(
        string='Open Bounce',
        compute='_compute_outstanding',
        store=True,
    )

    @api.depends('invoice_ids.payment_method')
    def _compute_is_credit_sale(self):
        for cheque in self:
            invoices = cheque.invoice_ids.filtered(
                lambda inv: inv.move_type == 'out_invoice'
            )
            if not invoices:
                cheque.is_credit_sale = cheque.payment_type == 'inbound'
                continue
            methods = invoices.mapped('payment_method')
            cheque.is_credit_sale = any(m == 'credit' for m in methods) or not any(methods)

    @api.depends('state', 'redeposit_ids.state')
    def _compute_outstanding(self):
        for cheque in self:
            if cheque.state != 'bounced':
                cheque.outstanding = False
            else:
                cheque.outstanding = not any(
                    r.state in ('deposited', 'cleared') for r in cheque.redeposit_ids
                )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('collection_no') or vals.get('collection_no') == 'New':
                vals['collection_no'] = self.env['ir.sequence'].next_by_code(
                    'wecare.cheque.register'
                ) or 'New'
        return super().create(vals_list)

    @api.constrains('name', 'company_id', 'original_cheque_id')
    def _check_duplicate_cheque_no(self):
        for cheque in self:
            if not cheque.name:
                continue
            domain = [
                ('name', '=', cheque.name),
                ('company_id', '=', cheque.company_id.id),
                ('id', '!=', cheque.id),
                ('original_cheque_id', '=', False),
            ]
            if cheque.original_cheque_id:
                domain.append(('id', '!=', cheque.original_cheque_id.id))
            if self.search_count(domain):
                raise ValidationError(self.env._(
                    'Cheque number "%s" already exists. Duplicate cheque numbers are not allowed.',
                    cheque.name,
                ))

    @api.constrains('amount', 'cheque_date')
    def _check_amount_date(self):
        for cheque in self:
            if cheque.amount <= 0:
                raise ValidationError(self.env._('Cheque amount must be greater than zero.'))
            if not cheque.cheque_date:
                raise ValidationError(self.env._('Every cheque must contain a cheque date.'))

    def action_deposit(self):
        for cheque in self:
            if cheque.state != 'received':
                raise UserError(self.env._('Only received cheques can be deposited.'))
            cheque.write({
                'state': 'deposited',
                'deposit_date': cheque.deposit_date or fields.Date.context_today(cheque),
            })

    def action_clear(self):
        for cheque in self:
            if cheque.state != 'deposited':
                raise UserError(self.env._('Only deposited cheques can be cleared.'))
            cheque.state = 'cleared'

    def action_bounce(self):
        for cheque in self:
            if cheque.state not in ('received', 'deposited'):
                raise UserError(self.env._(
                    'Only received or deposited cheques can be marked as bounced.'
                ))
            cheque.write({
                'state': 'bounced',
                'bounce_date': cheque.bounce_date or fields.Date.context_today(cheque),
            })

    def action_redeposit(self):
        """Create a new cheque linked to the bounced original. Never delete the bounce."""
        self.ensure_one()
        if self.state != 'bounced':
            raise UserError(self.env._('Only bounced cheques can be re-deposited.'))
        new_cheque = self.copy({
            'name': self.name,
            'state': 'deposited',
            'deposit_date': fields.Date.context_today(self),
            'redeposit_date': fields.Date.context_today(self),
            'original_cheque_id': self.id,
            'bounce_date': False,
            'bounce_reason': False,
            'payment_id': False,
            'collection_no': 'New',
            'remarks': self.env._('Re-deposit of bounced cheque %s', self.name),
        })
        self.redeposit_date = fields.Date.context_today(self)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'wecare.cheque.register',
            'res_id': new_cheque.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def unlink(self):
        bounced = self.filtered(lambda c: c.state == 'bounced')
        if bounced:
            raise UserError(self.env._(
                'A bounced cheque should not be deleted; keep it with status Bounced.'
            ))
        return super().unlink()

    def classify_for_period(self, date_from, date_to):
        """Return current / previous / bounce for the selected reporting period.

        Current: cheque date (or received date) and deposit date are both in the period.
        Previous: cheque originated earlier, but was deposited in this period.
        Bounce: bounced during the period (or bounced and still open).
        """
        self.ensure_one()
        if self.state == 'bounced':
            bounce_day = self.bounce_date or self.deposit_date or self.received_date
            if bounce_day and date_from <= bounce_day <= date_to:
                return 'bounce'
            if self.outstanding and self.bounce_date and self.bounce_date <= date_to:
                return 'bounce'
        origin = self.cheque_date or self.received_date
        deposit = self.deposit_date
        if deposit and date_from <= deposit <= date_to:
            if origin and origin < date_from:
                return 'previous'
            return 'current'
        if not deposit and self.received_date and date_from <= self.received_date <= date_to:
            if origin and origin < date_from:
                return 'previous'
            return 'current'
        return False

    def action_open_payment(self):
        self.ensure_one()
        if not self.payment_id:
            return False
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'res_id': self.payment_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _records_for_print(self):
        if self:
            return self
        domain = list(self.env.context.get('active_domain') or [])
        return self.search(domain)

    def _report_period(self):
        dates = [
            d for d in (
                self.mapped('received_date')
                + self.mapped('deposit_date')
                + self.mapped('cheque_date')
                + self.mapped('bounce_date')
            ) if d
        ]
        today = fields.Date.context_today(self)
        return (min(dates) if dates else today, max(dates) if dates else today)

    def _group_by_salesperson_report(self):
        from collections import defaultdict
        buckets = defaultdict(lambda: self.env['wecare.cheque.register'])
        for rec in self:
            buckets[rec.salesperson_id] |= rec
        groups = []
        for user, recs in buckets.items():
            groups.append({
                'salesperson_name': user.name if user else self.env._('Undefined'),
                'lines': recs,
                'subtotal': sum(recs.mapped('amount')),
            })
        groups.sort(key=lambda g: g['salesperson_name'])
        return groups

    def _report_company(self):
        return self[:1].company_id or self.env.company

    def _get_collection_report_data(self):
        date_from, date_to = self._report_period()
        groups = self._group_by_salesperson_report()
        company = self._report_company()
        return {
            'groups': groups,
            'grand_total': sum(g['subtotal'] for g in groups),
            'company': company,
            'date_from': date_from,
            'date_to': date_to,
            'reporting_date': fields.Date.context_today(self),
        }

    def _get_bank_deposit_report_data(self):
        date_from, date_to = self._report_period()
        company = self._report_company()
        rows = []
        for cheque in self:
            klass = cheque.classify_for_period(date_from, date_to)
            if not klass:
                continue
            rows.append({
                'cheque': cheque,
                'current': cheque.amount if klass == 'current' else 0.0,
                'previous': cheque.amount if klass == 'previous' else 0.0,
                'bounce': cheque.amount if klass == 'bounce' else 0.0,
            })
        from collections import defaultdict
        buckets = defaultdict(list)
        for row in rows:
            buckets[row['cheque'].salesperson_id].append(row)
        groups = []
        for user, recs in buckets.items():
            groups.append({
                'salesperson_name': user.name if user else self.env._('Undefined'),
                'lines': recs,
                'subtotal_current': sum(r['current'] for r in recs),
                'subtotal_previous': sum(r['previous'] for r in recs),
                'subtotal_bounce': sum(r['bounce'] for r in recs),
            })
        groups.sort(key=lambda g: g['salesperson_name'])
        existing_bounce = self.filtered(lambda c: c.state == 'bounced' and c.outstanding)
        return {
            'groups': groups,
            'total_current': sum(g['subtotal_current'] for g in groups),
            'total_previous': sum(g['subtotal_previous'] for g in groups),
            'total_bounce': sum(g['subtotal_bounce'] for g in groups),
            'existing_bounce': sum(existing_bounce.mapped('amount')),
            'company': company,
            'date_from': date_from,
            'date_to': date_to,
            'reporting_date': fields.Date.context_today(self),
        }

    def _get_classified_report_data(self, klass):
        date_from, date_to = self._report_period()
        cheques = self.filtered(
            lambda c: c.classify_for_period(date_from, date_to) == klass
        )
        groups = cheques._group_by_salesperson_report()
        titles = {
            'current': self.env._('Current Cheque Report'),
            'previous': self.env._('Previous Cheque Report'),
            'bounce': self.env._('Bounced Cheque Report'),
        }
        return {
            'title': titles.get(klass, self.env._('Cheque Report')),
            'groups': groups,
            'grand_total': sum(g['subtotal'] for g in groups),
            'company': self._report_company(),
            'date_from': date_from,
            'date_to': date_to,
            'reporting_date': fields.Date.context_today(self),
        }

    def _get_collection_performance_report_data(self):
        date_from, date_to = self._report_period()
        from collections import defaultdict
        buckets = defaultdict(lambda: {
            'received_amt': 0.0, 'received_count': 0,
            'deposited_amt': 0.0, 'bounce_amt': 0.0,
        })
        for cheque in self:
            key = cheque.salesperson_id
            buckets[key]['received_amt'] += cheque.amount
            buckets[key]['received_count'] += 1
            if cheque.deposit_date:
                buckets[key]['deposited_amt'] += cheque.amount
            if cheque.state == 'bounced':
                buckets[key]['bounce_amt'] += cheque.amount
        lines = []
        for salesperson, vals in buckets.items():
            lines.append({
                'salesperson_name': salesperson.name if salesperson else self.env._('Undefined'),
                **vals,
                'net': vals['deposited_amt'] - vals['bounce_amt'],
            })
        lines.sort(key=lambda l: l['salesperson_name'])
        return {
            'lines': lines,
            'total_received': sum(l['received_amt'] for l in lines),
            'total_deposited': sum(l['deposited_amt'] for l in lines),
            'total_bounce': sum(l['bounce_amt'] for l in lines),
            'company': self._report_company(),
            'date_from': date_from,
            'date_to': date_to,
            'reporting_date': fields.Date.context_today(self),
        }

    def _get_bank_summary_report_data(self):
        data = self._get_bank_deposit_report_data()
        from collections import defaultdict
        banks = defaultdict(lambda: {'current': 0.0, 'previous': 0.0, 'bounce': 0.0})
        for group in data['groups']:
            for row in group['lines']:
                bank = row['cheque'].journal_id
                banks[bank]['current'] += row['current']
                banks[bank]['previous'] += row['previous']
                banks[bank]['bounce'] += row['bounce']
        lines = []
        for bank, vals in banks.items():
            lines.append({
                'bank_name': bank.display_name if bank else self.env._('Undefined'),
                **vals,
                'total': vals['current'] + vals['previous'] + vals['bounce'],
            })
        lines.sort(key=lambda l: l['bank_name'])
        return {
            'lines': lines,
            'total_current': sum(l['current'] for l in lines),
            'total_previous': sum(l['previous'] for l in lines),
            'total_bounce': sum(l['bounce'] for l in lines),
            'existing_bounce': data['existing_bounce'],
            'company': data['company'],
            'date_from': data['date_from'],
            'date_to': data['date_to'],
            'reporting_date': data['reporting_date'],
        }

    def action_print_weekly_collection(self):
        return self.env.ref(
            'wecare_sales_management.action_report_weekly_collection'
        ).report_action(self._records_for_print())

    def action_print_weekly_bank_deposit(self):
        return self.env.ref(
            'wecare_sales_management.action_report_weekly_bank_deposit'
        ).report_action(self._records_for_print())

    def action_print_current_cheques(self):
        return self.env.ref(
            'wecare_sales_management.action_report_cheque_classified'
        ).with_context(cheque_classification='current').report_action(
            self._records_for_print()
        )

    def action_print_previous_cheques(self):
        return self.env.ref(
            'wecare_sales_management.action_report_cheque_classified'
        ).with_context(cheque_classification='previous').report_action(
            self._records_for_print()
        )

    def action_print_bounced_cheques(self):
        return self.env.ref(
            'wecare_sales_management.action_report_cheque_classified'
        ).with_context(cheque_classification='bounce').report_action(
            self._records_for_print()
        )

    def action_print_collection_performance(self):
        return self.env.ref(
            'wecare_sales_management.action_report_collection_performance'
        ).report_action(self._records_for_print())

    def action_print_bank_summary(self):
        return self.env.ref(
            'wecare_sales_management.action_report_bank_deposit_summary'
        ).report_action(self._records_for_print())

