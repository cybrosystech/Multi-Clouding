{
    'name': 'TASC Blanket Order Approval',
    'summary': """The module is used for adding approvals for blanket orders""",
    'description': """The module is used for adding approvals for blanket orders""",
    'author': " Cybrosys Technologies",
    'website': "",
    'category': 'Purchase',
    'version': '17.0.1.0.0',
    'depends': ['purchase','purchase_requisition','analytic_account_types'],
    'data':
        [
            'data/mail_template.xml',
            'security/ir.model.access.csv',
            'views/purchase_requisition_approval_check_view.xml',
            'views/purchase_requisition_views.xml',

        ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
