{
    'name': 'TASC Stock Landed Costs',
    'summary': """Module for customization on landed cost""",
    'description': """ Enable landed cost creation option for inventory user""",
    'author': "",
    'website': "",
    'category': 'Accounting',
    'version': '1.0',
    'depends': ['stock','stock_account','stock_landed_costs'],
    'data':
        [
            'security/ir.model.access.csv',
            'security/tasc_stock_landed_cost_security.xml',
            'views/stock_landed_cost_views.xml',
        ],
    "license": 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,

}
