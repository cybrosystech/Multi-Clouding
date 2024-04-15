# -*- coding: utf-8 -*-
# Copyright 2022 IZI PT Solusi Usaha Mudah
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).
# noinspection PyUnresolvedReferences,SpellCheckingInspection
{
    "name": """Analytic Dashboard Template: Sale""",
    "summary": """Free sales analysis template for IZI Dashboard""",
    "category": "Reporting",
    "version": "17.0.1.0.0",
    "development_status": "Alpha",  # Options: Alpha|Beta|Production/Stable|Mature
    "auto_install": False,
    "installable": True,
    "application": False,
    "author": "IZI PT Solusi Usaha Mudah",
    "support": "admin@iziapp.id",
    # "website": "https://iziapp.id",
    "license": "OPL-1",
    "images": [],

    "price": 0.00,
    "currency": "USD",

    "depends": [
        # odoo addons
        'base',
        'sale',
        # third party addons

        # developed addons
        'izi_data',
        'izi_dashboard',
    ],
    "data": [],
    "demo": [],
    "qweb": [],
    "external_dependencies": {"python": [], "bin": []},
}
