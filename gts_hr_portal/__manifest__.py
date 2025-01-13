# -*- coding: utf-8 -*-
{
    'name': 'Leave Request from portal/create user automatically',
    'description': 'HR Portal',
    'category': 'HR',
    'live_test_url': 'https://youtu.be/S7b5X6zSf0E',
    'summary': """Create employee user
        Odoo create employee user,Atomatic user created with employee,Create employee user version 15,Odoo version 15 employee user
        Odoo create user, odoo 15, Apply leave from portal, leave apply from portal, create user automatically, user create after employee creation
        employee user create, odoo leave apply, can see leave on portal, want to create user automatically, Odoo form view, Odoo tree view,Odoo enterprise, Odoo community 
        portal leave creation, leave request from portal, leave status on portal, apply leave from website, Odoo employee, Odoo leave management,leave request, leave application
        create leave from portal, employee leave , apply leave in odoo, leave status in odoo, create user, leave management in odoo 15,leave management  enterprise
        create employee module, leave approved, Odoo hr, portal user,  portal login, portal leave apploication, leave management for odoo user, leave status in odoo
        Odoo version 14, Odoo website, Odoo apps for leave , Portal leave application, employee leave, user create, how to create user with employee, create user for a employee
        Create user app, leave apply from website, website leave portal, website leave template, leave apply,
        portal leave apply,
        """,
    'category': 'HR',
    "version": "17.0.1.0.0",
    "author": "Geo Technosoft",
    "website": "http://www.geotechnosoft.com",
    "license": "OPL-1",
    'depends': ['base', 'mail', 'website', 'hr_holidays', 'hr', 'calendar',
                'resource', 'hr_attendance', 'hr_contract', 'hr_payroll',
                'tasc_hr'],
    'data': [
        'security/security.xml',
        'data/mail_template.xml',
        'security/ir.model.access.csv',
        'views/hr_payslip_views.xml',
        'views/hr_portal_templates.xml',
        'views/payslip_portal_templates.xml',
        # 'views/assets.xml',
        'views/report_payslip_templates.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'gts_hr_portal/static/src/css/style.css',
        ],
        'web.assets_frontend': [
            'gts_hr_portal/static/src/js/attendance.js',
        ],
    },
    'images': ['static/description/banner.png'],
    'price': '59',
    'currency': 'USD',
    'license': 'OPL-1',
    'installable': True,
    'application': True,
}

