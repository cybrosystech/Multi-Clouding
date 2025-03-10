# -*- coding: utf-8 -*-
{
    'name': 'TASC Incorrect Entry Report',
    'version': '17.0.1.0.0',
    'category': 'Extra Tools',
    'summary': """
       THe app is used for Incorrect Entry Report.
        """,
    'description': """
         The module is used for Incorrect Entry Report.
        """,
    'author': 'Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': 'https://www.cybrosys.com',
    'depends': ['analytic_account_colocation_type','account_reports'],
    'data': [
        'views/tasc_incorrect_entry_report_views.xml'
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
