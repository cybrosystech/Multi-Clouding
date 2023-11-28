{
    'name': 'Payslip Portal',
    'summary': """ The app has feature to add payslips to portal
     page. """,
    'description': """This app has the feature to add payslips to portal 
    page to download for employees""",
    'author': 'Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'website': 'https://www.cybrosys.com',
    'category': 'Website',
    'version': '14.0.1.0.0',
    'depends': ['base', 'portal', 'hr_payroll'],
    'data':
        [
            'security/hr_payslip_security.xml',
            'security/ir.model.access.csv',
            'views/payslip_portal_template.xml',
            'views/report_payslip_templates.xml',
            'views/hr_payroll_report.xml',
        ],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
