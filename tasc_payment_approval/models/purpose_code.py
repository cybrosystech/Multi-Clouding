from odoo import api, models, fields


class PurposeCode(models.Model):
    _name = 'purpose.code'
    _description = 'Purpose Code'
    _rec_name = 'code'

    code = fields.Char(string="Code", required=True)
    description = fields.Text(string="Description", required=True)
    company_ids = fields.Many2many('res.company', 'purpose_code_company_rel')

    @api.depends('code')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"{rec.code} - {rec.description}"
