from odoo import models, fields


class HrContract(models.Model):
    _inherit = 'hr.contract'

    housing = fields.Monetary('Housing', tracking=True)
    mobile_allowance = fields.Monetary('Mobile Allowance', required=True,
                                       tracking=True)
    # miscellaneous_1 = fields.Monetary('Miscellaneous 1', required=True,
    #                                   tracking=True)
    # miscellaneous_2 = fields.Monetary('Miscellaneous 2', required=True,
    #                                   tracking=True)
    transport = fields.Monetary('Transport',
                                tracking=True)
    other = fields.Monetary('Other',
                            tracking=True)
    nursery = fields.Monetary('Nursery', tracking=True)
    entertainment = fields.Monetary('Entertainment',
                                    tracking=True)
    overtime = fields.Monetary('Overtime', tracking=True)
    per_diem = fields.Monetary('Per Diem', tracking=True)
    zain_invoice = fields.Monetary('Zain Invoice', tracking=True)
