from odoo import models, fields


class HrContract(models.Model):
    _inherit = 'hr.contract'

    housing = fields.Monetary('Housing', required=True, tracking=True)
    mobile_allowance = fields.Monetary('Mobile Allowance', required=True,
                                       tracking=True)
    miscellaneous_1 = fields.Monetary('Miscellaneous 1', required=True,
                                      tracking=True)
    miscellaneous_2 = fields.Monetary('Miscellaneous 2', required=True,
                                      tracking=True)
    transport = fields.Monetary('Transport', required=True,
                                tracking=True)
    other = fields.Monetary('Other', required=True,
                            tracking=True)
    nursery = fields.Monetary('Nursery', required=True, tracking=True)
    entertainment = fields.Monetary('Entertainment', required=True,
                                    tracking=True)
    overtime = fields.Monetary('Overtime', required=True, tracking=True)
    per_diem = fields.Monetary('Per Diem', required=True, tracking=True)
    zain_invoice = fields.Monetary('Zain Invoice', required=True, tracking=True)
