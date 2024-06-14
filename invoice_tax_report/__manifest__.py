# -*- coding: utf-8 -*-
{
    "name": "invoice_tax_report",
    "summary": "invoice_tax_report",
    'sequence': 1,
    'category': 'sale',
    'version': '17.0.0.1.0',
    'author': "Cybrosys Techno Solutions",
    'website': "https://www.cybrosys.com",
    "depends": ["account", 'base', 'web', 'sale'],
    'data': [
        "reports/format.xml",
        "reports/layout.xml",
        "reports/report_inv_tax_report.xml",
        "reports/report_uk_inv_tax_report.xml",
        "views/res_company_inherit.xml"
    ],
    'installable': True,
}
