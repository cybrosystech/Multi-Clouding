{
    'name': 'Payroll Reports',
    'summary': """ Payroll Reports""",

    'description': """
    1. Payment summary report
    """,

    'author': "",
    'website': "",
    'category': 'Accounting',
    'version': '17.0.1.0.0',
    'depends': ['account','hr_payroll'],

    'data':
        [
            'security/ir.model.access.csv',
            'views/hr_employee_views.xml',
            'views/res_partner_views.xml',
            'wizard/payroll_summary_views.xml',
            'wizard/bank_transfer_views.xml',
        ],
    'qweb': [
    ],
}
