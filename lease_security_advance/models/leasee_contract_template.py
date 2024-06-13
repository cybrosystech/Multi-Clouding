from odoo import models, fields


class LeaseContractTemplate(models.Model):
    _inherit = 'leasee.contract.template'

    security_prepaid_account = fields.Many2one('account.account',
                                               string="Security Expenses")
    security_deferred_account = fields.Many2one('account.account',
                                                string="Security Deferred Account")
