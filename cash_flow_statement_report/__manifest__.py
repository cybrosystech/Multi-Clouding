{
    'name': 'Cash Flow Statement',
    'summary': """""",

    'description': """""",

    'author': "",
    'website': "",
    'category': 'Accounting',
    'version': '14.0.1.0.0',
    'depends': ['account_reports'],

    'data':
        [
            'views/assets.xml',
            'views/cash_flow_statement_views.xml',
            'views/cash_flow_search_template_view.xml',
            'views/cash_flow_comparison_filter_template.xml',
        ],
    'qweb': [
        'static/src/xml/cash_flow_report.xml',
    ],
}
