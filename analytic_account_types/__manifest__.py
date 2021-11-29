# -*- coding: utf-8 -*-
{
    'name': "Analytic Account Types",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "Oakland",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Accounting',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','sale','purchase','account','account_accountant','analytic','account_reports','account_budget','account_asset','account_analytic_parent'],

    # always loaded
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
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
