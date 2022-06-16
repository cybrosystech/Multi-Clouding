from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    # is_posted = fields.Boolean(default=False)
