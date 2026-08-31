# -*- coding: utf-8 -*-
from odoo import api, models


class ReportTargetVsActual(models.AbstractModel):
    _name = 'report.wecare_sales_management.report_target_vs_actual'
    _description = 'Target vs Actual Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['wecare.sales.target.line'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'wecare.sales.target.line',
            'docs': docs,
        }
