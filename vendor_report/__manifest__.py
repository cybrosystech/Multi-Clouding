# -*- coding: utf-8 -*-
{
    'name': 'Vendor Report',
    'summary': """Generate the vendor bills report""",
    'description': """This module has been developed for generating excel 
    report of bills""",
    'author': "Cybrosys Techno Solutions",
    'website': "https://www.cybrosys.com",
    'category': 'Accounting',
    'version': '17.0.1.0.0',
    'depends': ['account', 'base'],
    'data':
        [
            'security/ir.model.access.csv',
            'wizard/vendor_report_wizard.xml',
            'wizard/vendor_pdf_report.xml',
        ],
    'assets': {
        'web.assets_backend': [
            'vendor_report/static/src/js/vendor_report_wizard.js',
            'vendor_report/static/src/js/action_manager.js',
            'vendor_report/static/src/xml/control_panel_bills_inherit.xml',
        ],
    },
}
