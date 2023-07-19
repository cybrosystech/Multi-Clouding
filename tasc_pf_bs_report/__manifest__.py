{
    'name': 'Tasc profit&Loss BalanceSheet Report',
    'summary': """""",

    'description': """""",

    'author': "",
    'website': "",
    'category': 'Accounting',
    'version': '14.0.1.0.0',
    'depends': ['account_reports', 'cash_flow_statement_report',
                'tasc_trail_balance_report'],

    'data':
        [
            'views/assets.xml',
            'views/tasc_pf_bs_report_view.xml',
            'views/tasc_balance_sheet_report_view.xml',
        ],
    'qweb': [
    ],
}
