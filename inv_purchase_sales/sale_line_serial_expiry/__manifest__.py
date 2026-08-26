# -*- coding: utf-8 -*-
{
    'name': 'Sale Line Serial & Expiration',
    'version': '18.0.1.0.0',
    'category': 'Sales',
    'summary': 'Serial Number, Quantity, and Expiration Date on sales quotation/order lines',
    'description': """
Serial Number, Quantity, and Expiration Date Management
=======================================================
On Sales Quotation and Sales Order lines:
- Serial Number (Lot/Serial from stock)
- Quantity (existing order quantity)
- Expiration Date (from the selected lot)

Selected lot is carried to Delivery Orders (stock moves) and shown on
Customer Invoices for traceability.
    """,
    'author': 'Niyat Consultancy',
    'depends': [
        'sale_management',
        'sale_stock',
        'stock',
        'product_expiry',
        'account',
    ],
    'data': [
        'views/sale_order_views.xml',
        'views/stock_picking_views.xml',
        'views/account_move_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
