{
    'name': 'Payment Summary Reports',
    'summary': """ Payment Summary Reports""",

    'description': """
    1. Payment summary report
    """,

    'author': "",
    'website': "",
    'category': 'Accounting',
    'version': '14.0.1.0.0',
    'depends': ['account', 'cash_flow_statement_report'],

    'data':
        [
            'security/ir.model.access.csv',
            'wizard/payment_report_bank_integration_view.xml',
        ],
    'qweb': [
    ],
}
