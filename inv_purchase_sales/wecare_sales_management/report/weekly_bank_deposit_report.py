# -*- coding: utf-8 -*-
from odoo import api, models


class ReportWeeklyBankDeposit(models.AbstractModel):
    _name = 'report.wecare_sales_management.report_weekly_bank_deposit'
    _description = 'Weekly Bank Deposited Credit Sales Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['wecare.cheque.register'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'wecare.cheque.register',
            'docs': docs,
            'data': docs._get_bank_deposit_report_data(),
        }
