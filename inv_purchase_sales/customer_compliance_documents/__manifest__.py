# -*- coding: utf-8 -*-
{
    'name': 'Customer Compliance Document Management',
    'version': '18.0.1.1.0',
    'category': 'Sales/CRM',
    'summary': 'Customer Compliance Documents: licenses/certificates with SO confirmation control',
    'description': """
Customer Compliance Document Management
=======================================
Customer → Compliance Documents tab:
- Document Type, Document Number, Issue Date, Expiry Date
- Status: Valid / Expiring Soon / Expired
- Attachment and Remarks

Sales Order Control:
- On confirm, check mandatory documents are valid
- Block with warning when documents are missing or expired
- Expiring Soon within configurable days (default 30)
    """,
    'author': 'Niyat Consultancy',
    'depends': [
        'base',
        'contacts',
        'mail',
        'account',
        'sale_management',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/compliance_document_type_data.xml',
        'data/ir_cron_data.xml',
        'views/compliance_document_type_views.xml',
        'views/compliance_document_views.xml',
        'views/res_partner_views.xml',
        'views/sale_order_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'pre_init_hook': 'pre_init_hook',
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
