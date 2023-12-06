from odoo import models, fields, api, _
from datetime import date

from odoo.exceptions import ValidationError


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    child_below_18 = fields.Integer(string="Children below 18",
                                    compute='compute_age')
    child_below_4 = fields.Integer(string="Children below 4",
                                   compute='compute_age'
                                   )
    spouse_working = fields.Selection(string="Spouse Working",
                                      selection=[('working', 'Working'),
                                                 ('not_working', 'Not Working'),
                                                 ], default='not_working')

    date_of_birth_ids = fields.One2many('date.of.birth.line', 'employee_id',
                                        copy=False)
    social_security = fields.Char(string="Social Security Number")

    @api.constrains('date_of_birth_ids')
    def on_save_date_of_birth_ids(self):
        if len(self.date_of_birth_ids.ids) > self.children:
            raise ValidationError(
                _("You couldn't have dob lines  more than the total number of"
                  " children!!"))
        elif len(self.date_of_birth_ids.ids) < self.children:
            raise ValidationError(
                _('You must need to add date birth for all children!!'))
        else:
            pass

    @api.depends('date_of_birth_ids')
    def compute_age(self):
        print("hjnkm,l")
        for rec in self:
            if rec.date_of_birth_ids:
                count_child_below_18 = 0
                count_child_below_4 = 0
                for dob in rec.date_of_birth_ids:
                    age = self.calculate_age(dob.dob)
                    print("age", age)
                    if age <= 4:
                        count_child_below_4 = count_child_below_4 + 1
                    if age <= 18:
                        count_child_below_18 = count_child_below_18 + 1
                rec.child_below_18 = count_child_below_18
                rec.child_below_4 = count_child_below_4
            else:
                rec.child_below_18 = 0
                rec.child_below_4 = 0

    def calculate_age(self, born):
        today = date.today()
        if born:
            return today.year - born.year - (
                    (today.month, today.day) < (born.month, born.day))
        else:
            return 0


class DateOfBirthLine(models.Model):
    _name = 'date.of.birth.line'
    _description = 'Children - Date of Birth'

    dob = fields.Date(string="Date of Birth")
    employee_id = fields.Many2one('hr.employee')
