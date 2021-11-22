# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class InOutBudgets(models.Model):
    _name = 'budget.in.out.check'
    _rec_name = 'name'
    _description = ''

    name = fields.Char(string="Name", required=False, )
    type = fields.Selection(string="Type", selection=[('in_budget', 'In Budget'), ('out_budget', 'Out Budget'), ],
                            required=True, )
    budget_line_ids = fields.One2many(comodel_name="budget.in.out.lines", inverse_name="budget_id", string="",
                                      required=False, )
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)


    @api.constrains('budget_line_ids')
    def check_lines(self):
        for rec in self:
            count_map = {}
            latest_to = 0
            for line in rec.budget_line_ids:
                count = count_map.get(line.approval_seq, 0)
                # if latest_to != 0 and line.from_amount < latest_to:
                #     raise ValidationError(
                #         _('From amount is lower than the latest to amount - line %s') % line.name)
                if count != 0:
                    raise ValidationError(
                        _('Cannot add the same sequence more than once, asequence of  %s is repeated') % line.name)
                count_map[line.approval_seq] = 1
                latest_to = line.to_amount
    @api.model
    def create(self, vals):
        check = self.env['budget.in.out.check'].sudo().search([('type', '=', vals['type']),('company_id', '=', vals['company_id'])])
        if check:
            raise ValidationError(_('This Type is already created'))
        return super(InOutBudgets, self).create(vals)

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

    @api.onchange('approval_seq')
    def approval_seq_check(self):
        for rec in self:
            if rec.name and rec.approval_seq <= 0:
                rec.approval_seq = False
                raise ValidationError(_('Approval Sequence cannot be lower than 1'))

    @api.constrains('from_amount', 'to_amount')
    def get_from_to_amount(self):
        for rec in self:
            if rec.from_amount < 0:
                raise ValidationError(_('From amount is lower than 0'))
            # if rec.from_amount > rec.to_amount:
            #     raise ValidationError(_('From amount is lower than To amount in Budget Lines'))


class InOutBudgetsSales(models.Model):
    _name = 'budget.in.out.check.sales'
    _rec_name = 'name'
    _description = ''

    name = fields.Char(string="Name", required=False, )
    type = fields.Selection(string="Type", selection=[('in_budget', 'In Budget'), ('out_budget', 'Out Budget'), ],
                            required=True, )
    budget_line_ids = fields.One2many(comodel_name="budget.in.out.lines.sales", inverse_name="budget_id", string="",
                                      required=False, )
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)

    @api.constrains('budget_line_ids')
    def check_lines(self):
        for rec in self:
            count_map = {}
            latest_to = 0
            for line in rec.budget_line_ids:
                count = count_map.get(line.approval_seq, 0)
                # if latest_to != 0 and line.from_amount < latest_to:
                #     raise ValidationError(
                #         _('From amount is lower than the latest to amount - line %s') % line.name)
                if count != 0:
                    raise ValidationError(
                        _('Cannot add the same sequence more than once, asequence of  %s is repeated') % line.name)
                count_map[line.approval_seq] = 1
                latest_to = line.to_amount

    @api.model
    def create(self, vals):
        check = self.env['budget.in.out.check.sales'].sudo().search([('type', '=', vals['type']),('company_id', '=', vals['company_id'])])
        if check:
            raise ValidationError(_('This Type is already created'))
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

    @api.onchange('approval_seq')
    def approval_seq_check(self):
        for rec in self:
            if rec.name and rec.approval_seq <= 0:
                rec.approval_seq = False
                raise ValidationError(_('Approval Sequence cannot be lower than 1'))

    @api.constrains('from_amount', 'to_amount')
    def get_from_to_amount(self):
        for rec in self:
            if rec.from_amount < 0:
                raise ValidationError(_('From amount is lower than 0'))
            # if rec.from_amount > rec.to_amount:
            #     raise ValidationError(_('From amount is lower than To amount in Budget Lines'))



class InOutBudgetsInvoices(models.Model):
    _name = 'budget.in.out.check.invoice'
    _rec_name = 'name'
    _description = ''

    name = fields.Char(string="Name", required=False, )
    type = fields.Selection(string="Type", selection=[('in_budget', 'In Budget'), ('out_budget', 'Out Budget'), ],
                            required=True, )
    budget_line_ids = fields.One2many(comodel_name="budget.in.out.lines.invoice", inverse_name="budget_id", string="",
                                      required=False, )
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)


    @api.constrains('budget_line_ids')
    def check_lines(self):
        for rec in self:
            count_map = {}
            latest_to = 0
            for line in rec.budget_line_ids:
                count = count_map.get(line.approval_seq, 0)
                # if latest_to != 0 and line.from_amount < latest_to:
                #     raise ValidationError(
                #         _('From amount is lower than the latest to amount - line %s') % line.name)
                if count != 0:
                    raise ValidationError(
                        _('Cannot add the same sequence more than once, asequence of  %s is repeated') % line.name)
                count_map[line.approval_seq] = 1
                latest_to = line.to_amount

    @api.model
    def create(self, vals):
        if vals.get('type'):
            check = self.env['budget.in.out.check.invoice'].sudo().search([('type', '=', vals['type']),('company_id', '=', vals['company_id'])])
            if check:
                raise ValidationError(_('This Type is already created'))
        return super(InOutBudgetsInvoices, self).create(vals)


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

    company_id = fields.Many2one('res.company', 'Company', related='budget_id.company_id',store=True)

    @api.onchange('approval_seq')
    def approval_seq_check(self):
        for rec in self:
            if rec.name and rec.approval_seq <= 0:
                rec.approval_seq = False
                raise ValidationError(_('Approval Sequence cannot be lower than 1'))

    @api.constrains('from_amount', 'to_amount')
    def get_from_to_amount(self):
        for rec in self:
            if rec.from_amount < 0:
                raise ValidationError(_('From amount is lower than 0'))
            # if rec.from_amount > rec.to_amount:
            #     raise ValidationError(_('From amount is lower than To amount in Budget Lines'))