# -*- coding: utf-8 -*-
{
    'name': 'Import',
    'version': '17.0.1.0.0',
    'category': 'Extra Tools',
    'summary': """
                Customization on export
        """,
    'description': """
         1.Hiding of 'I want to update data' option on export dialog for the users..
        """,
    'author': 'Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': 'https://www.cybrosys.com',
    'depends': ['base','web'],
    'data': [
        'security/security.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'tasc_export/static/src/views/**/*'
        ],},
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
