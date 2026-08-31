# -*- coding: utf-8 -*-
from odoo import api, models


class ReportChequeClassified(models.AbstractModel):
    _name = 'report.wecare_sales_management.report_cheque_classified'
    _description = 'Classified Cheque Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['wecare.cheque.register'].browse(docids)
        klass = self.env.context.get('cheque_classification') or 'current'
        return {
            'doc_ids': docids,
            'doc_model': 'wecare.cheque.register',
            'docs': docs,
            'data': docs._get_classified_report_data(klass),
        }


class ReportCollectionPerformance(models.AbstractModel):
    _name = 'report.wecare_sales_management.report_collection_performance'
    _description = 'Salesperson Collection Performance'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['wecare.cheque.register'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'wecare.cheque.register',
            'docs': docs,
            'data': docs._get_collection_performance_report_data(),
        }


class ReportBankDepositSummary(models.AbstractModel):
    _name = 'report.wecare_sales_management.report_bank_deposit_summary'
    _description = 'Bank Deposit Summary'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['wecare.cheque.register'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'wecare.cheque.register',
            'docs': docs,
            'data': docs._get_bank_summary_report_data(),
        }


class ReportSalesAnalysis(models.AbstractModel):
    _name = 'report.wecare_sales_management.report_sales_analysis'
    _description = 'Customer / Product Sales Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        lines = self.env['account.move.line'].browse(docids)
        group_by = self.env.context.get('wecare_sales_group', 'customer')
        return {
            'doc_ids': docids,
            'doc_model': 'account.move.line',
            'docs': lines,
            'data': lines._wecare_sales_analysis_data(group_by),
        }


class ReportStockValuation(models.AbstractModel):
    _name = 'report.wecare_sales_management.report_stock_valuation'
    _description = 'Stock Valuation Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['stock.valuation.layer'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'stock.valuation.layer',
            'docs': docs,
            'data': docs._wecare_valuation_report_data(),
        }


class ReportStockExpiry(models.AbstractModel):
    _name = 'report.wecare_sales_management.report_stock_expiry'
    _description = 'Stock Expiry Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['stock.lot'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'stock.lot',
            'docs': docs,
        }
