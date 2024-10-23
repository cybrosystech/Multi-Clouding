# -*- coding: utf-8 -*-
{
    'name': "TASC Purchase Report",
    'summary': """
            TASC Purchase Reports.
        """,
    'description': """ Purchase Reports""",
    'author': "",
    'website': "",
    'category': 'Accounting',
    'version': '17.0.1.0.0',
    'depends': ['purchase', 'purchase_stock'],
    'data': [
        'views/purchase_order_views.xml',
        'reports/purchase_reports.xml',
        'reports/purchase_order_templates.xml',
    ],
    "license": 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
