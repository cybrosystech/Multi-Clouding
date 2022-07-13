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
        "reports/format.xml",
        "reports/layout.xml",
        "reports/report_inv_tax_report.xml",

    ],
    'installable': True,
}
