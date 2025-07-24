# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AccountMoveLine(models.Model):
    """ This model represents account.move.line."""
    _inherit = 'account.move.line'

    cip_account_move_line_id = fields.Many2one('cip.account.move.line',
                                               ondelete='SET NULL')
