{
    'name': 'Partial Assets Sale',
    'summary': """""",

    'description': """""",

    'author': "",
    'website': "",
    'category': 'Accounting',
    'version': '17.0.1.0.0',
    'depends': ['account_asset', 'lease_management', 'assets_sub_models_config'],

    'data':
        [
            'views/asset_sell_inherit_view.xml',
            'views/account_aaset_form_capex_inherit.xml',
        ],
  "license": 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
