{
    'name': 'Lease Security Advance',
    'summary': """""",

    'description': """""",

    'author': "",
    'website': "",
    'category': 'Accounting',
    'version': '17.0.1.0.0',
    'depends': ['base', 'lease_management'],

    'data':
        [
            'security/ir.model.access.csv',
            'data/advance_data.xml',
            'views/lease_contract_inherit_security.xml',
            'views/lease_security_advance_view.xml',
        ],
  "license": 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
