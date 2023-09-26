# -*- coding: utf-8 -*-
{
    'name': "Chart of Account Inter Company Balance Report",
    'summary': """ Chart of Account Inter Company Balance Report """,
    'author': "",
    "version": "14.0.1.0.0",
    "category": "Accounting",
    "depends": ["account", "cash_flow_statement_report"],
    "data": [
        'security/ir.model.access.csv',
        'wizards/account_balance_report_wizard_views.xml',
        'reports/account_reports.xml',
        'reports/account_report_template.xml',
    ],
    "license": 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
