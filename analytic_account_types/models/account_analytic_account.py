from odoo import fields, models

class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    is_inventory = fields.Boolean(string='Is Inventory', default=False)