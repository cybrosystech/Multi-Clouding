from odoo import api, fields, models


class HrDepartment(models.Model):
    _inherit = 'hr.department'

    sub_department_id = fields.Many2one('hr.department',
                                        string="Sub Department")

    @api.depends('name', 'parent_id.complete_name','sub_department_id.complete_name')
    def _compute_complete_name(self):
        for department in self:
            if department.parent_id:
                department.complete_name = '%s / %s' % (
                department.parent_id.complete_name, department.name)
            else:
                department.complete_name = department.name
            if department.sub_department_id:
                department.sub_department_id.parent_id = department.id
                department.sub_department_id.complete_name = '%s / %s' % (
                    department.complete_name, department.sub_department_id.name)
