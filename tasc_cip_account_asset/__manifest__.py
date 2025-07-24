# -*- coding: utf-8 -*-
{
    'name': 'Tasc Cip Account Asset',
    'version': '17.0.1.0.0',
    'summary': 'Asset creation from journal entry created from stock'
               'journal items',
    'description': '''
        Asset creation from journal entry created from stock'
               'journal items
    ''',
    'category': 'Accounting',
    'author': 'Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': 'https://www.cybrosys.com',
    'depends': ['account','analytic_account_colocation_type'],
    'data': [
        'security/ir.model.access.csv',
        'views/cip_account_asset_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}