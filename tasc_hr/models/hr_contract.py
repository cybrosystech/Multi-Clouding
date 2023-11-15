from odoo import models, fields


class HrContract(models.Model):
    _inherit = 'hr.contract'

    housing = fields.Monetary('Housing', required=True, tracking=True)
    mobile_allowance = fields.Monetary('Mobile Allowance', required=True, tracking=True)
    miscellaneous_1 = fields.Monetary('Miscellaneous 1', required=True, tracking=True)
    miscellaneous_2 = fields.Monetary('Miscellaneous 2', required=True, tracking=True)
