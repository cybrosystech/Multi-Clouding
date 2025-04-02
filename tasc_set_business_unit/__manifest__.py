{
    'name': 'Set Business Unit',
    'summary': """This module is used for populating business unit values""",
    'description': """
        1. This module is used for populating business unit values in journal items.
    """,
    'author': "",
    'website': "",
    'category': 'Accounting',
    'version': '17.0.1.0.0',
    'depends': ['analytic_account_colocation_type'],
    'data':
        ['security/ir.model.access.csv',
         'wizard/set_business_unit_views.xml',
         ],
    'installable': True,
    'auto_install': False,
    'application': False,

}
