from odoo import models, fields


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    date_of_joining = fields.Date(string="Date of Joining")
    employment_type = fields.Selection(string="Employment Type",
                                       selection=[('FTE', 'FTE'),
                                                  ('Contract', 'Contract')])
