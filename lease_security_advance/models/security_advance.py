from odoo import models, fields


class LeaseeSecurityAdvance(models.Model):
    _name = 'leasee.security.advance'

    leasee_reference = fields.Char()
    leasee_contract_id = fields.Many2one('leasee.contract')