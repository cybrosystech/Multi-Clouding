{
    'name': 'Lease Management Inherit',
    'summary': """""",

    'description': """""",

    'author': "",
    'website': "",
    'category': 'Accounting',
    'version': '17.0.1.0.0',
    'depends': ['base', 'lease_management'],

    'data':
        [
            'security/lease_contract_security.xml',
            'views/lease_contract_inherit.xml',
            'views/lease_contract_template_inherit.xml',
            'views/leasor_contract_inherit.xml',
        ],
    "license": 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,

}
