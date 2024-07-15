{
    'name': 'Tasc Cash Burn Report',
    'summary': """The module is used for Tasc Cash Burn Report""",

    'description': """The module is used for Tasc Cash Burn Report""",

    'author': " Cybrosys Technologies",
    'website': "",
    'category': 'Accounting',
    'version': '17.0.1.0.0',
    'depends': ['account_accountant', 'cash_flow_statement_report'],

    'data':
        [
            'security/ir.model.access.csv',
            'wizard/cash_burn_report_wizard_views.xml',
        ],

    'qweb': [],
}
