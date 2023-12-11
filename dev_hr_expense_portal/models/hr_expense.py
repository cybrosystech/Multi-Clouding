# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2015 DevIntelle Consulting Service Pvt.Ltd (<http://www.devintellecs.com>).
#
#    For Module Support : devintelle@gmail.com  or Skype : devintelle
#
##############################################################################

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, date
from dateutil.relativedelta import relativedelta


class hr_expense(models.Model):
    _name = 'hr.expense'
    _inherit = ['hr.expense', 'portal.mixin']

    project_site_id = fields.Many2one('account.analytic.account', domain=[
        ('analytic_account_type', '=', 'project_site')])
    analytic_account_id = fields.Many2one('account.analytic.account',
                                          domain=[('analytic_account_type', '=',
                                                   'cost_center')],
                                          string='Analytic Account',
                                          check_company=True)
    is_manager_approved = fields.Boolean(string="Is Manager Approved",
                                         copy=False)
    state = fields.Selection([
        ('waiting_approval', 'Awaiting Manager Approval'),
        ('draft', 'To Submit'),
        ('reported', 'Submitted'),
        ('approved', 'Approved'),
        ('done', 'Paid'),
        ('refused', 'Refused')], compute='_compute_state', string='Status',
        copy=False, index=True, readonly=True, store=True,
        default='waiting_approval', help="Status of the expense.")

    @api.depends('sheet_id', 'sheet_id.account_move_id', 'sheet_id.state')
    def _compute_state(self):
        for expense in self:
            if not expense.sheet_id:
                expense.state = 'waiting_approval'
            elif expense.sheet_id.state == 'draft':
                expense.state = "draft"
            elif expense.sheet_id.state == "cancel":
                expense.state = "refused"
            elif expense.sheet_id.state == "approve" or expense.sheet_id.state == "post":
                expense.state = "approved"
            elif not expense.sheet_id.account_move_id:
                expense.state = "reported"
            else:
                expense.state = "done"

    def _compute_access_url(self):
        super(hr_expense, self)._compute_access_url()
        for expense in self:
            expense.access_url = '/my/hr_expense/%s' % (expense.id)

    def action_submit_expenses_all_employees(self):
        print("self", self)
        employees_ids = self.mapped('employee_id')
        print("employees", employees_ids)
        for emp in employees_ids:
            expense_ids = self.env['hr.expense'].search(
                [('employee_id', '=', emp.id), ('id', 'in', self.ids),
                 ('state', '=', 'draft'), ('sheet_id', '=', False)])
            print("expense_id", expense_ids)
            if expense_ids:
                expense_ids._create_sheet_from_expenses()
