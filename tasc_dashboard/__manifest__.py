# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "TASC dashboards",
    "version": "17.0.1.0.0",
    "category": "Hidden",
    "summary": "Dashboard access rights customization",
    "description": "Dashboard access rights customization",
    "depends": ["base","purchase","spreadsheet_dashboard",
                "account_consolidation","account","budget_approval_group",
                "analytix_dashboard_bits","izi_data","izi_dashboard","website"],
    "installable": True,
    "auto_install": False,
    "application": False,
    "data": [
        'security/security.xml',
        "security/ir.model.access.csv",
        "views/dashboard_menu.xml"
    ],
}
