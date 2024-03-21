from odoo import api,fields, models


class DefaultPurposeCode(models.Model):
    _name = 'default.purpose.code'

    purpose_code_id = fields.Many2one('purpose.code', string='Purpose Code')
    company_id = fields.Many2one('res.company', string="Company")

    _sql_constraints = [
        ('company_unique', 'unique(company_id)', 'Company Already Exist.')
    ]

