{
    'name': 'Depreciation Schedule Custom Report',
    'summary': """Depreciation Schedule Custom Report""",

    'description': """Depreciation Schedule Custom Report""",

    'author': "",
    'website': "",
    'category': 'Accounting',
    'version': '17.0.1.0.0',
    'depends': ['cash_flow_statement_report', 'tasc_account_assets','assets_sub_models_config'],

    'data':
        [
            'views/account_asset_views.xml',
            'report/account_assets_custom_report_view.xml',
            'report/account_asset.xml',
        ],
    # 'assets': {
    #     'web.assets_backend': [
    #         'depreciation_schedule_custom/static/src/components/**/*',
    #     ],
    # },
    'installable': True,
    'auto_install': False,
    'application': False,
}
