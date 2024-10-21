{
    'name': 'General Ledger Report Custom',
    'summary': """ Custom General Ledger Report""",

    'description': """  Custom General Ledger Report
                        1. Adding of project_site and cost center to general 
                        ledger report.
                    """,
    'author': "",
    'website': "",
    'category': 'Accounting',
    'version': '17.0.1.0.0',
    'depends': ['account_reports'],
    'data':
        [
            'reports/general_ledger.xml',
            'reports/partner_ledger.xml'
        ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
