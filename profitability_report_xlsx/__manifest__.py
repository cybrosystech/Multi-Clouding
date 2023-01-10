{
    'name': 'Profitability Xlsx',
    'summary': """""",

    'description': """""",

    'author': "",
    'website': "",
    'category': 'Accounting',
    'version': '14.0.1.0.0',
    'depends': ['account_asset'],

    'data':
        [
            'security/ir.model.access.csv',
            'data/profitability_cron_jobs.xml',
            'views/assets.xml',
            'views/profitability_report_managed_view.xml',
            'views/account_move_line_inherit_view.xml',
            'wizard/profitability_report_wizard.xml',
            'wizard/profitability_report_managed.xml',
        ]
}
