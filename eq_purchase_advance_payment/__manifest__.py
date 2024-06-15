# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright 2019 EquickERP
#
##############################################################################

{
    'name': 'Purchase Advance Payment',
    'category': 'Purchases',
    'version': '17.0.1.0.0',
    'author': 'Equick ERP',
    'description': """
        This Module allows to create Suppliers Advance payment from Purchase order.
        * Allow user to manage the Suppliers Advance payment for the Purchase order.
        * Manage with Multi Company & Multi Currency.
    """,
    'summary': """create Suppliers Advance payments from Purchase order advance 
    payment | purchase payment | advance purchase payment | purchase order payment
     register payment from purchase order register payment from po advance payment 
     purchase Supplier Advance Payments""",
    'depends': ['base', 'purchase'],
    'price': 10,
    'currency': 'EUR',
    'license': 'OPL-1',
    'website': "",
    'data': [
        'views/purchase_view.xml',
    ],
    'demo': [],
    'images': ['static/description/main_screenshot.png'],
    'installable': True,
    'auto_install': False,
    'application': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
