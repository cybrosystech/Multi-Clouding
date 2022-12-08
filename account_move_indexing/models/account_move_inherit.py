from odoo import models, fields


class AccountMoveIndexing(models.Model):
    _inherit = 'account.move'

    # ==== Reverse feature fields ====
    reversed_entry_id = fields.Many2one('account.move', string="Reversal of",
                                        readonly=True, copy=False,
                                        check_company=True, index=True)