# -*- coding: utf-8 -*-
{
    'name': "Analytic Account Types",
    'summary': """
            Customizations related to analytic accounts.
        """,

    'description': """
    """,
    'author': "",
    'website': "",
    'category': 'Accounting',
    'version': '0.1',
    'depends': ['sale', 'purchase', 'account', 'account_accountant',
                'analytic', 'account_reports', 'account_budget',
                'account_asset'],
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/sale_order_line.xml',
        'views/purchase_order_line.xml',
        'views/account_move_line.xml',
        'views/analytic_item.xml',
        'views/assets.xml',
        'views/budget.xml',
        'views/account_analytic_account.xml',
        'views/account_asset.xml',
        'views/in_out_budget.xml',
        'views/in_out_budget_sales.xml',
        'views/in_out_budget_invoice.xml',
        'views/approve_mail_template.xml',
        'views/account_account.xml',
        'views/account_group.xml',
        'views/account_asset_views.xml',
    ],
    "license": 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
