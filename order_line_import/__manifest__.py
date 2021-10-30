# -*- coding: utf-8 -*-
{
    'name': 'Import Order line',
    'category': 'Extra Tools',
    'author':'Bonainfo guoyihot@outlook.com ',
    'sequence': 1,
    'summary': """Import order line from excel file,such as sale order line,purchase orderline,bom line. """,
    'website': 'www.bonainfo.com',
    'version': '1.0',   
    'description': """Add a button to open wizard, easily import any order lines using the function by system default . """,
    'license': 'AGPL-3',
    'support': '124358678@qq.com, bower_guo@msn.com',
    'price': '0',
    'currency:': 'EUR',
    'images': ['static/description/main_banner.png'],
    'Read description for': ['v11.0','v10.0'],

    # any module necessary for this one to work correctly
    'depends': ['sale_management','sale','account',
                'purchase',
                'stock',
                #'mrp',
                'base_import'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/sale_order_line_views.xml',
        'views/purchase_order_line_views.xml',
        #'views/bom_line_views.xml',
        'views/stock_move_line_views.xml',
        'views/account_invoce_line_views.xml',
        'views/web.xml',
    ],
    # only loaded in demonstration mode
    #'demo': [
    #    'demo/demo.xml',
    #],
    #'qweb':['static/src/xml/*.xml']
}
