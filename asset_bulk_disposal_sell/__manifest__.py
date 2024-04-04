{
    'name': 'Assets Bulk Sale/Disposal',
    'summary': """This module helps to sell or dispose assets on selected assets""",

    'description': """""",

    'author': "",
    'website': "",
    'category': 'account_asset',
    'version': '17.0.1.0.0',
    'depends': ['account_asset'],

    'data':
        [
            'security/ir.model.access.csv',
            'views/account_asset_sell_dispose.xml',
            'views/account_asset_bulk_wizard_view.xml',
            'views/account_asset_bulk_relation_view.xml',
        ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
