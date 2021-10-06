# -*- coding: utf-8 -*-

from odoo import models, fields, api


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
    user_id = fields.Many2one(comodel_name="res.users", string="User", required=True, )


