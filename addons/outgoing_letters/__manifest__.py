{
    'name': 'Outgoing Letters',
    'version': '18.0.1.33.0',
    'category': 'Productivity',
    'summary': 'Register and print outgoing letters with automatic reference numbers',
    'depends': ['base', 'mail', 'web'],
    'data': [
        'security/outgoing_letter_security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'report/outgoing_letter_report.xml',
        'views/outgoing_letter_views.xml',
        'views/res_company_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'outgoing_letters/static/src/css/letter_form.css',
            'outgoing_letters/static/src/xml/letter_sidebar.xml',
            'outgoing_letters/static/src/js/letter_sidebar.js',
        ],
    },
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
