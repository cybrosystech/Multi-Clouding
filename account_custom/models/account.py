from odoo import models, fields, api


class Account(models.Model):
    _inherit = 'account.account'

    code_num = fields.Integer(string="Code in Number",
                              compute='compute_code_num', store=True)

    @api.depends('code')
    def compute_code_num(self):
        for rec in self:
            if rec.code:
                rec.code_num = int(rec.code)
            else:
                rec.code_num = False
