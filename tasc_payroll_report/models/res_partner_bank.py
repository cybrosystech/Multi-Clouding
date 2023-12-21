from odoo import models, fields, api
from odoo.exceptions import UserError


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    bank_iban = fields.Char(string="IBAN")
    branch = fields.Char(string="Branch")

    @api.constrains('bank_bic')
    def onsave_bank_bic(self):
        if self.bank_bic and (len(self.bank_bic) not in [8, 11]):
            raise UserError("Invalid SWIFT/BIC !!!")
