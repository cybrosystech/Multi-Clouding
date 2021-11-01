# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class InOutBudgets(models.Model):
    _name = 'budget.in.out.check'
    _rec_name = 'name'
    _description = ''

    name = fields.Char(string="Name", required=False, )
    type = fields.Selection(string="Type", selection=[('in_budget', 'In Budget'), ('out_budget', 'Out Budget'), ], required=True, )
    budget_line_ids = fields.One2many(comodel_name="budget.in.out.lines", inverse_name="budget_id", string="", required=False, )


class BudgetInOutLines(models.Model):
    _name = 'budget.in.out.lines'
    _rec_name = 'name'
    _description = ''

    budget_id = fields.Many2one(comodel_name="budget.in.out.check", string="", required=False, )
    name = fields.Char(string="Name", required=True, )
    from_amount = fields.Float(string="From", required=False, )
    to_amount = fields.Float(string="To", required=False, )
    approval_seq = fields.Integer(string="Approval Sequence", required=False, )
    user_ids = fields.Many2many(comodel_name="res.users", string="User", required=True, )


class InOutBudgetsSales(models.Model):
    _name = 'budget.in.out.check.sales'
    _rec_name = 'name'
    _description = ''

    name = fields.Char(string="Name", required=False, )
    type = fields.Selection(string="Type", selection=[('in_budget', 'In Budget'), ('out_budget', 'Out Budget'), ], required=True, )
    budget_line_ids = fields.One2many(comodel_name="budget.in.out.lines.sales", inverse_name="budget_id", string="", required=False, )

    @api.model
    def create(self, vals):
        check = self.env['budget.in.out.check.sales'].sudo().search([('type', '=', vals['type'])])
        if check:
            raise ValidationError(_('This Type is already created'))
        else:
            return super(InOutBudgetsSales, self).create(vals)

class BudgetInOutLinesSales(models.Model):
    _name = 'budget.in.out.lines.sales'
    _rec_name = 'name'
    _description = ''

    budget_id = fields.Many2one(comodel_name="budget.in.out.check.sales", string="", required=False, )
    name = fields.Char(string="Name", required=True, )
    from_amount = fields.Float(string="From", required=False, )
    to_amount = fields.Float(string="To", required=False, )
    approval_seq = fields.Integer(string="Approval Sequence", required=False, )
    user_ids = fields.Many2many(comodel_name="res.users", string="User", required=True, )

    @api.model
    def create(self, vals):
        check_seq = self.env['budget.in.out.lines.sales'].sudo().search([('budget_id', '=', vals['budget_id']), ('approval_seq', '=', vals['approval_seq'])])
        if check_seq:
            raise ValidationError(_('Approval Sequence is already found'))
        if vals['from_amount'] > vals['to_amount']:
            raise ValidationError(_('From amount is lower than To amount'))
        return super(BudgetInOutLinesSales, self).create(vals)

class InOutBudgetsInvoices(models.Model):
    _name = 'budget.in.out.check.invoice'
    _rec_name = 'name'
    _description = ''

    name = fields.Char(string="Name", required=False, )
    type = fields.Selection(string="Type", selection=[('in_budget', 'In Budget'), ('out_budget', 'Out Budget'), ], required=True, )
    budget_line_ids = fields.One2many(comodel_name="budget.in.out.lines.invoice", inverse_name="budget_id", string="", required=False, )


class BudgetInOutLinesInvoices(models.Model):
    _name = 'budget.in.out.lines.invoice'
    _rec_name = 'name'
    _description = ''

    budget_id = fields.Many2one(comodel_name="budget.in.out.check.invoice", string="", required=False, )
    name = fields.Char(string="Name", required=True, )
    from_amount = fields.Float(string="From", required=False, )
    to_amount = fields.Float(string="To", required=False, )
    approval_seq = fields.Integer(string="Approval Sequence", required=False, )
    user_ids = fields.Many2many(comodel_name="res.users", string="User", required=True, )




