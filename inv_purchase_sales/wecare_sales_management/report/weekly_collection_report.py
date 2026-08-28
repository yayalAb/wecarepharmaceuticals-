# -*- coding: utf-8 -*-
from odoo import api, models


class ReportWeeklyCollection(models.AbstractModel):
    _name = 'report.wecare_sales_management.report_weekly_collection'
    _description = 'Weekly Collection Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['wecare.weekly.report.wizard'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'wecare.weekly.report.wizard',
            'docs': docs,
        }
