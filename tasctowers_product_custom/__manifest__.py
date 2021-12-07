# Copyright 2013 Savoir-faire Linux
{
    "name": "product_custom",
    "summary": "product_custom",
    'sequence': 1,
    'category': 'sale',
    'version': '0.1',
    "depends": [
        'base',
        "sale",
        'stock'
    ],
    'data': [
        # "security/ir.model.access.csv",
        'security/security.xml',
        'views/product.xml'
    ],
    'installable': True,
}
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

