# Copyright 2013 Savoir-faire Linux
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "invoice_tax_report",
    "summary": "invoice_tax_report",
    'sequence': 1,
    'category': 'sale',
    'version': '0.1',
    "depends": [
       "account",'base','web','sale'
    ],
    'data': [

        "views/account_invoice.xml",
        "views/sale_order.xml",
        "reports/format.xml",
        "reports/layout.xml",
        "reports/report_inv_tax_report.xml",

    ],
    'installable': True,
}
