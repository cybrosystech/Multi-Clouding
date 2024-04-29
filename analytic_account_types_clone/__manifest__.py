{
    'name': 'Analytic Account Types Clone',
    'summary': """""",

    'description': """""",

    'author': "",
    'website': "",
    'category': 'Accounting',
    'version': '17.0.1.0.0',
    'depends': ['analytic_account_types', 'analytic',
                'account_asset'],
    'data': [
        'views/account_move.xml',
        'views/sale_order_line.xml',
    ],
    'qweb': [],
    'installable': True,
    'auto_install': False,
    'application': False,
}
