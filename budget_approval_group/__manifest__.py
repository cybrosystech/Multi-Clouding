{
    'name': 'Budget Approval Configuration',
    'summary': """Module for budget approval configuration""",
    'description': """Module for budget approval configuration""",
    'author': "",
    'website': "",
    'category': 'Accounting',
    'version': '1.0',
    'depends': ['analytic_account_types','tasc_deferred_expense_report'],
    'data':
        [
            'security/budget_approval_group.xml',
            'data/budget_approver_check_automated.xml',
            'views/account_move_form_inherit.xml',
        ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
