from odoo import models, fields, api
from odoo.exceptions import UserError


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    bank_iban = fields.Char(string="IBAN")
    branch = fields.Char(string="Branch")

    @api.constrains('bank_iban')
    def onsave_bank_iban(self):
        print("cvbn")
        if self.bank_iban and (len(self.bank_iban) != 34):
            print("hjk")
            raise UserError("Invalid IBAN !!!")

    @api.constrains('bank_bic')
    def onsave_bank_bic(self):
        print("poiug")
        if self.bank_bic and (len(self.bank_bic) not in [8, 11]):
            print("asdfg")
            raise UserError("Invalid SWIFT/BIC !!!")
