from odoo import models, fields, api, _
from odoo.exceptions import UserError

class ResCompany(models.Model):
    _inherit = 'res.company'

    izi_lab_api_key = fields.Char('IZI Lab API Key')

