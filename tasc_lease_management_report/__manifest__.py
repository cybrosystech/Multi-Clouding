# -*- coding: utf-8 -*-
{
    'name': 'Lease Management Report',
    "version": "14.0.1.0.0",
    "category": "Accounting",
    'summary': 'Lease Management Report',
    'description': """ Generates an xlsx report of lease.""",
    'author': '',
    'maintainer': '',
    'company': '',
    'website': '',
    'depends': ['lease_management'],
    'data': [
        'security/ir.model.access.csv',
        'wizards/lease_contract_xlsx_report_wizard_views.xml',
        'wizards/lease_interest_amortization_report_wizard_views.xml',
        'wizards/lease_ll_rou_report_wizard_views.xml',
        'wizards/ll_aging_report_wizard_views.xml',
    ],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
