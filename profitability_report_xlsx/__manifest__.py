{
    'name': 'Profitability Xlsx',
    'summary': """Module for Profitability managed and owned reports""",
    'description': """Module for Profitability managed and owned reports""",
    'author': "",
    'website': "",
    'category': 'Accounting',
    'version': '17.0.1.0.0',
    'depends': ['account_asset','analytic_account_types'],
    'data':
        [
            'security/ir.model.access.csv',
            'security/profitability_report_managed_data.xml',
            'security/profitability_report_owned_data.xml',
            'views/profitability_report_managed_view.xml',
            'views/profitability_report_owned_view.xml',
            'wizard/profitability_report_wizard.xml',
            'wizard/profitability_report_managed.xml',
        ],
    'assets': {
        'web.assets_backend': [
            'profitability_report_xlsx/static/src/js/action_manager.js',
        ],
    }
}
