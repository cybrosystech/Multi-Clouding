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

    @api.model
    def _default_product_uom_id(self):
        return self.env['uom.uom'].search([], limit=1, order='id')

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
                                 domain="[('can_be_expensed', '=', True),('product_expense_type', 'not in', ['overtime','per_diem']), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
                                 ondelete='restrict')
    unit_amount = fields.Float("Unit Price",
                               compute='_compute_from_product_id_company_id',
                               store=True, required=True, copy=True,
                               states={
                                   'waiting_approval': [('readonly', False)],
                                   'draft': [('readonly', False)],
                                   'reported': [('readonly', False)],
                                   'refused': [('readonly', False)]},
                               digits='Product Price')
    quantity = fields.Float(required=True, readonly=True,
                            states={'waiting_approval': [('readonly', False)],
                                    'draft': [('readonly', False)],
                                    'reported': [('readonly', False)],
                                    'refused': [('readonly', False)]},
                            digits='Product Unit of Measure', default=1)

    project_site_id = fields.Many2one('account.analytic.account', domain=[
        ('analytic_account_type', '=', 'project_site')])
    analytic_account_id = fields.Many2one('account.analytic.account',
                                          domain=[('analytic_account_type', '=',
                                                   'cost_center')],
                                          string='Analytic Account',
                                          check_company=True)
    is_manager_approved = fields.Boolean(string="Is Manager Approved",
                                         copy=False)
    state = fields.Selection(compute='_compute_state', string='Status',
                             selection_add=[('waiting_approval',
                                             'Awaiting Manager Approval')],
                             copy=False, index=True, readonly=True, store=True,
                             default='waiting_approval',
                             help="Status of the expense.")

    description = fields.Text('Notes...', readonly=True,
                              states={'waiting_approval': [('readonly', False)],
                                      'draft': [('readonly', False)],
                                      'reported': [('readonly', False)],
                                      'refused': [('readonly', False)]})
    date = fields.Date(readonly=True,
                       states={'waiting_approval': [('readonly', False)],
                               'draft': [('readonly', False)],
                               'reported': [('readonly', False)],
                               'refused': [('readonly', False)]},
                       default=fields.Date.context_today, string="Expense Date")
    product_uom_id = fields.Many2one('uom.uom', string='Unit of Measure',
                                     compute='_compute_from_product_id_company_id',
                                     store=True, copy=True,
                                     states={'waiting_approval': [
                                         ('readonly', False)],
                                         'draft': [('readonly', False)],
                                         'refused': [('readonly', False)]},
                                     default=_default_product_uom_id,
                                     domain="[('category_id', '=', product_uom_category_id)]")

    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 readonly=True,
                                 states={
                                     'waiting_approval': [
                                         ('readonly', False)],
                                     'draft': [('readonly', False)],
                                     'refused': [('readonly', False)]},
                                 default=lambda self: self.env.company)

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
        employees_ids = self.mapped('employee_id')
        for emp in employees_ids:
            expense_ids = self.env['hr.expense'].search(
                [('employee_id', '=', emp.id), ('id', 'in', self.ids),
                 ('state', '=', 'draft'), ('sheet_id', '=', False)])
            total_amount = sum(expense_ids.mapped('total_amount'))
            full_month_name = fields.Datetime.now().strftime("%B")
            print("full_month_name", full_month_name)
            expense_report_summary = emp.name + " - " + full_month_name + "(" + str(
                total_amount) + ") "
            if expense_ids:
                print("ddddddd")
                journal = self.env['ir.config_parameter'].sudo().get_param(
                    'dev_hr_expense_portal.expense_journal_id')
                print("journal", journal)
                expense_ids._create_sheet_all_employees_from_expenses(
                    expense_report_summary, journal)

    def _create_sheet_all_employees_from_expenses(self, expense_report_summary,
                                                  journal):
        print("journalllllllllll", journal, type(journal))
        if any(expense.state != 'draft' or expense.sheet_id for expense in
               self):
            raise UserError(_("You cannot report twice the same line!"))
        if len(self.mapped('employee_id')) != 1:
            raise UserError(
                _("You cannot report expenses for different employees in the same report."))
        if any(not expense.product_id for expense in self):
            raise UserError(_("You can not create report without product."))

        todo = self.filtered(
            lambda x: x.payment_mode == 'own_account') or self.filtered(
            lambda x: x.payment_mode == 'company_account')
        sheet = self.env['hr.expense.sheet'].create({
            'company_id': self.company_id.id,
            'employee_id': self[0].employee_id.id,
            'name': expense_report_summary,
            'expense_line_ids': [(6, 0, todo.ids)],
            'journal_id': journal,
        })
        return sheet


class HrExpenseSheet(models.Model):
    _inherit = 'hr.expense.sheet'

    def action_create_journal_entry(self):
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
        employees = sheets_approved.mapped('employee_id')

        for emp in employees:
            expense_line_ids = sheets_approved.mapped('expense_line_ids') \
                .filtered(lambda r: not float_is_zero(r.total_amount,
                                                      precision_rounding=(
                                                              r.currency_id or self.env.company.currency_id).rounding) and r.employee_id.id == emp.id)
            journal = self.env['account.journal'].search(
                [('code', '=', 'MISC'), ('type', '=', 'general')])
            move_values = {
                'journal_id': journal.id,
                'date': fields.Datetime.now().date(),
                'ref': 'Expense Report for Month - ' + str(
                    fields.Datetime.now().month) + ' - ' + str(
                    fields.Datetime.now().year),
                'name': '/',
            }
            move = self.env['account.move'].with_context(
                default_journal_id=move_values['journal_id']).create(
                move_values)
            for exp in expense_line_ids:
                move_line_values_by_expense = exp._get_account_move_line_values()
                move_line_values = move_line_values_by_expense.get(exp.id)
                # link move lines to move, and move to expense sheet
                move.write(
                    {'line_ids': [(0, 0, line) for line in move_line_values]})
                exp.sheet_id.write({'account_move_id': move.id})
                exp.sheet_id.write({'state': 'done'})
            emp = emp.name + '-' + str(fields.Datetime.now().date())
            move.ref = emp
            move._post()

            for sheet in self.filtered(lambda s: not s.accounting_date):
                sheet.accounting_date = sheet.account_move_id.date
            to_post = self.filtered(lambda
                                        sheet: sheet.payment_mode == 'own_account' and sheet.expense_line_ids)
            to_post.write({'state': 'post'})
            (self - to_post).write({'state': 'done'})
            self.activity_update()

    def action_report_in_next_payslip(self):
        records = self.filtered(lambda l: l.refund_in_payslip == False)
        print("records", records)
        self.write({'refund_in_payslip': True})
        if records:
            for record in records:
                record.message_post(
                    body=_(
                        "Your expense (%s) will be added to your next payslip.") % (
                             record.name),
                    partner_ids=record.employee_id.user_id.partner_id.ids,
                    subtype_id=self.env.ref('mail.mt_note').id,
                    email_layout_xmlid='mail.mail_notification_light')
                print("payslip", record.payslip_id)
        else:
            raise UserError(_("The expense reports are already reported in "
                              "payslip."))
