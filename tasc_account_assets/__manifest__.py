# -*- coding: utf-8 -*-
{
    'name': "Asset Customizations",
    'summary': """ Show total for depreciable value field  """,
    'author': 'Cybrosys Techno Solutions',
    "version": "17.0.1.0.0",
    "category": "Accounting",
    "depends": ["assets_partial_sale"],
    "data": ['data/ir_cron_data.xml',
             'data/sequence.xml',
             'views/account_asset.xml', ],
    "license": 'AGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
