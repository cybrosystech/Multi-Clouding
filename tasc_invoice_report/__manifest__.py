# -*- coding: utf-8 -*-
{
    'name': 'TASC Invoice Report',
    'version': '17.0.1.0.0',
    'category': 'Extra Tools',
    'summary': """
       THe app is used for Invoice Report.
        """,
    'description': """
         The module is used for Invoice Entry Report.
        """,
    'author': 'Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': 'https://www.cybrosys.com',
    'depends': ['account',],
    'data': [
        'security/ir.model.access.csv',
        'wizard/tasc_invoice_report_views.xml'
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
