{
    'name': 'Assets Sub Model',
    'summary': """""",

    'description': """""",

    'author': "",
    'website': "",
    'category': 'Accounting',
    'version': '14.0.1.0.0',
    'depends': ['account_asset', 'analytic_account_types'],

    'data':
        [
            'security/ir.model.access.csv',
            'views/assets_sub_model_view.xml',
            'views/account_asset_inherit_submodel_view.xml',
        ]
}