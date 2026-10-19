# -*- coding: utf-8 -*-
from collections import defaultdict
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.tools import float_compare, float_round

CUSTOMER_TYPES = [
    ('pharmacy', 'Pharmacy'),
    ('hospital', 'Hospital'),
    ('distributor', 'Distributor'),
    ('clinic', 'Clinic'),
    ('ngo', 'NGO'),
]


class WecareExecutiveDashboard(models.TransientModel):
    _name = 'wecare.executive.dashboard'
    _description = 'WeCare Executive Management Dashboard'

    # -------------------------------------------------------------------------
    # Helper: Date Calculations
    # -------------------------------------------------------------------------
    @api.model
    def _resolve_date_range(self, range_key, date_from=None, date_to=None):
        today = fields.Date.context_today(self)
        if range_key == 'today':
            return today, today, range_key
        elif range_key in ('wtd', 'this_week'):
            start = today - timedelta(days=today.weekday())
            return start, today, 'wtd'
        elif range_key in ('mtd', 'this_month_mtd'):
            start = today.replace(day=1)
            return start, today, 'mtd'
        elif range_key in ('ytd', 'this_year_ytd'):
            start = today.replace(month=1, day=1)
            return start, today, 'ytd'
        elif range_key == 'yesterday':
            yesterday = today - timedelta(days=1)
            return yesterday, yesterday, range_key
        elif range_key == 'last_week':
            end = today - timedelta(days=today.weekday() + 1)
            start = end - timedelta(days=6)
            return start, end, range_key
        elif range_key == 'last_month':
            first_of_this_month = today.replace(day=1)
            end = first_of_this_month - timedelta(days=1)
            start = end.replace(day=1)
            return start, end, range_key
        elif range_key == 'last_30_days':
            start = today - timedelta(days=30)
            return start, today, range_key
        elif range_key == 'this_quarter_qtd':
            quarter = (today.month - 1) // 3
            start = today.replace(month=quarter * 3 + 1, day=1)
            end = (start + relativedelta(months=3)) - timedelta(days=1)
            return start, end, range_key
        elif range_key == 'custom' and date_from and date_to:
            start = fields.Date.from_string(date_from)
            end = fields.Date.from_string(date_to)
            return start, end, 'custom'
        
        # Default fallback: MTD
        start = today.replace(day=1)
        return start, today, 'mtd'

    # -------------------------------------------------------------------------
    # Public RPC: Aggregated Dashboard Data
    # -------------------------------------------------------------------------
    @api.model
    def get_dashboard_data(
        self,
        date_range='mtd',
        date_from=None,
        date_to=None,
        customer_type=None,
        territory_id=None,
        collection_type=None,
    ):
        company = self.env.company
        today = fields.Date.context_today(self)
        start_date, end_date, active_range = self._resolve_date_range(date_range, date_from, date_to)

        # Base partner domain for filters
        partner_domain = [('company_id', 'in', (company.id, False))]
        if customer_type and customer_type != 'all':
            partner_domain.append(('wecare_customer_type', '=', customer_type))
        if territory_id and str(territory_id) != 'all':
            partner_domain.append(('wecare_territory_id', '=', int(territory_id)))

        filtered_partners = self.env['res.partner'].search(partner_domain)
        filtered_partner_ids = filtered_partners.ids

        # ---------------------------------------------------------------------
        # ROW 1: Executive Financial KPIs
        # ---------------------------------------------------------------------
        # 1. Sales This Month
        month_start = today.replace(day=1)
        month_domain = [
            ('company_id', '=', company.id),
            ('move_type', 'in', ('out_invoice', 'out_refund')),
            ('state', '=', 'posted'),
            ('invoice_date', '>=', month_start),
            ('invoice_date', '<=', today),
        ]
        if customer_type or territory_id:
            month_domain.append(('partner_id', 'in', filtered_partner_ids))

        invoices_this_month = self.env['account.move'].search(month_domain)
        sales_this_month = sum(invoices_this_month.mapped('amount_untaxed_signed'))

        # 2. Sales for the Selected Period
        period_domain = [
            ('company_id', '=', company.id),
            ('move_type', 'in', ('out_invoice', 'out_refund')),
            ('state', '=', 'posted'),
            ('invoice_date', '>=', start_date),
            ('invoice_date', '<=', end_date),
        ]
        if customer_type or territory_id:
            period_domain.append(('partner_id', 'in', filtered_partner_ids))

        invoices_period = self.env['account.move'].search(period_domain)
        sales_selected_period = sum(invoices_period.mapped('amount_untaxed_signed'))
        invoice_count_period = len(invoices_period.filtered(lambda m: m.move_type == 'out_invoice'))

        # 3. Sales Target Achievement (Actual sales vs approved target)
        plan_domain = [
            ('company_id', '=', company.id),
            ('state', '=', 'approved'),
            ('date_start', '<=', end_date),
            ('date_end', '>=', start_date),
        ]
        plans = self.env['wecare.sales.plan'].search(plan_domain)
        
        target_amount = 0.0
        months_in_range = set()
        if plans:
            month_abbrs = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
            cur_iter = start_date.replace(day=1)
            end_month = end_date.replace(day=1)
            while cur_iter <= end_month:
                months_in_range.add(cur_iter.month)
                cur_iter += relativedelta(months=1)

            tl_domain = [('plan_id', 'in', plans.ids)]
            if customer_type and customer_type != 'all':
                tl_domain.append(('partner_id.wecare_customer_type', '=', customer_type))
            if territory_id and str(territory_id) != 'all':
                tl_domain.append(('territory_id', '=', int(territory_id)))

            target_lines = self.env['wecare.sales.target.line'].search(tl_domain)
            for line in target_lines:
                price = line.unit_price or 0.0
                line_target = 0.0
                if len(months_in_range) >= 12 or active_range in ('ytd', 'custom'):
                    if line.annual_revenue:
                        line_target = line.annual_revenue
                    elif line.annual_qty:
                        line_target = line.annual_qty * price
                else:
                    for m in months_in_range:
                        field_name = f'qty_{month_abbrs[m - 1]}'
                        qty_month = getattr(line, field_name, 0.0)
                        line_target += qty_month * price
                target_amount += line_target
        
        target_achievement_pct = (
            (sales_selected_period / target_amount) * 100.0 if target_amount > 0 else 0.0
        )
        target_variance = sales_selected_period - target_amount

        # 4. Total Receivables (Outstanding customer balances)
        open_domain = [
            ('company_id', '=', company.id),
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('payment_state', 'in', ('not_paid', 'partial')),
        ]
        if customer_type or territory_id:
            open_domain.append(('partner_id', 'in', filtered_partner_ids))

        open_customer_invoices = self.env['account.move'].search(open_domain)
        total_receivables = sum(open_customer_invoices.mapped('amount_residual_signed'))
        total_receivables_count = len(open_customer_invoices)

        # 5. Overdue Receivables: "(the outstanding rule is 45 day)"
        cutoff_date_45 = today - timedelta(days=45)
        overdue_invoices = open_customer_invoices.filtered(
            lambda inv: (inv.invoice_date and inv.invoice_date <= cutoff_date_45) or
                        (inv.invoice_date_due and inv.invoice_date_due < today)
        )
        overdue_receivables = sum(overdue_invoices.mapped('amount_residual_signed'))
        overdue_count = len(overdue_invoices)
        overdue_pct = (
            (overdue_receivables / total_receivables) * 100.0 if total_receivables > 0 else 0.0
        )

        # ---------------------------------------------------------------------
        # ROW 2: Cheque Management KPIs
        # ---------------------------------------------------------------------
        cheque_model = self.env['wecare.cheque.register']
        base_cheque_domain = [
            ('company_id', '=', company.id),
            ('payment_type', '=', 'inbound'),
        ]
        if customer_type or territory_id:
            base_cheque_domain.append(('partner_id', 'in', filtered_partner_ids))

        # Cheques Received: Total value received during the selected period
        cheques_received = cheque_model.search(base_cheque_domain + [
            ('received_date', '>=', start_date),
            ('received_date', '<=', end_date),
        ])
        cheques_received_amount = sum(cheques_received.mapped('amount'))
        cheques_received_count = len(cheques_received)

        # Cheques in Clearing: Deposited cheques awaiting bank confirmation (state = 'deposited')
        cheques_in_clearing = cheque_model.search(base_cheque_domain + [
            ('state', '=', 'deposited'),
        ])
        cheques_in_clearing_amount = sum(cheques_in_clearing.mapped('amount'))
        cheques_in_clearing_count = len(cheques_in_clearing)

        # Cleared Cheques: Cheques confirmed by bank (state = 'cleared')
        cheques_cleared = cheque_model.search(base_cheque_domain + [
            ('state', '=', 'cleared'),
            ('deposit_date', '>=', start_date),
            ('deposit_date', '<=', end_date),
        ])
        if not cheques_cleared:
            cheques_cleared = cheque_model.search(base_cheque_domain + [
                ('state', '=', 'cleared'),
            ])
        cheques_cleared_amount = sum(cheques_cleared.mapped('amount'))
        cheques_cleared_count = len(cheques_cleared)

        # Bounced Cheques: Unresolved bounced cheque value (state = 'bounced', open bounce)
        bounced_domain = base_cheque_domain + [('state', '=', 'bounced')]
        if 'outstanding' in cheque_model._fields:
            bounced_cheques = cheque_model.search(bounced_domain + [('outstanding', '=', True)])
        else:
            bounced_cheques = cheque_model.search(bounced_domain)
        
        cheques_bounced_amount = sum(bounced_cheques.mapped('amount'))
        cheques_bounced_count = len(bounced_cheques)

        # ---------------------------------------------------------------------
        # ROW 3: Sales and Collection Analysis
        # ---------------------------------------------------------------------
        collection_breakdown = {
            'cheque': 0.0,
            'cash': 0.0,
            'bank_transfer': 0.0,
            'other': 0.0,
        }
        collection_counts = {
            'cheque': 0,
            'cash': 0,
            'bank_transfer': 0,
            'other': 0,
        }

        # 1. From wecare.cheque.register
        collections_in_period = cheque_model.search(base_cheque_domain + [
            ('received_date', '>=', start_date),
            ('received_date', '<=', end_date),
        ])
        for rec in collections_in_period:
            ctype = rec.collection_type
            amt = rec.amount or 0.0
            if ctype in ('cheque', 'cpo'):
                collection_breakdown['cheque'] += amt
                collection_counts['cheque'] += 1
            elif ctype == 'cash':
                collection_breakdown['cash'] += amt
                collection_counts['cash'] += 1
            elif ctype == 'tele_birr':
                collection_breakdown['other'] += amt
                collection_counts['other'] += 1
            else:
                collection_breakdown['cheque'] += amt
                collection_counts['cheque'] += 1

        # 2. From direct account.payment
        pay_domain = [
            ('company_id', '=', company.id),
            ('payment_type', '=', 'inbound'),
            ('partner_type', '=', 'customer'),
            ('state', '=', 'posted'),
            ('date', '>=', start_date),
            ('date', '<=', end_date),
        ]
        if customer_type or territory_id:
            pay_domain.append(('partner_id', 'in', filtered_partner_ids))

        direct_payments = self.env['account.payment'].search(pay_domain)
        linked_payment_ids = set(collections_in_period.mapped('payment_id').ids)
        for payment in direct_payments:
            if payment.id in linked_payment_ids:
                continue
            amt = payment.amount or 0.0
            jtype = payment.journal_id.type
            if jtype == 'cash':
                collection_breakdown['cash'] += amt
                collection_counts['cash'] += 1
            elif jtype == 'bank':
                pm_code = payment.payment_method_line_id.code if payment.payment_method_line_id else ''
                if 'cheque' in pm_code or 'check' in pm_code:
                    collection_breakdown['cheque'] += amt
                    collection_counts['cheque'] += 1
                else:
                    collection_breakdown['bank_transfer'] += amt
                    collection_counts['bank_transfer'] += 1
            else:
                collection_breakdown['other'] += amt
                collection_counts['other'] += 1

        total_collections = sum(collection_breakdown.values())
        total_collection_items = sum(collection_counts.values())

        # Monthly timeline chart for Sales vs Target
        months_labels = []
        sales_timeline = []
        target_timeline = []
        
        trend_start = (end_date.replace(day=1) - relativedelta(months=5))
        iter_m = trend_start
        while iter_m <= end_date.replace(day=1):
            m_label = iter_m.strftime('%b %Y')
            m_start = iter_m
            m_end = (iter_m + relativedelta(months=1)) - timedelta(days=1)
            
            m_invoices = self.env['account.move'].search([
                ('company_id', '=', company.id),
                ('move_type', 'in', ('out_invoice', 'out_refund')),
                ('state', '=', 'posted'),
                ('invoice_date', '>=', m_start),
                ('invoice_date', '<=', m_end),
            ])
            m_sales = sum(m_invoices.mapped('amount_untaxed_signed'))
            m_target = (target_amount / max(1, len(months_in_range))) if target_amount > 0 else 0.0
            
            months_labels.append(m_label)
            sales_timeline.append(float_round(m_sales, precision_digits=2))
            target_timeline.append(float_round(m_target, precision_digits=2))
            iter_m += relativedelta(months=1)

        # ---------------------------------------------------------------------
        # ROW 4: Management Action Center
        # ---------------------------------------------------------------------
        action_center = [
            {
                'id': 'overdue_invoices',
                'title': _('Overdue Customer Invoices'),
                'subtitle': _('Follow up with customers & collection officers (>45 days)'),
                'count': overdue_count,
                'amount': overdue_receivables,
                'icon': 'fa-exclamation-triangle',
                'severity': 'danger' if overdue_count > 0 else 'success',
                'badge': _('Action Req.') if overdue_count > 0 else _('All Clear'),
                'badge_color': 'red' if overdue_count > 0 else 'green',
                'icon_color': 'red' if overdue_count > 0 else 'green',
                'action_model': 'account.move',
                'action_name': _('Overdue Customer Invoices'),
                'action_domain': [
                    ('move_type', '=', 'out_invoice'),
                    ('state', '=', 'posted'),
                    ('payment_state', 'in', ('not_paid', 'partial')),
                    '|',
                    ('invoice_date', '<=', fields.Date.to_string(cutoff_date_45)),
                    '&',
                    ('invoice_date_due', '!=', False),
                    ('invoice_date_due', '<', fields.Date.to_string(today)),
                ],
            },
            {
                'id': 'cheques_awaiting_deposit',
                'title': _('Cheques Awaiting Deposit'),
                'subtitle': _('Confirm deposit and bank submission'),
                'count': len(cheque_model.search(base_cheque_domain + [('state', '=', 'received')])),
                'amount': sum(cheque_model.search(base_cheque_domain + [('state', '=', 'received')]).mapped('amount')),
                'icon': 'fa-hourglass-half',
                'severity': 'warning',
                'badge': _('Pending Deposit'),
                'badge_color': 'amber',
                'icon_color': 'amber',
                'action_model': 'wecare.cheque.register',
                'action_name': _('Cheques Awaiting Deposit'),
                'action_domain': base_cheque_domain + [('state', '=', 'received')],
            },
            {
                'id': 'cheques_awaiting_clearance',
                'title': _('Cheques in Clearing'),
                'subtitle': _('Follow up with the bank for clearance confirmation'),
                'count': cheques_in_clearing_count,
                'amount': cheques_in_clearing_amount,
                'icon': 'fa-university',
                'severity': 'info',
                'badge': _('In Clearing'),
                'badge_color': 'blue',
                'icon_color': 'sky',
                'action_model': 'wecare.cheque.register',
                'action_name': _('Cheques in Clearing'),
                'action_domain': base_cheque_domain + [('state', '=', 'deposited')],
            },
            {
                'id': 'bounced_cheques',
                'title': _('Bounced Cheques'),
                'subtitle': _('Record follow-up, replacement or settlement'),
                'count': cheques_bounced_count,
                'amount': cheques_bounced_amount,
                'icon': 'fa-times-circle',
                'severity': 'danger' if cheques_bounced_count > 0 else 'secondary',
                'badge': _('Action Req.') if cheques_bounced_count > 0 else _('None'),
                'badge_color': 'red' if cheques_bounced_count > 0 else 'gray',
                'icon_color': 'red' if cheques_bounced_count > 0 else 'gray',
                'action_model': 'wecare.cheque.register',
                'action_name': _('Bounced Cheques'),
                'action_domain': bounced_domain + ([('outstanding', '=', True)] if 'outstanding' in cheque_model._fields else []),
            },
            {
                'id': 'high_balance_customers',
                'title': _('High Outstanding Customers'),
                'subtitle': _('Inspect top debtors and coordinate credit recovery'),
                'count': len(set(open_customer_invoices.mapped('partner_id').ids)),
                'amount': total_receivables,
                'icon': 'fa-users',
                'severity': 'primary',
                'badge': _('Debtor Review'),
                'badge_color': 'purple',
                'icon_color': 'purple',
                'action_model': 'res.partner',
                'action_name': _('Customers with Outstanding Balances'),
                'action_domain': [('id', 'in', open_customer_invoices.mapped('partner_id').ids)],
            },
        ]

        # ---------------------------------------------------------------------
        # ROW 5: Sales and Customer Performance
        # ---------------------------------------------------------------------
        partner_sales = defaultdict(float)
        for inv in invoices_period:
            if inv.partner_id:
                partner_sales[inv.partner_id.id] += inv.amount_untaxed_signed

        partner_receivables = defaultdict(float)
        partner_overdue = defaultdict(float)
        for inv in open_customer_invoices:
            if inv.partner_id:
                partner_receivables[inv.partner_id.id] += inv.amount_residual_signed
                if (inv.invoice_date and inv.invoice_date <= cutoff_date_45) or (inv.invoice_date_due and inv.invoice_date_due < today):
                    partner_overdue[inv.partner_id.id] += inv.amount_residual_signed

        all_relevant_partner_ids = set(partner_sales.keys()) | set(partner_receivables.keys())
        partners = self.env['res.partner'].browse(list(all_relevant_partner_ids))
        top_customers_list = []
        for p in partners:
            s_amt = partner_sales.get(p.id, 0.0)
            rec_amt = partner_receivables.get(p.id, 0.0)
            od_amt = partner_overdue.get(p.id, 0.0)
            c_type = getattr(p, 'wecare_customer_type', False) or getattr(p, 'customer_type', False) or 'Customer'
            if s_amt > 0 or rec_amt > 0:
                top_customers_list.append({
                    'partner_id': p.id,
                    'name': p.display_name,
                    'customer_type': dict(CUSTOMER_TYPES).get(c_type, str(c_type).capitalize()),
                    'sales_amount': float_round(s_amt, 2),
                    'outstanding_balance': float_round(rec_amt, 2),
                    'overdue_balance': float_round(od_amt, 2),
                })
        top_customers_list.sort(key=lambda x: (x['sales_amount'], x['outstanding_balance']), reverse=True)
        top_customers_display = top_customers_list[:15]

        # Salesperson Performance
        salesperson_stats = defaultdict(lambda: {'target': 0.0, 'actual': 0.0, 'name': ''})
        if plans:
            target_lines = self.env['wecare.sales.target.line'].search([('plan_id', 'in', plans.ids)])
            for t_line in target_lines:
                user = t_line.salesperson_id
                if user:
                    line_target = 0.0
                    price = t_line.unit_price or 0.0
                    if len(months_in_range) >= 12 or active_range in ('ytd', 'custom'):
                        line_target = t_line.annual_revenue or (t_line.annual_qty * price)
                    else:
                        for m in months_in_range:
                            line_target += getattr(t_line, f'qty_{month_abbrs[m - 1]}', 0.0) * price
                    salesperson_stats[user.id]['target'] += line_target
                    salesperson_stats[user.id]['name'] = user.name

        for inv in invoices_period:
            sp = inv.invoice_user_id or inv.user_id
            if sp:
                salesperson_stats[sp.id]['actual'] += inv.amount_untaxed_signed
                salesperson_stats[sp.id]['name'] = sp.name

        salesperson_performance = []
        for sp_id, data in salesperson_stats.items():
            tgt = data['target']
            act = data['actual']
            ach = (act / tgt * 100.0) if tgt > 0 else (100.0 if act > 0 else 0.0)
            diff = act - tgt
            salesperson_performance.append({
                'salesperson_id': sp_id,
                'name': data['name'] or _('Unassigned'),
                'target': float_round(tgt, 2),
                'actual': float_round(act, 2),
                'achievement_pct': float_round(ach, 1),
                'variance': float_round(diff, 2),
            })
        salesperson_performance.sort(key=lambda x: x['actual'], reverse=True)

        # Product Sales Performance
        inv_lines = self.env['account.move.line'].search([
            ('company_id', '=', company.id),
            ('move_id.move_type', 'in', ('out_invoice', 'out_refund')),
            ('move_id.state', '=', 'posted'),
            ('move_id.invoice_date', '>=', start_date),
            ('move_id.invoice_date', '<=', end_date),
            ('product_id', '!=', False),
            ('display_type', '=', 'product'),
        ])
        product_stats = defaultdict(lambda: {'qty': 0.0, 'revenue': 0.0, 'product': None})
        for l in inv_lines:
            sign = -1 if l.move_id.move_type == 'out_refund' else 1
            product_stats[l.product_id.id]['qty'] += (l.quantity * sign)
            product_stats[l.product_id.id]['revenue'] += (l.price_subtotal * sign)
            product_stats[l.product_id.id]['product'] = l.product_id

        product_performance = []
        for p_id, d in product_stats.items():
            prod = d['product']
            rev = d['revenue']
            qty = d['qty']
            avg_p = (rev / qty) if qty > 0 else 0.0
            product_performance.append({
                'product_id': p_id,
                'name': prod.name,
                'default_code': prod.default_code or '',
                'category': prod.categ_id.name or '',
                'qty_sold': float_round(qty, 2),
                'uom': prod.uom_id.name or '',
                'revenue': float_round(rev, 2),
                'avg_price': float_round(avg_p, 2),
            })
        product_performance.sort(key=lambda x: x['revenue'], reverse=True)
        product_performance_display = product_performance[:15]

        # Salesperson Collections
        sp_collections = defaultdict(lambda: {'cheque': 0.0, 'cash': 0.0, 'other': 0.0, 'count': 0, 'name': ''})
        for c in collections_in_period:
            sp = c.salesperson_id
            sp_id = sp.id if sp else 0
            sp_name = sp.name if sp else _('Unassigned')
            sp_collections[sp_id]['name'] = sp_name
            sp_collections[sp_id]['count'] += 1
            amt = c.amount or 0.0
            if c.collection_type in ('cheque', 'cpo'):
                sp_collections[sp_id]['cheque'] += amt
            elif c.collection_type == 'cash':
                sp_collections[sp_id]['cash'] += amt
            else:
                sp_collections[sp_id]['other'] += amt

        salesperson_collections = []
        for sp_id, data in sp_collections.items():
            t_col = data['cheque'] + data['cash'] + data['other']
            salesperson_collections.append({
                'salesperson_id': sp_id,
                'name': data['name'],
                'cheque_amount': float_round(data['cheque'], 2),
                'cash_amount': float_round(data['cash'], 2),
                'other_amount': float_round(data['other'], 2),
                'total_collected': float_round(t_col, 2),
                'count': data['count'],
            })
        salesperson_collections.sort(key=lambda x: x['total_collected'], reverse=True)

        # Bank Deposit Summary
        bank_journals = self.env['account.journal'].search([
            ('company_id', '=', company.id),
            ('type', '=', 'bank'),
        ])
        bank_summary = []
        for bj in bank_journals:
            deposited_in_bank = cheque_model.search(base_cheque_domain + [
                ('journal_id', '=', bj.id),
                ('deposit_date', '>=', start_date),
                ('deposit_date', '<=', end_date),
            ])
            cleared_in_bank = deposited_in_bank.filtered(lambda c: c.state == 'cleared')
            in_clearing_bank = deposited_in_bank.filtered(lambda c: c.state == 'deposited')
            bounced_in_bank = deposited_in_bank.filtered(lambda c: c.state == 'bounced')
            
            tot_dep = sum(deposited_in_bank.mapped('amount'))
            tot_clr = sum(cleared_in_bank.mapped('amount'))
            tot_pend = sum(in_clearing_bank.mapped('amount'))
            tot_bnc = sum(bounced_in_bank.mapped('amount'))

            if tot_dep > 0 or tot_pend > 0 or tot_clr > 0:
                bank_summary.append({
                    'journal_id': bj.id,
                    'journal_name': bj.name,
                    'bank_name': bj.bank_id.name if bj.bank_id else (bj.name or ''),
                    'acc_number': bj.bank_acc_number or '',
                    'total_deposited': float_round(tot_dep, 2),
                    'cleared_amount': float_round(tot_clr, 2),
                    'in_clearing_amount': float_round(tot_pend, 2),
                    'bounced_amount': float_round(tot_bnc, 2),
                })
        
        # Cash journals balance
        cash_journals = self.env['account.journal'].search([
            ('company_id', '=', company.id),
            ('type', '=', 'cash'),
        ])
        cash_summary = {
            'total_cash_collected_period': float_round(collection_breakdown['cash'], 2),
            'cash_journals': [],
        }
        for cj in cash_journals:
            balance = 0.0
            if cj.default_account_id:
                balance = cj.default_account_id.current_balance
            cash_summary['cash_journals'].append({
                'journal_id': cj.id,
                'name': cj.name,
                'balance': float_round(balance, 2),
            })

        # Dynamic filter options for top ribbon
        territory_records = self.env['wecare.sales.territory'].search([('company_id', 'in', (company.id, False))])
        territory_options = [{'id': t.id, 'name': t.name} for t in territory_records]
        customer_type_options = [{'id': code, 'name': label} for code, label in CUSTOMER_TYPES]

        currency_info = {
            'symbol': 'Br',  # Matching screenshot display ('60000 Br')
            'position': 'after',
            'decimal_places': 0,
        }

        return {
            'company_name': company.name,
            'currency': currency_info,
            'active_range': active_range,
            'date_from': fields.Date.to_string(start_date),
            'date_to': fields.Date.to_string(end_date),
            'period_label': f"{start_date.strftime('%m/%d/%Y')} - {end_date.strftime('%m/%d/%Y')}",
            'filter_options': {
                'customer_types': customer_type_options,
                'territories': territory_options,
            },
            
            # Row 1: Executive Financial KPIs
            'financial_kpis': {
                'sales_this_month': float_round(sales_this_month, 0),
                'sales_selected_period': float_round(sales_selected_period, 0),
                'sales_target': float_round(target_amount, 0),
                'target_achievement_pct': float_round(target_achievement_pct, 1),
                'target_variance': float_round(target_variance, 0),
                'total_receivables': float_round(total_receivables, 0),
                'total_receivables_count': total_receivables_count,
                'overdue_receivables': float_round(overdue_receivables, 0),
                'overdue_count': overdue_count,
                'overdue_pct': float_round(overdue_pct, 1),
                'invoice_count': invoice_count_period,
            },

            # Row 2: Cheque Management KPIs
            'cheque_kpis': {
                'received_amount': float_round(cheques_received_amount, 0),
                'received_count': cheques_received_count,
                'in_clearing_amount': float_round(cheques_in_clearing_amount, 0),
                'in_clearing_count': cheques_in_clearing_count,
                'cleared_amount': float_round(cheques_cleared_amount, 0),
                'cleared_count': cheques_cleared_count,
                'bounced_amount': float_round(cheques_bounced_amount, 0),
                'bounced_count': cheques_bounced_count,
            },

            # Row 3: Sales and Collection Analysis
            'sales_collection_analysis': {
                'actual_sales': float_round(sales_selected_period, 0),
                'target_sales': float_round(target_amount, 0),
                'achievement_pct': float_round(target_achievement_pct, 1),
                'collections_by_method': {
                    'cheque': float_round(collection_breakdown['cheque'], 0),
                    'cash': float_round(collection_breakdown['cash'], 0),
                    'bank_transfer': float_round(collection_breakdown['bank_transfer'], 0),
                    'other': float_round(collection_breakdown['other'], 0),
                    'total': float_round(total_collections, 0),
                },
                'collection_counts': collection_counts,
                'total_items': total_collection_items,
                'chart_timeline': {
                    'labels': months_labels,
                    'sales': sales_timeline,
                    'targets': target_timeline,
                },
            },

            # Row 4: Management Action Center
            'action_center': action_center,

            # Row 5: Sales and Customer Performance
            'top_customers': top_customers_display,
            'salesperson_performance': salesperson_performance,
            'product_performance': product_performance_display,
            'salesperson_collections': salesperson_collections,
            'bank_summary': bank_summary,
            'cash_summary': cash_summary,
        }
