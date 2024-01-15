from odoo import models, fields


class HrSubDepartment(models.Model):
    _name = 'hr.sub.department'

    name = fields.Char(string="Sub Department")
    department_ids = fields.Many2many('hr.department','department_sub_department_rel',column1='department_id',column2='sub_department_id', string="Departments")
