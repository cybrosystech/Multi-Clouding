# -*- coding: utf-8 -*-
{
    'name': 'Tasc Trial Balance Report',
    'summary': """""",
    'description': """""",
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
        ],
}
