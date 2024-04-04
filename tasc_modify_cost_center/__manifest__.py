{
    'name': 'Modify Cost center',
    'summary': """""",

    'description': """
    1. Modify cost center on journal items and invoice lines.
    """,

    'author': "",
    'website': "",
    'category': 'Accounting',
    'version': '17.0.1.0.0',
    'depends': ['analytic_account_colocation_type'],

    'data':
        ['security/ir.model.access.csv',
         'wizard/cost_center_modify_views.xml',
         ],
    'qweb': [
    ],
}
