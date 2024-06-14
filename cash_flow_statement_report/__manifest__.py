{
    'name': 'Cash Flow Statement',
    'summary': """""",

    'description': """""",

    'author': "",
    'website': "",
    'category': 'Accounting',
    'version': '17.0.1.0.0',
    'depends': ['account_reports'],

    'data':
        [
            # 'views/assets.xml',
            'views/tasc_cash_flow_report.xml',
            'views/account_report_actions.xml',
            # 'views/cash_flow_statement_views.xml',
            # 'views/cash_flow_search_template_view.xml',
            # 'views/cash_flow_comparison_filter_template.xml',
            'views/menuitems.xml',
        ],
    # 'web.assets_backend': [
    #     "/cash_flow_statement_report/static/src/js/cash_flow_report.js",
    #     "/cash_flow_statement_report/static/src/js/action_manager.js",
    #     "/cash_flow_statement_report/static/src/scss/cash_flow_report.scss",
    #     ],
    'qweb': [
        'static/src/xml/cash_flow_report.xml',
    ],
}
