{
    'name': 'Journal Active Checks',
    'summary': """
                This module is used to check the journal entries are active or not using scheduled action
    """,

    'description': """""",

    'author': "",
    'website': "",
    'category': 'Accounting',
    'version': '14.0.1.0.0',
    'depends': ['account'],

    'data':
        [
            'data/journals_active_check_cron.xml',
            'views/account_move_active_view.xml'
        ]
}
