{
    'name': 'TASC Bill Payment Report',
    'summary': """The module is used for TASC Bill Payment Report""",
    'description': """The module is used for  TASC Bill Payment Report""",
    'author': " Cybrosys Technologies",
    'website': "",
    'category': 'Accounting',
    'version': '17.0.1.0.0',
    'depends': ['account_accountant', 'lease_management'],
    'data':
        [
            'security/ir.model.access.csv',
            'wizard/bill_payment_report_wizard_views.xml',
        ],
}
