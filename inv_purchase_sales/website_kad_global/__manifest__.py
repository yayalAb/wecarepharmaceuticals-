# -*- coding: utf-8 -*-
{
    'name': 'KAD Global Website',
    'version': '18.0.1.4.3',
    'summary': 'Custom public website for KAD Import & Export',
    'description': """
        Branded Odoo website for Kalkidan Abebaw Derso Import & Export (KADIE).

        - Homepage with company story, services, products, and contact
        - Brand colors from the KAD logo (blue / green)
        - Typography and UI patterns inspired by Niyat POS landing pages
        - Content aligned with kadglobaltrading.com
    """,
    'author': 'Niyat Consultancy.',
    'website': 'https://kadglobaltrading.com',
    'category': 'Website/Theme',
    'license': 'LGPL-3',
    'depends': ['website'],
    'data': [
        'data/unlock_homepage.xml',
        'views/homepage_body.xml',
        'views/layout.xml',
        'views/thanks.xml',
        'data/pages/home.xml',
        'data/menu.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'website_kad_global/static/src/css/kad_website.css',
            'website_kad_global/static/src/js/kad_website.js',
        ],
    },
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': False,
}
