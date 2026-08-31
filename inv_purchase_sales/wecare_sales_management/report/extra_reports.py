# -*- coding: utf-8 -*-
from odoo import api, models


class ReportChequeClassified(models.AbstractModel):
    _name = 'report.wecare_sales_management.report_cheque_classified'
    _description = 'Classified Cheque Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['wecare.weekly.report.wizard'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'wecare.weekly.report.wizard',
            'docs': docs,
        }


class ReportCollectionPerformance(models.AbstractModel):
    _name = 'report.wecare_sales_management.report_collection_performance'
    _description = 'Salesperson Collection Performance'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['wecare.weekly.report.wizard'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'wecare.weekly.report.wizard',
            'docs': docs,
        }


class ReportBankDepositSummary(models.AbstractModel):
    _name = 'report.wecare_sales_management.report_bank_deposit_summary'
    _description = 'Bank Deposit Summary'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['wecare.weekly.report.wizard'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'wecare.weekly.report.wizard',
            'docs': docs,
        }


class ReportSalesAnalysis(models.AbstractModel):
    _name = 'report.wecare_sales_management.report_sales_analysis'
    _description = 'Customer / Product Sales Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['wecare.sales.analysis.wizard'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'wecare.sales.analysis.wizard',
            'docs': docs,
        }


class ReportStockValuation(models.AbstractModel):
    _name = 'report.wecare_sales_management.report_stock_valuation'
    _description = 'Stock Valuation Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['wecare.stock.valuation.wizard'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'wecare.stock.valuation.wizard',
            'docs': docs,
        }


class ReportStockExpiry(models.AbstractModel):
    _name = 'report.wecare_sales_management.report_stock_expiry'
    _description = 'Stock Expiry Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['wecare.stock.valuation.wizard'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'wecare.stock.valuation.wizard',
            'docs': docs,
        }
