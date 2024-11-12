{
    'name': 'Payment Approval',
    'summary': """Payment Approval""",
    'description': """
    1.Payment approval by batches..
    """,
    'author': "Aswathi",
    'website': "",
    'category': 'Accounting',
    'version': '17.0.1.0.0',
    'depends': ['account', 'analytic_account_types'],
    'data':
        [
            'data/mail_template.xml',
            'security/ir.model.access.csv',
            'security/security.xml',
            'views/purpose_code_view.xml',
            'views/default_purpose_code_view.xml',
            'views/account_payment.xml',
            'views/payment_approval_check.xml',
            'wizard/account_register_payment_view.xml',
            'wizard/account_payment_approval.xml',

        ],
    'qweb': [
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
