{
    'name': 'Tasc Cash Burn Monthly Report',
    'summary': """The module is used for Tasc Cash Burn MOnthly Report""",
    'description': """The module is used for Tasc Cash Burn Monthly Report""",
    'author': " Cybrosys Technologies",
    'website': "",
    'category': 'Accounting',
    'version': '17.0.1.0.0',
    'depends': ['account_accountant', 'cash_flow_statement_report'],
    'data':
        [
            'security/ir.model.access.csv',
            'views/account_account.xml',
            'wizard/monthly_cash_burn_views.xml',
        ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
