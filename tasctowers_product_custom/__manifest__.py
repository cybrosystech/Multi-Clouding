# Copyright 2013 Savoir-faire Linux
{
    "name": "Product Custom",
    "summary": "Adding company field to product category and product",
    "description": "1.Adding company field to product category and product"
                   "2. Adding multi company record rule to product, product "
                   "category.",
    'sequence': 1,
    'category': 'sale',
    'version': '1.0',
    "depends": [
        'base',
        "sale",
        'stock'
    ],
    'data': [
        'security/security.xml',
        'views/product.xml'
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}

