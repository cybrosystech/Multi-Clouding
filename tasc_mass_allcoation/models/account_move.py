from odoo import fields,models

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    mass_allocation_id = fields.Many2one('mass.allocation',string="Mass Allocation",
                                         help="The mass allocation that selected for the journal entry creation",
                                         copy=False)
