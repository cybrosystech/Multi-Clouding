{
    'name': 'Payment Approval',
    'summary': """""",

    'description': """
    1. Modify cost center on journal items and invoice lines.
    """,

    'author': "Aswathi",
    'website': "",
    'category': 'Accounting',
    'version': '14.0.1.0.0',
    'depends': ['account', 'analytic_account_types'],

    'data':
        [
            'data/mail_template.xml',
            'security/ir.model.access.csv',
            'security/security.xml',
            'views/purpose_code_view.xml',
            'wizard/account_payment_approval.xml',
            'wizard/account_register_payment_view.xml',
            'views/account_payment.xml',
            'views/payment_approval_check.xml',
            'views/default_purpose_code_view.xml',
        ],
    'qweb': [
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
