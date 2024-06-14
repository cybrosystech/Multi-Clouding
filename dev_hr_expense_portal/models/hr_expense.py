# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2015 DevIntelle Consulting Service Pvt.Ltd (<http://www.devintellecs.com>).
#
#    For Module Support : devintelle@gmail.com  or Skype : devintelle
#
##############################################################################

from odoo import models, fields, api, _, Command
from odoo.exceptions import UserError
from odoo.tools import float_round
from odoo.tools.misc import format_date
from odoo.tools.misc import clean_context


class hr_expense(models.Model):
    _name = 'hr.expense'
    _inherit = ['hr.expense', 'portal.mixin']

    @api.model
    def _default_product_uom_id(self):
        return self.env['uom.uom'].search([], limit=1, order='id')

    price_unit = fields.Monetary(
        string="Unit Price",
        currency_field='company_currency_id',
        compute='_compute_price_unit', precompute=True, store=True, required=True, readonly=False,
        copy=True,
    )
    product_id = fields.Many2one(
        comodel_name='product.product',
        string="Category",
        tracking=True,
        check_company=True,
        domain="[('can_be_expensed', '=', True),('product_expense_type', 'not in', ['overtime','per_diem']), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        ondelete='restrict',
    )

    is_manager_approved = fields.Boolean(string="Is Manager Approved",
                                         copy=False)

    state = fields.Selection(
        selection_add=[
            ('waiting_approval',
             'Awaiting Manager Approval')
        ],
        string="Status",
        compute='_compute_state', store=True, readonly=True,
        index=True,
        copy=False,
        default='waiting_approval',
    )


    @api.depends('sheet_id', 'sheet_id.account_move_ids', 'sheet_id.state')
    def _compute_state(self):
        for expense in self:
            if not expense.sheet_id:
                expense.state = 'waiting_approval'
            elif expense.sheet_id.state == 'draft':
                expense.state = 'reported'
            elif expense.sheet_id.state == 'cancel':
                expense.state = 'refused'
            elif expense.sheet_id.state in {'approve', 'post'}:
                expense.state = 'approved'
            elif not expense.sheet_id.account_move_ids:
                expense.state = 'submitted'
            else:
                expense.state = 'done'

    def _compute_access_url(self):
        super(hr_expense, self)._compute_access_url()
        for expense in self:
            expense.access_url = '/my/hr_expense/%s' % (expense.id)

    def action_approve(self):
        for rec in self:
            if rec.state == 'waiting_approval':
                rec.write({'state':'draft'})

    def _get_default_expense_sheet_values(self):
        # If there is an expense with total_amount == 0, it means that expense has not been processed by OCR yet
        expenses_with_amount = self.filtered(lambda expense: not (
                expense.currency_id.is_zero(expense.total_amount_currency)
                or expense.company_currency_id.is_zero(expense.total_amount)
                or not float_round(expense.quantity,
                                   precision_rounding=expense.product_uom_id.rounding)
        ))

        if any(expense.state not in ['draft',
                                     'waiting_approval'] or expense.sheet_id for
               expense in expenses_with_amount):
            raise UserError(_("You cannot report twice the same line!"))
        if not expenses_with_amount:
            raise UserError(_("You cannot report the expenses without amount!"))
        if len(expenses_with_amount.mapped('employee_id')) != 1:
            raise UserError(
                _("You cannot report expenses for different employees in the same report."))
        if any(not expense.product_id for expense in expenses_with_amount):
            raise UserError(_("You can not create report without category."))
        if len(self.company_id) != 1:
            raise UserError(
                _("You cannot report expenses for different companies in the same report."))

        # Check if two reports should be created
        own_expenses = expenses_with_amount.filtered(
            lambda x: x.payment_mode == 'own_account')
        company_expenses = expenses_with_amount - own_expenses
        create_two_reports = own_expenses and company_expenses

        sheets = (own_expenses, company_expenses) if create_two_reports else (
            expenses_with_amount,)
        values = []
        for todo in sheets:
            if len(todo) == 1:
                expense_name = todo.name
            else:
                dates = todo.mapped('date')
                min_date = format_date(self.env, min(dates))
                max_date = format_date(self.env, max(dates))
                expense_name = min_date if max_date == min_date else f'{min_date} - {max_date}'

            values.append({
                'company_id': self.company_id.id,
                'employee_id': self[0].employee_id.id,
                'name': expense_name,
                'expense_line_ids': [Command.set(todo.ids)],
                'state': 'draft',
            })
        return values

    def action_submit_expenses_all_employees(self):
        if self:
            employees_ids = self.mapped('employee_id')
        else:
            expenses = self.env['hr.expense'].search([
                ('state', '=', 'draft'),
                ('sheet_id', '=', False),
                ('employee_id', '=', self.env.user.employee_id.id),
                ('is_editable', '=', True),
            ])
            employees_ids = expenses.mapped('employee_id')

        for emp in employees_ids:
            if self:
                expenses = self.filtered(lambda
                                             expense: expense.state in ['draft',
                                                                        'approved'] and not expense.sheet_id and expense.is_editable and expense.employee_id.id == emp.id)
            else:
                expenses = self.env['hr.expense'].search([
                    '|', ('state', '=', 'draft'), ('state', '=', 'approved'),
                    ('sheet_id', '=', False),
                    ('employee_id', '=', self.env.user.employee_id.id),
                    ('is_editable', '=', True), ('employee_id', '=', emp.id),
                ])

            if expenses.filtered(lambda expense: not expense.is_editable):
                raise UserError(
                    _('You are not authorized to edit this expense.'))

            total_amount = sum(expenses.mapped('total_amount'))
            full_month_name = fields.Datetime.now().strftime("%B")
            expense_report_summary = emp.name + " - " + full_month_name + "(" + str(
                total_amount) + ") "

            expenses_with_amount = expenses.filtered(lambda expense: not (
                    expense.currency_id.is_zero(expense.total_amount_currency)
                    or expense.company_currency_id.is_zero(expense.total_amount)
                    or not float_round(expense.quantity,
                                       precision_rounding=expense.product_uom_id.rounding)
            ))

            if any(expense.state not in ['draft',
                                         'waiting_approval'] or expense.sheet_id
                   for expense in
                   expenses_with_amount):
                raise UserError(_("You cannot report twice the same line!"))
            if not expenses_with_amount:
                raise UserError(
                    _("You cannot report the expenses without amount!"))
            if len(expenses_with_amount.mapped('employee_id')) != 1:
                raise UserError(
                    _("You cannot report expenses for different employees in the same report."))
            if any(not expense.product_id for expense in expenses_with_amount):
                raise UserError(
                    _("You can not create report without category."))
            if len(expenses.company_id) != 1:
                raise UserError(
                    _("You cannot report expenses for different companies in the same report."))

            # Check if two reports should be created
            own_expenses = expenses_with_amount.filtered(
                lambda x: x.payment_mode == 'own_account')
            company_expenses = expenses_with_amount - own_expenses
            create_two_reports = own_expenses and company_expenses

            sheets = (
                own_expenses, company_expenses) if create_two_reports else (
                expenses_with_amount,)
            values = []
            for todo in sheets:
                values.append({
                    'company_id': expenses.company_id.id,
                    'employee_id': expenses[0].employee_id.id,
                    'name': expense_report_summary,
                    'expense_line_ids': [Command.set(todo.ids)],
                    'state': 'draft',
                })

            sheets = self.env['hr.expense.sheet'].create(values)

    def _create_sheet_all_employees_from_expenses(self, expense_report_summary,
                                                  journal):
        if any(expense.state != 'approved' or expense.sheet_id for expense in
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
        for exp in self:
            exp.sheet_id = sheet.id
        return sheet


class HrExpense(models.Model):
    _inherit = 'hr.expense'

    currency_id = fields.Many2one('res.currency', string='Currency',
                                  readonly=False,
                                  default=lambda
                                      self: self.env.company.currency_id)


class HrExpenseSheet(models.Model):
    _inherit = 'hr.expense.sheet'

    currency_id = fields.Many2one('res.currency', string='Currency',
                                  readonly=False,
                                  default=lambda
                                      self: self.env.company.currency_id)
    # move_id = fields.Many2one(
    #     string="Journal Entry",
    #     comodel_name='account.move', readonly=True,
    # )

    def action_create_journal_entry(self):
        employee_ids = self.mapped('employee_id')
        for emp in employee_ids:
            sheets = self.filtered(lambda x: x.employee_id.id == emp.id)
            sheets._check_can_create_move()
            for expense in sheets.expense_line_ids.filtered(
                    lambda expense: expense.sale_order_id and not expense.analytic_distribution):
                if not expense.sale_order_id.analytic_account_id:
                    expense.sale_order_id._create_analytic_account()
                expense.write({
                    'analytic_distribution': {
                        expense.sale_order_id.analytic_account_id.id: 100}
                })
            sheets = sheets.with_context(
                clean_context(self.env.context))  # remove default_*
            skip_context = {
                'skip_invoice_sync': True,
                'skip_invoice_line_sync': True,
                'skip_account_move_synchronization': True,
                'check_move_validity': False,
            }
            own_account_sheets = sheets.filtered(
                lambda sheet: sheet.payment_mode == 'own_account')
            company_account_sheets = sheets - own_account_sheets

            # for sheet in own_account_sheets:
            journal = own_account_sheets.mapped('journal_id')
            currency = own_account_sheets.mapped('currency_id')
            move_values = {
                'journal_id': journal[0].id if journal else False,
                'date': fields.Datetime.now().date(),
                'ref': 'Expense Report for Month - ' + str(
                    fields.Datetime.now().month) + ' - ' + str(
                    fields.Datetime.now().year),
                'name': '/',
                'move_type': 'in_invoice',
                'partner_id': emp.sudo().work_contact_id.id,
                'currency_id': currency.id,
                'line_ids': [Command.create(expense._prepare_move_lines_vals())
                             for expense in own_account_sheets.expense_line_ids],
                'attachment_ids': [
                    Command.create(attachment.copy_data(
                        {'res_model': 'account.move', 'res_id': False,
                         'raw': attachment.raw})[0])
                    for attachment in
                    own_account_sheets.expense_line_ids.message_main_attachment_id
                ],
            }
            move = self.env['account.move'].create(move_values)
            for sheet in sheets:
                sheet.account_move_ids =[move.id]


    def action_report_in_next_payslip(self):
        records = self.filtered(lambda l: l.refund_in_payslip == False)
        if records:
            records.write({'refund_in_payslip': True})
            for record in records:
                record.message_post(
                    body=_(
                        "Your expense (%s) will be added to your next payslip.") % (
                             record.name),
                    partner_ids=record.employee_id.user_id.partner_id.ids,
                    subtype_id=self.env.ref('mail.mt_note').id,
                    email_layout_xmlid='mail.mail_notification_light')
        else:
            raise UserError(_("The expense reports are already reported in "
                              "payslip."))
