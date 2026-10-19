# -*- coding: utf-8 -*-
{
    'name': 'WeCare Executive Dashboard',
    'version': '18.0.1.0.0',
    'category': 'Sales/Reporting',
    'summary': 'Executive Financial KPIs, Cheque Management, Sales & Collections, Action Center & Performance',
    'description': """
WeCare Pharmaceuticals — Executive Management Dashboard
======================================================
Comprehensive executive dashboard built specifically for WeCare Pharmaceuticals:

- Row 1: Executive Financial KPIs
    * Sales This Month
    * Sales for the Selected Period
    * Sales Target Achievement (Actual sales vs approved target)
    * Total Receivables (Outstanding customer balances)
    * Overdue Receivables (with 45-day outstanding rule)

- Row 2: Cheque Management KPIs
    * Cheques Received: Total value received during the selected period
    * Cheques in Clearing: Deposited cheques awaiting bank confirmation
    * Cleared Cheques: Cheques confirmed by the bank
    * Bounced Cheques: Unresolved bounced cheque value

- Row 3: Sales and Collection Analysis
    * Sales vs Target (Actual vs Target, Achievement %, Monthly visual analysis)
    * Collection by Method (Cash, Bank Transfer, Cheque, Telebirr/Other)

- Row 4: Management Action Center
    * Overdue customer invoices (Follow up with customers and collection officers)
    * Cheques awaiting deposit (Confirm deposit and bank submission)
    * Cheques awaiting clearance (Follow up with the bank)
    * Bounced cheques (Record follow-up, replacement or settlement)
    * Customers with high outstanding balances

- Row 5: Sales and Customer Performance
    * Top customers by sales and outstanding balances
    * Salesperson target versus actual sales
    * Product sales performance
    * Salesperson collection achievement
    * Bank deposit summary and cash collection position
    """,
    'author': 'WeCare Pharmaceuticals / Niyat Consultancy',
    'depends': [
        'base',
        'web',
        'sale',
        'account',
        'stock',
        'wecare_sales_management',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/menu_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'wecare_executive_dashboard/static/src/css/dashboard_style.css',
            'wecare_executive_dashboard/static/src/components/chart_renderer/chart_renderer.xml',
            'wecare_executive_dashboard/static/src/components/chart_renderer/chart_renderer.js',
            'wecare_executive_dashboard/static/src/components/dashboard_card/dashboard_card.xml',
            'wecare_executive_dashboard/static/src/components/dashboard_card/dashboard_card.js',
            'wecare_executive_dashboard/static/src/components/executive_dashboard.xml',
            'wecare_executive_dashboard/static/src/components/executive_dashboard.js',
        ],
    },
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
