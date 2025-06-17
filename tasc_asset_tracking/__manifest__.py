# -*- coding: utf-8 -*-
{
    'name': "Asset Tracking",
    'summary': """ This module is used for asset tracking """,
    'description': """ This module is used for asset tracking """,
    'author': 'Cybrosys Techno Solutions',
    "version": "17.0.1.0.0",
    "category": "Accounting",
    "depends": ["analytic_account_types"],
    "data": [
            'data/account_asset_data.xml',
            'security/ir.model.access.csv',
            'views/account_asset_views.xml',
            'reports/product_template.xml',
            'reports/product_report.xml',
            'reports/product_report.xml',
            'wizard/tasc_asset_tracking_wizard.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
