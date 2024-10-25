{
    'name': 'Bank Reconciliation Report Inherit',
    'summary': """""",
    'description': """""",
    'author': "",
    'website': "",
    'category': 'Accounting',
    'version': '17.0.1.0.0',
    'depends': ['account', 'account_accountant', 'analytic_account_types',
                'account_reports'],
    'data':
        [
            'security/ir.model.access.csv',
            'data/account_bank_statement_data.xml',
            'data/mail_template.xml',
            'views/account_statement_approval_check_views.xml',
            'views/account_bank_statement_views.xml'
        ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
