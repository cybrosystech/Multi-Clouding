{
    'name': 'Assets Bulk Sale/Disposal',
    'summary': """This module helps to sell or dispose assets on selected
     assets""",
    'description': """This module helps to sell or dispose assets on selected
     assets""",
    'author': "",
    'website': "",
    'category': 'account_asset',
    'version': '17.0.1.0.0',
    'depends': ['account_asset','lease_management','lease_management_inherit','queue_job', 'queue_job_cron_jobrunner'],
    'data':
        [
            'security/ir.model.access.csv',
            'views/account_asset_sell_dispose.xml',
            'views/account_asset_bulk_wizard_view.xml',
            'views/account_asset_bulk_relation_view.xml',
            'wizard/asset_bulk_pause_depreciation_view.xml',
            'wizard/asset_bulk_sale_dispose_wizard_views.xml',
        ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
