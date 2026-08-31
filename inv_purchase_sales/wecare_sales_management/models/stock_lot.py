# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import fields, models


class StockLot(models.Model):
    _inherit = 'stock.lot'

    def _records_for_print(self):
        if self:
            return self
        return self.search(list(self.env.context.get('active_domain') or []))

    def action_print_stock_expiry(self):
        return self.env.ref(
            'wecare_sales_management.action_report_stock_expiry'
        ).report_action(self._records_for_print())

    def _cron_wecare_expiry_notification(self):
        companies = self.env['res.company'].search([])
        activity_type = self.env.ref('mail.mail_activity_data_todo')
        StockManager = self.env.ref('stock.group_stock_manager', raise_if_not_found=False)
        for company in companies:
            days = company.wecare_expiry_notify_days or 90
            limit = fields.Datetime.now() + timedelta(days=days)
            lots = self.search([
                ('company_id', '=', company.id),
                ('expiration_date', '!=', False),
                ('expiration_date', '<=', limit),
            ])
            lots = lots.filtered(lambda lot: lot.product_qty > 0)
            users = self.env['res.users']
            if StockManager:
                users = StockManager.users.filtered(
                    lambda u: company in u.company_ids and u.share is False
                )
            if not users:
                users = self.env.ref('base.user_admin')
            for lot in lots:
                existing = self.env['mail.activity'].search_count([
                    ('res_model', '=', 'stock.lot'),
                    ('res_id', '=', lot.id),
                    ('activity_type_id', '=', activity_type.id),
                    ('summary', 'ilike', 'expir'),
                ])
                if existing:
                    continue
                expiry = lot.expiration_date
                expiry_txt = fields.Datetime.context_timestamp(
                    lot, expiry
                ).strftime('%Y-%m-%d') if expiry else ''
                for user in users[:5]:
                    lot.activity_schedule(
                        'mail.mail_activity_data_todo',
                        user_id=user.id,
                        summary=self.env._('Batch/lot expiry: %s', lot.name),
                        note=self.env._(
                            'Lot/batch <b>%s</b> of product <b>%s</b> expires on %s. '
                            'On-hand quantity: %s',
                            lot.name,
                            lot.product_id.display_name,
                            expiry_txt,
                            lot.product_qty,
                        ),
                    )
