from odoo import models, fields


class CrossOveredBudgetLines(models.Model):
    _inherit = 'crossovered.budget.lines'

    practical_demo = fields.Monetary()
