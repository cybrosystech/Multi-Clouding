# -*- coding: utf-8 -*-
{
    'name': "Lease Management",
    'summary': """Lease Management""",
    'author': "Mahmoud Naguib",
    "version": "14.0.1.0.0",
    "category": "Accounting",
    "depends": ["account", "account_asset", "analytic_account_types"],
    "data": [
        'security/ir.model.access.csv',
        'data/data.xml',
        'wizard/account_asset_sell.xml',
        'wizard/leassee_contract_reassessment.xml',
        'wizard/leassee_period_extend.xml',
        'views/res_config_settings.xml',
        'views/leasee_contract.xml',
        'views/leasee_contract_template.xml',
        'views/account_payment.xml',
        'views/leasor_contract.xml',
        'views/account_move.xml',
        'reports/general_ledger_posting.xml',
        'reports/ap_recon.xml',
        'reports/lease_liability_schedule.xml',
        'reports/rou_asset_schedule_wizard.xml',

    ],
    "license": 'AGPL-3',
    'installable': True,
}
