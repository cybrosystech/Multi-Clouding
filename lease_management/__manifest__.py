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
        'reports/general_ledger_posting.xml',

    ],
    "license": 'AGPL-3',
    'installable': True,
}
