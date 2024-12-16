{
    'name': 'Tasc Cash Burn GL Report',
    'summary': """The module is used for Tasc Cash Burn GL Report""",
    'description': """The module is used for Tasc Cash Burn GLReport""",
    'author': " Cybrosys Technologies",
    'website': "",
    'category': 'Accounting',
    'version': '17.0.1.0.0',
    'depends': ['account_accountant', 'cash_flow_statement_report'],
    'data':
        [
            'security/ir.model.access.csv',
            'wizard/cash_burn_report_gl_wizard_views.xml',
        ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
