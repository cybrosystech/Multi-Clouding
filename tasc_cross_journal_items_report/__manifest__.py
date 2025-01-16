{
    'name': 'TASC Cross Journal Items Report',
    'summary': """ Module for TASC Cross Journal Items Report""",
    'description': """Module for TASC Cross Journal Items Report""",
    'author': "Cybrosys Technologies",
    'website': "",
    'category': 'Accounting',
    'version': '17.0.1.0.0',
    'depends': ['analytic_account_colocation_type'],
    'data':
        [
            'security/ir.model.access.csv',
            'wizard/tasc_cross_journal_items.xml',
        ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
