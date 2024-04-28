{
    'name': 'Accounting Customizations',
    'summary': """""",

    'description': """
    1. Add project site to vendor bills
    """,

    'author': "",
    'website': "",
    'category': 'Accounting',
    'version': '17.0.1.0.0',
    'depends': ['account', 'lease_management'],

    'data':
        [
            'views/account_move.xml',
            'views/account_move_line_views.xml',
        ],
    "license": 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
