{
    'name': 'Account Dashboard Inherit',
    'summary': """""",

    'description': """This module adds extra menu tags in the accounting 
     dashboard tiles. Based on the click it will redirect to journals with
     specified filters. Showed the count of the links shown in the 
     dashboard.""",

    'author': "",
    'website': "",
    'category': 'Accounting',
    'version': '14.0.1.1.0',
    'depends': ['account', 'account_analytic_parent', 'approve_status'],

    'data':
        [
            'views/account_dashboard_inherit.xml',
            'views/account_move_filter_inherit.xml',
            'data/vendor_bills_approval.xml'
        ]
}
