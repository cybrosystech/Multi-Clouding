from odoo import models, fields


class AccountMoveLineInherit(models.Model):
    _inherit = 'account.move.line'

    profitability_managed_bool = fields.Boolean('Profitability Managed')
    profitability_owned_bool = fields.Boolean('Profitability Owned')
