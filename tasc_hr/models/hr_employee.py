from odoo import models,fields


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    child_below_18 = fields.Integer(string="Children below 18")
    child_below_4 = fields.Integer(string="Children below 4")




