# -*- coding: utf-8 -*-
{
    'name': 'Tasc Mass Allocation',
    'summary': """Module used for mass allocation""",
    'description': """Module used for mass allocation""",
    'author': 'Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': "https://www.cybrosys.com",
    'category': 'Accounting',
    'version': '17.0.1.0.0',
    'depends': ['account','analytic_account_colocation_type'],
    'data':
        [
            'security/ir.model.access.csv',
            'views/tasc_mass_allocation_views.xml',
            'views/unnatural_account_balance_views.xml',
        ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
