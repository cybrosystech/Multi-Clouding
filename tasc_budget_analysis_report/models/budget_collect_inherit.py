from odoo import models, fields


class BudgetCollectCopy(models.Model):
    _name = 'budget.collect.copy'

    remaining_amount_copy = fields.Float()
    demand_amount_copy = fields.Float()
    difference_amount_copy = fields.Float()
    budget_id = fields.Many2one(comodel_name="crossovered.budget",
                                string="Budget", required=False, )
    budget_line_id = fields.Many2one(comodel_name="crossovered.budget.lines",
                                string="Budget", required=False, )
    move_id = fields.Many2one(comodel_name="account.move", string="",
                              required=False, )
