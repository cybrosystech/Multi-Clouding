from odoo import models, fields, api


class Account(models.Model):
    _inherit = 'account.account'

    code_num = fields.Integer(string="Code in Number",
                              compute='compute_code_num', store=True)
    account_category = fields.Char(string="Account Category",
                                   help="Used for classification of accounts "
                                        "for reporting purpose.")
    report_category = fields.Char(string="Report Category",
                                   help="Used for classification of accounts "
                                        "for reporting purpose.")

    @api.depends('code')
    def compute_code_num(self):
        for rec in self:
            if rec.code:
                rec.code_num = int(rec.code)
            else:
                rec.code_num = False
