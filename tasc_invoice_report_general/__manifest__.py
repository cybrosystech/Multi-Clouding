# -*- coding: utf-8 -*-
{
    'name': 'Generic Report - Invoices, Debit Note, Credit Note',
    "version": "17.0.1.0.0",
    "category": "Accounting",
    'summary': 'Generates a general  report for invoices, debit note and '
               'credit note',
    'description': """ Generates a pdf report for the credit note and debit
     note.""",
    'author': "Cybrosys Techno Solutions",
    'maintainer': "Cybrosys Techno Solutions",
    'company': "Cybrosys Techno Solutions",
    'website': "https://www.cybrosys.com",
    'depends': ['invoice_tax_report'],
    'data': [
        'reports/layout.xml',
        'reports/format.xml',
        'reports/account_move_report_templates.xml',
        'reports/account_move_report.xml',
        'reports/credit_note_views.xml',
        'reports/invoice_report_general_template.xml',
    ],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
