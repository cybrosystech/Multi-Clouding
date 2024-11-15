{
    'name': 'TASC User Activity Report',
    'summary': """ The module is used for printing user activity report. """,
    'description': """The module is used for printing user activity report which
     includes total invoice created, total bills created, total assets 
     created,etc of all users""",
    'author': 'Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'website': 'https://www.cybrosys.com',
    'category': 'Accounting/Accounting',
    'version': '17.0.1.0.0',
    'depends': ['account','sale_management','purchase'],
    'data':
        [
            'security/ir.model.access.csv',
            'wizard/user_activity_report_wizard_views.xml'
        ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
