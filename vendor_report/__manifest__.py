{
    'name': 'Vendor Report',
    'summary': """Generate the vendor bills report""",

    'description': """This module has been developed for generating excel 
    report of bills""",

    'author': "",
    'website': "",
    'category': 'Accounting',
    'version': '14.0.1.0.0',
    'depends': ['account'],

    'data':
        [
            'security/ir.model.access.csv',
            'views/assets.xml',
            'wizard/vendor_report_wizard.xml',
            'wizard/vendor_pdf_report.xml',
        ],

    'qweb': [
            'static/src/xml/control_panel_bills_inherit.xml',
        ],
}
