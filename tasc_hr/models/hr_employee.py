from odoo import models, fields


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    child_below_18 = fields.Integer(string="Children below 18")
    child_below_4 = fields.Integer(string="Children below 4")
    spouse_working = fields.Selection(string="Spouse Working",
                                      selection=[('working', 'Working'),
                                                 ('not_working', 'Not Working'),
                                                 ], default='not_working')

#     date_of_birth_ids = fields.One2many('date.of.birth.line', 'employee_id',
#                                         copy=False)
#
#
# class DateOfBirthLine(models.Model):
#     _name = 'date.of.birth.line'
#     _description = 'Children - Date of Birth'
#
#     dob = fields.Date(string="Date of Birth")
#     employee_id = fields.Many2one('hr.employee')
