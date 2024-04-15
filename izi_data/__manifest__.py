# -*- coding: utf-8 -*-
# Copyright 2022 IZI PT Solusi Usaha Mudah
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).
# noinspection PyUnresolvedReferences,SpellCheckingInspection
{
    "name": """Analytic Data Query""",
    "summary": """IZI Module to Handle Data Query. Dependency For IZI Dashboard by IZI""",
    "category": "Reporting",
    "version": "17.0.1.0.0",
    "development_status": "Alpha",  # Options: Alpha|Beta|Production/Stable|Mature
    "auto_install": False,
    "installable": True,
    "application": False,
    "author": "IZI PT Solusi Usaha Mudah",
    "support": "admin@iziapp.id",
    "website": "https://www.iziapp.id",
    "license": "OPL-1",
    "price": 0.00,
    "currency": "USD",
    "depends": [
        # odoo addons
        'base',
        # third party addons

        # developed addons
    ],
    "data": [],
    "demo": [],
    "qweb": [],
    "external_dependencies": {"python": [
        "requests",
        "xlsxwriter",
        "sqlparse",
    ], "bin": []},
  
}
