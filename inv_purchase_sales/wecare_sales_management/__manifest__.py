# -*- coding: utf-8 -*-
{
    'name': 'WeCare Sales Management',
    'version': '18.0.1.3.0',
    'category': 'Sales',
    'summary': 'Sales plan, cheque lifecycle, weekly reports, share to media, invoice-time stock',
    'description': """
WeCare Pharmaceuticals — Sales Planning, Collections and Weekly Reporting
=========================================================================
- Sales Plan and salesperson/customer/product targets
- Target vs actual sales analysis
- Cheque register: received, deposited, cleared, bounced, re-deposit
- Current / Previous / Bounce classification for weekly reports
- Weekly collection and weekly bank-deposited credit sales reports
- Share to Media (WhatsApp / Telegram) on sales, purchase and inventory documents
- Stock location, batch and expiry carried through quotation → SO → invoice → delivery
- Stock deduction on customer invoice validation
- Expiry date notifications
    """,
    'author': 'Niyat Consultancy',
    'depends': [
        'sale_management',
        'sale_stock',
        'stock',
        'stock_account',
        'account',
        'purchase',
        'purchase_stock',
        'mail',
        'product_expiry',
        'sales_team',
        'purchase_request',
        'store_request',
        'custom_payment',
        'sale_line_serial_expiry',
        'stock_picking_custom',
    ],
    'data': [
        'security/wecare_security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/ir_cron_data.xml',
        'views/res_partner_views.xml',
        'views/sales_territory_views.xml',
        'views/sales_plan_views.xml',
        'views/cheque_register_views.xml',
        'views/share_history_views.xml',
        'views/sale_order_views.xml',
        'views/account_move_views.xml',
        'views/stock_picking_views.xml',
        'views/purchase_order_views.xml',
        'views/account_payment_views.xml',
        'views/supplies_rfp_views.xml',
        'views/stock_scrap_views.xml',
        'views/store_request_views.xml',
        'views/res_config_settings_views.xml',
        'views/reporting_views.xml',
        'wizard/weekly_report_wizard_views.xml',
        'wizard/target_vs_actual_wizard_views.xml',
        'wizard/share_to_media_wizard_views.xml',
        'wizard/kpi_wizard_views.xml',
        'wizard/sales_analysis_wizard_views.xml',
        'wizard/stock_valuation_wizard_views.xml',
        'report/wecare_report_paperformat.xml',
        'report/weekly_collection_report.xml',
        'report/weekly_bank_deposit_report.xml',
        'report/sales_plan_report.xml',
        'report/target_vs_actual_report.xml',
        'report/extra_reports.xml',
        'views/menus.xml',
    ],
    'pre_init_hook': 'pre_init_hook',
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
