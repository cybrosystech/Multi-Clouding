{
    'name': 'Journal Cron Configuration',
    'summary': """ """,
    'description': """""",
    'author': "",
    'website': "",
    'category': 'Accounting',
    'version': '17.0.1.0.0',
    'depends': ['account'],
    'data':
        [
            'security/ir.model.access.csv',
            'security/journal_entry_posting_security.xml',
            'data/journal_draft_cron.xml',
            'views/account_move_config_view.xml',
            'views/journal_entry_posting_view.xml',
        ]
}
