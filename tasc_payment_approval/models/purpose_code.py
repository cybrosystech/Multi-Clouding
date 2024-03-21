from odoo import api,models,fields,_
from odoo.exceptions import ValidationError


class PurposeCode(models.Model):
    _name = 'purpose.code'
    _description = 'Purpose Code'
    _rec_name = 'code'

    code = fields.Char(string="Code",required=True)
    description = fields.Text(string="Description",required=True)
    company_ids = fields.Many2many('res.company','purpose_code_company_rel')

    def name_get(self):
        result = []
        for rec in self:
            result.append((rec.id, '%s - %s' % (rec.code, rec.description)))
        return result