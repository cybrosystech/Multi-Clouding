from odoo import models, fields


class ResCompanyStamp(models.Model):
    _inherit = 'res.company'

    company_stamp = fields.Binary(string='Stamp')
