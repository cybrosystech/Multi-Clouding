{
    "name": "OAuth Authorization Code Flow",
    "version": "14.0.0.0.3",
    "license": "AGPL-3",
    "author": ("TTH"),
    "maintainers": ["ifujis"],
    "website": "https://github.com/tasctowers",
    "summary": "Adds OAuth Authorization Code Flow authentication to Odoo",
    "external_dependencies": {"python": ["python-jose"]},
    "depends": ["auth_oauth","hr"],
    "data": ["views/auth_oauth_provider.xml", "views/res_users_views.xml"],
}
