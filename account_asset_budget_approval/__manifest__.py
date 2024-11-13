{
    'name': 'Account Asset Budget Check',
    'summary': """The module contains asset approval""",
    'description': """The module contains asset approval""",
    'author': "",
    'website': "",
    'category': 'Accounting',
    'version': '1.0',
    'depends': ['account', 'analytic_account_types',
                'approve_status'],

    'data':
        [
            'security/ir.model.access.csv',
            'security/budget_asset_check.xml',
            'data/data.xml',
            'views/in_out_assets_budget.xml',
            'views/account_asset_view_inherit.xml',
        ],
    "license": 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
