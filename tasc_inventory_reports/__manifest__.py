# -*- coding: utf-8 -*-
{
    'name': 'TASC Inventory Reports',
    'version': '17.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': """
        Module used for create some stock reports.
        """,
    'description': """
        Module used for create some stock reports.
        """,
    'author': 'Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': 'https://www.cybrosys.com',
    'depends': ['stock','analytic_account_types'],
    'data': [
        'security/ir.model.access.csv',
        'views/product_views.xml',
        'report/tasc_moves_history_views.xml',
        'report/tasc_locations_report_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
