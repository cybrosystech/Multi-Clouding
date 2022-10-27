{
    'name': 'Account Asset Budget Check',
    'summary': """""",

    'description': """""",

    'author': "",
    'website': "",
    'category': 'Accounting',
    'version': '14.0.1.0.0',
    'depends': ['account', 'analytic_account_types', 'approve_status'],

    'data':
        [
            'security/ir.model.access.csv',
            'security/budget_asset_check.xml',
            'data/data.xml',
            'views/in_out_assets_budget.xml',
            'views/account_asset_view_inherit.xml',
        ]
}
