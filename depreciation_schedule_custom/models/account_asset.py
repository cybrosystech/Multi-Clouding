from odoo import models, fields


class AccountAsset(models.Model):
    _inherit = 'account.asset'

    additional_info = fields.Char(string="Additional Info",
                                  help="Additional Info")
    additional_info2 = fields.Char(string="Additional Info2",
                                  help="Additional Info2")
