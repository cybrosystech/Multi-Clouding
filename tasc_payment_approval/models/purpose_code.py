from odoo import api, models, fields
from odoo.osv import expression


class PurposeCode(models.Model):
    _name = 'purpose.code'
    _description = 'Purpose Code'
    _rec_name = 'code'

    code = fields.Char(string="Code", required=True)
    description = fields.Text(string="Description", required=True)
    company_ids = fields.Many2many('res.company', 'purpose_code_company_rel')

    @api.model
    def _name_search(self, name, domain=None, operator='ilike', limit=None,
                     order=None):
        domain = domain or []
        if operator != 'ilike' or (name or '').strip():
            name_domain = ['|', ('code', 'ilike', name),
                           ('description', 'ilike', name)]
            domain = expression.AND([name_domain, domain])
        return self._search(domain, limit=limit, order=order)

    @api.depends('code')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"{rec.code} - {rec.description}"
