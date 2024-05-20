{
    "name": "TASC Towers Holding branding",
    "version": "17.0.1.0.0",
    "author": ("TTH"),
    "maintainers": ["ifujis"],
    "website": "https://github.com/tasctowers",
    "summary": "Modifies Odoo branding",
    "depends": ["web",
                "auth_oauth"
                ],
    "data": [
        "views/favicon.xml",
        'views/web_login.xml',
        'views/mail_layout.xml',
        'data/mail_data.xml'
    ],
    'assets': {
        'web.assets_backend': [
            'tth_branding/static/src/js/window_title.js',
            'tth_branding/static/src/js/user_menu.js',
        ],
    },

    'web.assets_web': [
        ('include', 'web.assets_backend'),
        'tth_branding/static/src/js/window_title.js',
        'static/src/xml/menu.xml',
    ],

    "license": 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
