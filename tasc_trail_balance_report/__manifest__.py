# -*- coding: utf-8 -*-
{
    'name': 'Tasc Trial Balance Reports',
    'summary': """ Tasc Trial Balance Report """,
    'description': """Tasc Trial Balance Report """,
    'author': "Cybrosys Techno Solutions",
    'website': "https://www.cybrosys.com",
    'category': 'Accounting',
    'version': '17.0.1.0.0',
    'depends': ['account_reports', 'cash_flow_statement_report'],
    'data':
        [
            'security/ir.model.access.csv',
            'views/tasc_trial_balance_report_view.xml',
            'wizard/tasc_trial_balance_detail_report_wizard_views.xml',
            'wizard/tasc_trial_balance_cc_report_views.xml',
        ],
}
