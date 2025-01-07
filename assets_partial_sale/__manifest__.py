{
    'name': 'Partial Assets Sale',
    'summary': """Module for asset partial sale.""",
    'description': """Module for asset partial sale.""",
    'author': "",
    'website': "",
    'category': 'Accounting',
    'version': '17.0.1.0.0',
    'depends': ['account_asset', 'lease_management', 'assets_sub_models_config'],
    'data':
        [   'data/account_asset_data.xml',
            'views/asset_sell_inherit_view.xml',
            'views/account_aaset_form_capex_inherit.xml',
        ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
