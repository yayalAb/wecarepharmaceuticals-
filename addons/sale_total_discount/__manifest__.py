{
    'name': 'Sale Order Total Discount',
    'version': '18.0.1.2.0',
    'category': 'Sales',
    'summary': 'Display Sub Total, Total Discount, and Grand Total on sales orders and customer invoices.',
    'author': 'Niyat ERP',
    'license': 'LGPL-3',
    'depends': ['sale_management', 'account'],
    'data': [
        'views/report_tax_totals.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'sale_total_discount/static/src/xml/tax_totals.xml',
        ],
    },
    'installable': True,
    'application': False,
}
