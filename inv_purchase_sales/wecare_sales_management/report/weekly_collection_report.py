# -*- coding: utf-8 -*-
from odoo import api, models


class ReportWeeklyCollection(models.AbstractModel):
    _name = 'report.wecare_sales_management.report_weekly_collection'
    _description = 'Weekly Collection Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['wecare.cheque.register'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'wecare.cheque.register',
            'docs': docs,
            'data': docs._get_collection_report_data(),
        }
