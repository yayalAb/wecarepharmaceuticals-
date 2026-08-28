# -*- coding: utf-8 -*-
from odoo import api, models


class ReportSalesPlan(models.AbstractModel):
    _name = 'report.wecare_sales_management.report_sales_plan'
    _description = 'Sales Plan Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['wecare.sales.plan'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'wecare.sales.plan',
            'docs': docs,
        }
