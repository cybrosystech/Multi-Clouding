from odoo import api, fields, models


class HrDepartment(models.Model):
    _inherit = 'hr.department'

    sub_department_id = fields.Many2one('hr.sub.department',
                                        string="Sub Department")
