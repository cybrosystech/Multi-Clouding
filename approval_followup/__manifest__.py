{
    'name': 'Approval Followup',
    'summary': """The module is used for purchase approval follow up.""",
    'description': """The module is used to send remainder email for purchase
     order if the order is pending approval greater than 2 days.""",
    'author': "Cybrosys Technologies",
    'website': "",
    'category': 'Accounting',
    'version': '17.0.1.0.0',
    'depends': ['purchase','analytic_account_types'],
    'data':
        [
            'data/purchase_data.xml',
            'data/mail_template.xml',
        ],
    "license": 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
