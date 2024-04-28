from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    child_below_18 = fields.Integer(string="Children below 18")
    child_below_4 = fields.Integer(string="Children below 4")
    spouse_working = fields.Selection(string="Spouse Working",
                                      selection=[('working', 'Working'),
                                                 ('not_working', 'Not Working'),
                                                 ], default='not_working')

    date_of_birth_ids = fields.One2many('date.of.birth.line', 'employee_id',
                                        copy=False)
    social_security = fields.Char(string="Social Security Number")
    sub_department_ids = fields.Many2many('hr.sub.department',compute='compute_sub_department_ids')
    sub_department_id = fields.Many2one('hr.sub.department',
                                        string="Sub Department",domain="[('id','in',sub_department_ids)]"
                                        )

    @api.depends('department_id')
    def compute_sub_department_ids(self):
        for rec in self:
            if rec.department_id:
                sub_departments = self.env['hr.sub.department'].sudo().search([])
                sub_deps = sub_departments.sudo().filtered(
                    lambda x: rec.department_id.id in x.department_ids.ids)
                rec.sub_department_ids = sub_deps.ids
            else:
                rec.sub_department_ids = False

    @api.onchange('department_id')
    def get_sub_department(self):
        if self.department_id:
            sub_department = self.env['hr.sub.department'].search([])
            deps = sub_department.filtered(
                lambda x: self.department_id.id in x.department_ids.ids)
            domain = [('id', 'in', deps.ids),
                      ('company_id', '=', self.env.company.id)]
        else:
            domain = [('company_id', '=', self.env.company.id)]
        return {'domain': {'sub_department_id': domain}}

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


class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    child_below_18 = fields.Integer(string="Children below 18")
    child_below_4 = fields.Integer(string="Children below 4")
    spouse_working = fields.Selection(string="Spouse Working",
                                      selection=[('working', 'Working'),
                                                 ('not_working', 'Not Working'),
                                                 ], default='not_working')

    date_of_birth_ids = fields.One2many('date.of.birth.line', 'employee_id',
                                        copy=False)
    social_security = fields.Char(string="Social Security Number")
    sub_department_id = fields.Many2one('hr.sub.department',
                                        string="Sub Department",

                                        )


class DateOfBirthLine(models.Model):
    _name = 'date.of.birth.line'
    _description = 'Children - Date of Birth'

    dob = fields.Date(string="Date of Birth")
    employee_id = fields.Many2one('hr.employee')
