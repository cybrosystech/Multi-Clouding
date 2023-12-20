from odoo import models, fields


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    bank_iban = fields.Char(string="IBAN")
    branch = fields.Char(string="Branch")
