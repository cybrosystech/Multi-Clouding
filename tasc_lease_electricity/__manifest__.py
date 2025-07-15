{
    'name': 'Lease Electricity',
    'summary': """Module used for Lease Electricity""",
    'description': """Module used for  Lease Electricity""",
    'author': "",
    'website': "",
    'category': 'Accounting',
    'version': '17.0.1.0.0',
    'depends': ['base', 'lease_management'],
    'data':
        [
            'security/ir.model.access.csv',
            'views/lease_electricity_views.xml',
            'views/leasee_contract_template_views.xml',
            'views/leasee_contract_views.xml',
        ],
  "license": 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
