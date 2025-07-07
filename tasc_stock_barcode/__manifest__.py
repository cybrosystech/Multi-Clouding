# -*- coding: utf-8 -*-

{
    'name': 'Asset Barcode',
    'summary': """This module is used for adding barcode
        scanning for assets""",
    'description': """
        1. This module is used for adding barcode
     scanning for assets.
    """,
    'author': "",
    'website': "",
    'category': 'Inventory/Inventory',
    'version': '17.0.1.0.0',
    'depends': ['stock_barcode','account_asset','tasc_account_assets'],
    'data':
        [
        'security/ir.model.access.csv',
        'views/asset_barcode_view.xml'
         ],
    'assets': {
        'web.assets_backend': [
            'tasc_stock_barcode/static/src/**/*.js',
            'tasc_stock_barcode/static/src/**/*.xml',
    ]},
    'installable': True,
    'auto_install': False,
    'application': False,

}
