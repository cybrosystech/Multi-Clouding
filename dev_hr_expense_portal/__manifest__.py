# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2015 DevIntelle Consulting Service Pvt.Ltd (<http://www.devintellecs.com>).
#
#    For Module Support : devintelle@gmail.com  or Skype : devintelle
#
##############################################################################

{
    'name': 'Employee Expense Portal, Expense Portal, Expense Request Portal',
    'version': '15.0.1.0',
    'sequence': 1,
    'category': 'Human Resources',
    'description':
        """
         The Odoo Portal Expenses App allows portal users to view and create expense records using the Odoo application. User can able to sort, filter, search and group expense using different criterias. This makes it easy for portal users to submit and track their expenses
         
         expense portal
         hr expense
         hr expense portal
         website hr expense
         create and view expense from portal
         Expense management
         Employee expenses
         Employee expenses portal
         Expense reimbursement
         Expense approval system
         Employee expense software
         Expense tracking portal
         Business travel expenses
         Expense approval 
         Employee Expense approval
         Employee Expense approval Portal
         
    """,
    'summary': 'Odoo app allows portal users to view and create expense, expense portal, hr expense, hr expense portal, website hr expense, create and view expense from portal, expense management, employee expenses, employee expenses portal, expense reimbursement, expense approval system, employee expense software, expense tracking portal, business travel expenses, expense approval, employee expense approval, employee expense approval portal',
    'depends': ['product','sale_expense','hr_payroll_expense', 'portal', 'analytic_account_types'],
    'data': [
        'data/hr_payroll_expense_data.xml',
        'security/ir.model.access.csv',
        'security/security.xml',
        # 'views/hr_employee_views.xml',
        'views/hr_expense_views.xml',
        'views/hr_expense_portal.xml',
        'views/product_template_views.xml',
        'views/expense_journal_views.xml',
    ],
    'demo': [],
    'test': [],
    'css': [],
    'qweb': [],
    'js': [],
    'images': ['images/main_screenshot.png'],
    'installable': True,
    'application': True,
    'auto_install': False,

    # author and support Details
    'author': 'DevIntelle Consulting Service Pvt.Ltd',
    'website': 'http://www.devintellecs.com',
    'maintainer': 'DevIntelle Consulting Service Pvt.Ltd',
    'support': 'devintelle@gmail.com',
    'price': 19.0,
    'currency': 'EUR',
    'license': 'LGPL-3',
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
