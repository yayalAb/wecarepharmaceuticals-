# -*- coding: utf-8 -*-
{
    'name': 'Customer Compliance Document Management',
    'version': '18.0.1.0.4',
    'category': 'Sales/CRM',
    'summary': 'Track customer trade licenses and certificates; block Sales Orders when expired',
    'description': """
Customer Compliance Document Management
=======================================
Maintain trade licenses, business licenses, registrations, and certificates
per customer. Automatically compute Valid / Expiring Soon / Expired status
and prevent confirming Sales Orders when required documents are missing or expired.
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
