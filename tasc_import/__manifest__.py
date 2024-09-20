# -*- coding: utf-8 -*-
{
    'name': 'Import',
    'version': '17.0.1.0.0',
    'category': 'Extra Tools',
    'summary': """
        Import Analytic distribution with analytic account names instead of id.
        """,
    'description': """
         Import Analytic distribution with analytic account names instead of id..
        """,
    'author': 'Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': 'https://www.cybrosys.com',
    'images': ['static/description/banner.jpg'],
    'depends': ['base_import'],
    'data': [
    ],
    'assets': {
        'web.assets_backend': [
            'tasc_import/static/src/**/*.js',
        ],},
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
