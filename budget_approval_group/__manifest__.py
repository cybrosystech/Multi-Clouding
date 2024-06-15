{
    'name': 'Budget Approval Configuration',
    'summary': """""",

    'description': """""",

    'author': "",
    'website': "",
    'category': 'Accounting',
    'version': '1.0',
    'depends': ['analytic_account_types',
                ],

    'data':
        [
            'security/budget_approval_group.xml',
            'data/budget_approver_check_automated.xml',
            'views/account_move_form_inherit.xml',
        ],
    "license": 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
