from odoo import models,fields

class AccountMove(models.Model):
    _inherit = 'account.move'

    lease_electricity_id = fields.Many2one('leasee.electricity',string="Electricity")