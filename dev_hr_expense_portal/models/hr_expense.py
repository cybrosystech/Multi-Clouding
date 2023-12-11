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

from odoo.tools import float_is_zero


class hr_expense(models.Model):
    _name = 'hr.expense'
    _inherit = ['hr.expense', 'portal.mixin']

    name = fields.Char('Description',
                       compute='_compute_from_product_id_company_id',
                       store=True, required=True, copy=True,
                       states={'waiting_approval': [('readonly', False)],
                               'draft': [('readonly', False)],
                               'reported': [('readonly', False)],
                               'refused': [('readonly', False)]})
    product_id = fields.Many2one('product.product', string='Product',
                                 readonly=True, tracking=True,
                                 states={
                                     'waiting_approval': [('readonly', False)],
                                     'draft': [('readonly', False)],
                                     'reported': [('readonly', False)],
                                     'refused': [('readonly', False)]},
                                 domain="[('can_be_expensed', '=', True), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
                                 ondelete='restrict')

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


class HrExpenseSheet(models.Model):
    _inherit = 'hr.expense.sheet'

    def action_create_journal_entry(self):
        print("action_create_journal_entry", self)
        samples = self.mapped('expense_line_ids.sample')
        if samples.count(True):
            if samples.count(False):
                raise UserError(
                    _("You can't mix sample expenses and regular ones"))
            self.write({'state': 'post'})
            return

        if any(sheet.state != 'approve' for sheet in self):
            raise UserError(
                _("You can only generate accounting entry for approved expense(s)."))

        if any(not sheet.journal_id for sheet in self):
            raise UserError(
                _("Expenses must have an expense journal specified to generate accounting entries."))

        sheets_approved = self.env['hr.expense.sheet'].search(
            [('id', 'in', self.ids), ('state', '=', 'approve')])

        expense_line_ids = sheets_approved.mapped('expense_line_ids') \
            .filtered(lambda r: not float_is_zero(r.total_amount,
                                                  precision_rounding=(
                                                          r.currency_id or self.env.company.currency_id).rounding))
        journal = self.env['account.journal'].search(
            [('short_code', '=', 'MISC'), ('type', '=', 'general')])
        move_values = {
            'journal_id': journal.id,
            'date': fields.Datetime.now().date(),
            'ref': 'Expense Report for Month - ' + fields.Datetime.now().month + '-' + fields.Datetime.now().year,
            'name': '/',
        }
        move = self.env['account.move'].with_context(
            default_journal_id=move_values['journal_id']).create(move_values)
        print("move", move)

        for exp in expense_line_ids:
            # move_group_by_sheet = self._get_account_move_by_sheet()
            move_line_values_by_expense = exp._get_account_move_line_values()
            print("move_line_values_by_expense", move_line_values_by_expense)
            move_line_values = move_line_values_by_expense.get(exp.id)

            # link move lines to move, and move to expense sheet
            move.write(
                {'line_ids': [(0, 0, line) for line in move_line_values]})
            exp.sheet_id.write({'account_move_id': move.id})
            exp.sheet_id.write({'state': 'done'})
        res = move._post()

        for sheet in self.filtered(lambda s: not s.accounting_date):
            sheet.accounting_date = sheet.account_move_id.date
        to_post = self.filtered(lambda
                                    sheet: sheet.payment_mode == 'own_account' and sheet.expense_line_ids)
        to_post.write({'state': 'post'})
        (self - to_post).write({'state': 'done'})
        self.activity_update()
        return res
