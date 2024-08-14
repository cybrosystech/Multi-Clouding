{
    'name': 'Deferred Expense Report',
    'summary': """Deferred expense report""",

    'description': """ This module is used for deferred expense report""",

    'author': "",
    'website': "",
    'category': 'Accounting',
    'version': '17.0.1.0.0',
    'depends': ['account_accountant','account_asset', 'account_reports',
                'cash_flow_statement_report', 'tasc_budget_analysis_report'],

    'data':
        [
            'security/ir.model.access.csv',
            'views/account_move_views.xml',
            'wizard/deferred_expense_wizard_view.xml',
            # 'report/tasc_deferred_expense_report.xml',
        ],

}
