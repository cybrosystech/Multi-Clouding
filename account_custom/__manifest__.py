{
    'name': 'Accounting Customizations',
    'summary': """This module contains accounting customizations""",
    'description': """
        1. Add project site to vendor bills
        2. Adding account code as number
        3. Adding Tasc reference
        4. Adding some account fields to products and updating product multi 
        company record rule.
    """,
    'author': "",
    'website': "",
    'category': 'Accounting',
    'version': '17.0.1.0.0',
    'depends': ['base','account', 'lease_management'],
    'data':
        [
            "data/security.xml",
            'views/product_view.xml',
            'views/account_move.xml',
            'views/account_move_line_views.xml',
            'views/product_category_views.xml',
        ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
