{
    'name': 'Budget Approval Configuration',
    'summary': """""",

    'description': """""",

    'author': "",
    'website': "",
    'category': 'Accounting',
    'version': '14.0.1.0.0',
    'depends': ['base_automation', 'analytic_account_types', 'base'],

    'data':
        [
            'security/budget_approval_group.xml',
            'views/account_move_form_inherit.xml',
            'data/budget_approver_check_automated.xml'
        ]
}
