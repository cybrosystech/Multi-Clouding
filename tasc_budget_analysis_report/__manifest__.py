{
    'name': 'Tasc Budget Analysis Report',
    'summary': """""",

    'description': """""",

    'author': "",
    'website': "",
    'category': 'Accounting',
    'version': '17.0.1.0.0',
    'depends': ['account_reports', 'cash_flow_statement_report'],

    'data':
        [
            'security/ir.model.access.csv',
            'views/budget_analysis_report.xml',
            'views/account_report_views.xml',
            'views/account_report_actions.xml',
            'views/menuitems.xml',
            # 'views/account_move_budget_conf_button_view.xml',
        ],
    'assets': {
        'web.assets_backend': [
            'tasc_budget_analysis_report/static/src/components/**/*',
        ],
    },
    'qweb': [
    ],
}
