{
    'name': 'Deferred Expense Report',
    'summary': """Deferred expense report""",

    'description': """ This module is used for deferred expense report""",

    'author': "",
    'website': "",
    'category': 'Accounting',
    'version': '14.0.1.0.0',
    'depends': ['account_asset', 'account_reports',
                'cash_flow_statement_report'],

    'data':
        [
            'report/account_deferred_expense_report_views.xml',
        ]
}
