{
    'name': 'Consolidation Eliminate Configuration',
    'summary': """""",

    'description': """""",

    'author': "",
    'website': "",
    'category': 'Accounting',
    'version': '17.0.1.0.0',
    'depends': ['account', 'consolidation_name_inherit'],

    'data':
        [
            'security/ir.model.access.csv',
            'views/consolidation_period_view_inherit.xml',
            'views/elimination_journal_conf_view.xml',
        ],
    "license": 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
