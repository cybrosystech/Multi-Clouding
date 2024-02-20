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
            'wizard/account_payment_approval.xml',
            'views/account_payment.xml',
            'views/payment_approval_check.xml',
        ],
    'qweb': [
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
