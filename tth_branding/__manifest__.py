{
    "name": "TASC Towers Holding branding",
    "version": "14.0.0.0.1",
    "license": "AGPL-3",
    "author": ("TTH"),
    "maintainers": ["ifujis"],
    "website": "https://github.com/tasctowers",
    "summary": "Modifies Odoo branding",
    "depends": ["web",
                "auth_oauth"
    ],
    "data": ["views/favicon.xml",
            'views/custom_views.xml',
            'views/web_login.xml',
            'views/mail_layout.xml',
            'data/mail_data.xml'
    ],
    "qweb": ["static/src/xml/menu.xml"],
}
