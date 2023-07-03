# -*- coding: utf-8 -*-
{
    'name': 'Generic Report - Invoices, Debit Note, Credit Note',
    "version": "14.0.1.0.0",
    "category": "Accounting",
    'summary': 'Generates a general  report for invoices, debit note and '
               'credit note',
    'description': """ Generates a pdf report for the credit note and debit
     note.""",
    'author': '',
    'maintainer': '',
    'company': '',
    'website': '',
    'depends': ['account'],
    'data': [
        'views/account_move_views.xml',
        'report/layout.xml',
        'report/format.xml',
        'report/account_move_report_templates.xml',
        'report/account_move_report.xml',
    ],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
