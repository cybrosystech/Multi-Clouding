from odoo import fields, models

class AccountAccount(models.Model):
    """To add new fields CF and MR"""
    _inherit = 'account.account'

    cf = fields.Char(string="CF", help="Cash Flow")
    mr = fields.Char(string="MR", help="Monthly Revenue")