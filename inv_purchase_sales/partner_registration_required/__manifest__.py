{
    'name': 'Partner Registration Required Fields',
    'version': '18.0.1.0.4',
    'category': 'Sales/CRM',
    'summary': 'Require Tax ID and Phone on customer and vendor registration',
    'description': """
        Makes Tax ID and Phone mandatory when creating or updating
        top-level customers and vendors (res.partner without a parent company).

        Also provides Odoo 18 compatibility stubs/fixes for partner form views
        that still reference removed fields such as duplicate_bank_partner_ids.
    """,
    'author': 'Universal Food Complex PLC',
    'depends': [
        'base',
        'contacts',
        'account',
    ],
    'data': [
        'views/res_partner_views.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
