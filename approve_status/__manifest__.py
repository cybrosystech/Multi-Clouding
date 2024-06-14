{
    'name': 'Approve Status',
    'summary': """""",

    'description': """""",

    'author': "",
    'website': "",
    'category': 'Accounting',
    'version': '1.0',
    'depends': ['account', 'analytic_account_types', 'account_asset'],

    'data':
        [
            'security/ir.model.access.csv',
            'data/mail_template.xml',
            'wizard/budget_reject_reason_wizard.xml',
            # 'view/reset_to_draft.xml',
            'view/approve_status.xml',
            'view/reject_button_budget_check.xml'
        ],
    "license": 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
