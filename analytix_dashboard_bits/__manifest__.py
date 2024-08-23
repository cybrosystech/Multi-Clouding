# -*- coding: utf-8 -*-
#################################################################################
# Author      : Terabits Technolab (<www.terabits.xyz>)
# Copyright(c): 2024
# All Rights Reserved.
#
# This module is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#################################################################################
{
    "name": "AnalytiX Dashboard",
    "version": "17.0.6.2.3",
    'author': "Terabits Technolab",
    'summary': """  
        Unlock the true potential of your data with AnalytiX Dashboard, a cutting-edge Odoo dashboard module designed to revolutionize the way you visualize and analyze information. Elevate your decision-making process with intuitive, interactive, and insightful dashboards that empower you to confidently navigate your business landscape.| 
        AnalytiX Dashboard | Dashboard manager | All in One Dashboard | Simplified dashboard manager |  Sales Dashboard manager | CRM dashboard manager | 
        HR dashboard manager | Inventory dashboard manager | Product dashboard manager | webiste dashboard manager | support dashboard | events dashboard manager.
        AnalytiX Dashboard | Dashboard manager | All in One Dashboard | Simplified dashboard manager |  purchase dashboard manager | CRM dashboard manager | 
        HR dashboard manager | Inventory dashboard manager | Product dashboard manager | webiste dashboard manager | support dashboard | events dashboard manager |
        Simplify Access Management | Manage - Hide Menu, Submenu, Fields, Action, Reports, Views, | Restrict/Read-Only User, Apps,  Fields, Export, Archive, Actions, Views, Reports, Delete items | Manage Access rights from one place | Hide Tabs and buttons | Multi Company supported.
        Delight POS theme | Advance POS Theme | point of sale theme | Theme POS | Odoo POS theme | Point of sale split bill | Point of sale split order | POS split bill | POS split invoices |
        You can create a Sales Dashboard, Inventory Dashboard, Finance Dashboard, or Others dynamically with this module. |
        KPI dashboards. Dashboard designer. KPI charts. Odoo dashboards. Analytic dashboards. Create dashboards. Customize dashboards. Chart Graphs. Key performance indicators. Dynamic KPIs. Smart goals.|
        Bar chart| Line chart | Statistics Chart | Trend Chart| Dashboard Ninja Advance | Dashboard Ninja with ai
        Get smart visual data with interactive and engaging dashboards for your Odoo ERP.|Odoo Dashboard, CRM Dashboard, Inventory Dashboard, Sales Dashboard, Account Dashboard, Invoice Dashboard, Revamp Dashboard,
        Best Dashboard, Odoo Best Dashboard, Odoo Apps Dashboard, Best Ninja Dashboard, Analytic Dashboard, Pre-Configured Dashboard, Create Dashboard, Beautiful Dashboard, Customized Robust Dashboard, Predefined Dashboard, 
        Multiple Dashboards, Advance Dashboard, Beautiful Powerful Dashboards, Chart Graphs Table View, All In One Dynamic Dashboard, Accounting Stock Dashboard, Pie Chart Dashboard, Modern Dashboard, Dashboard Studio, 
        Dashboard Builder, Dashboard Designer, Odoo Studio,Open hrms | crm | sales | inventrory | point of sales | modern odoo dashboard | data analysis | dynamic odoo dashboard | Create Own Analytic Odoo dashboards |
        account dashboard | employee dashboard | employee leave analysis | activity dashbord | ceo dashboard | manager dashboard | HR dashboard | marketing
    """,
    'description': """
        AnalytiX Dashboard | Dashboard manager | All in One Dashboard | Simplified dashboard manager |  Sales Dashboard manager | CRM dashboard manager | 
        HR dashboard manager | Inventory dashboard manager | Product dashboard manager | webiste dashboard manager | support dashboard | events dashboard manager |
        Simplify Access Management | Manage - Hide Menu, Submenu, Fields, Action, Reports, Views, | Restrict/Read-Only User, Apps,  Fields, Export, Archive, Actions, Views, Reports, Delete items | Manage Access rights from one place | Hide Tabs and buttons | Multi Company supported.
        Delight POS theme | Advance POS Theme | point of sale theme | Theme POS | Odoo POS theme | Point of sale split bill | Point of sale split order | POS split bill | POS split invoices |
        You can create a Sales Dashboard, Inventory Dashboard, Finance Dashboard, or Others dynamically with this module. |
        KPI dashboards. Dashboard designer. KPI charts. Odoo dashboards. Analytic dashboards. Create dashboards. Customize dashboards. Chart Graphs. Key performance indicators. Dynamic KPIs. Smart goals.|
        Bar chart| Line chart | Statistics Chart | Trend Chart| Dashboard Ninja Advance | Dashboard Ninja with ai
        Get smart visual data with interactive and engaging dashboards for your Odoo ERP.|Odoo Dashboard, CRM Dashboard, Inventory Dashboard, Sales Dashboard, Account Dashboard, Invoice Dashboard, Revamp Dashboard,
        Best Dashboard, Odoo Best Dashboard, Odoo Apps Dashboard, Best Ninja Dashboard, Analytic Dashboard, Pre-Configured Dashboard, Create Dashboard, Beautiful Dashboard, Customized Robust Dashboard, Predefined Dashboard, 
        Multiple Dashboards, Advance Dashboard, Beautiful Powerful Dashboards, Chart Graphs Table View, All In One Dynamic Dashboard, Accounting Stock Dashboard, Pie Chart Dashboard, Modern Dashboard, Dashboard Studio, 
        Dashboard Builder, Dashboard Designer, Odoo Studio.
    """,
    "sequence": 7,
    "license": "OPL-1",
    'category': 'Services',
    # 'external_dependencies': {
    #     'python': ['sqlalchemy']
    # },
    "website": "https://www.terabits.xyz",
    "depends": ["base", "web", "bus", "advanced_web_domain_widget"],
    "data": [
        "data/data_dashboard_themes.xml",
        "data/action.xml",
        "data/res_groups.xml", 
        "security/ir.model.access.csv",
        "templates_data/grid_templates.xml",
        "views/dashboard_actions_bits.xml",
        "views/view_dashboard_bits.xml",
        "views/view_dashboard_item_bits.xml",
        "views/view_dashboard_themes.xml",
        "views/view_dashboard_filter_bits.xml",
        "wizard/import_dashboard.xml",
        "wizard/import_dashboard_item.xml",
    ],
    "assets": {
        "web.assets_backend": [ 
            "/analytix_dashboard_bits/static/lib/echarts.min.js",
            "/analytix_dashboard_bits/static/lib/echarts.js",
            "/analytix_dashboard_bits/static/lib/gridstack-all.js",
            "/analytix_dashboard_bits/static/src/preview_widget/chart_preview_bits.js",
            "/analytix_dashboard_bits/static/lib/css/gridstack.min.css",
            "/analytix_dashboard_bits/static/lib/fontawesome/css/font-awesome.css",
            "/analytix_dashboard_bits/static/lib/fontawesome/fonts/*",
            "/analytix_dashboard_bits/static/lib/mdi-light/mdi-light.css",
            "/analytix_dashboard_bits/static/src/xml/dashboard_controller.xml",
            "/analytix_dashboard_bits/static/src/preview_widget/preview_styles.scss",
            "/analytix_dashboard_bits/static/src/scss/dashboard_bits.scss",
            "/analytix_dashboard_bits/static/src/js/dashboards_view_bits.js",
            "/analytix_dashboard_bits/static/src/js/dashboard_bits.js",
            "/analytix_dashboard_bits/static/src/media_widget/IconSelectorBits.js",
            "/analytix_dashboard_bits/static/src/media_widget/MidIconSelectorBits.js",
            "/analytix_dashboard_bits/static/lib/bootstrap-iconpicker.min.js",
            "/analytix_dashboard_bits/static/lib/mid-iconpicker.min.js",
            "/analytix_dashboard_bits/static/lib/css/iconpicker.css",
            "/analytix_dashboard_bits/static/lib/html2canvas.min.js",
            "/analytix_dashboard_bits/static/lib/jspdf.umd.min.js",
            "/analytix_dashboard_bits/static/src/add_to_board/add_to_board.js",
            "/analytix_dashboard_bits/static/src/widget/custom_dropdown_dynamic.js",
            "/analytix_dashboard_bits/static/src/field_widget/qry_group_select.js",
            "/analytix_dashboard_bits/static/src/field_widget/qry_measure_select.js",
            "/analytix_dashboard_bits/static/src/media_widget/IconSelectorBits.xml", 
            "/analytix_dashboard_bits/static/src/preview_widget/chart_preview_bits.xml",
            "/analytix_dashboard_bits/static/src/xml/dashboards_view_bits.xml", 
            "/analytix_dashboard_bits/static/src/xml/dashboard_grid.xml",
            "/analytix_dashboard_bits/static/src/xml/kpi_items_bits.xml",
            "/analytix_dashboard_bits/static/src/xml/statistics_items_bits.xml",
            "/analytix_dashboard_bits/static/src/xml/listview_items_bits.xml",
            "/analytix_dashboard_bits/static/src/xml/country_map_view_bits.xml",
            "/analytix_dashboard_bits/static/src/xml/no_data_bits.xml",
            "/analytix_dashboard_bits/static/src/xml/dialog_templates.xml",
            "/analytix_dashboard_bits/static/src/xml/custom_dropdown_dynamic.xml",
            "/analytix_dashboard_bits/static/src/add_to_board/add_to_board.xml",
            "/analytix_dashboard_bits/static/src/field_widget/qry_axis_select.xml",
            'web/static/src/legacy/js/core/*',
            'web/static/src/legacy/xml/dialog.xml',
            '/analytix_dashboard_bits/static/src/xml/embade_iframe.xml'
        ],
    },
     "price": "139",
    "currency": "USD",
    'installable': True,
    'application': True,
    'auto_install': False,
    'uninstall_hook': 'uninstall_hook',
    "live_test_url": "https://www.terabits.xyz/request_demo?source=index&version=17&app=analytix_dashboard_bits",
    "images": ["static/description/banner.gif"],
}
