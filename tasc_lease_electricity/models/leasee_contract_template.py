from odoo import fields, models


class LeaseContractTemplate(models.Model):
    """Inherited lease template to add electricity expense account"""
    _inherit = 'leasee.contract.template'

    electricity_expense_account_id = fields.Many2one('account.account',
                                               string="Electricity Expenses")
    electricity_due_account_id = fields.Many2one('account.account',
                                                 string="Electricity Due From")
    electricity_liability_account_id = fields.Many2one('account.account',
                                                   string="Electricity Liability Account")

