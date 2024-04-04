from odoo import models, fields


class ResUsers(models.Model):
    _inherit = "res.users"

    oauth_enforced = fields.Boolean(string='Enforce OAuth')
