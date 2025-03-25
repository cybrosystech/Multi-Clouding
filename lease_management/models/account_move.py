# -*- coding: utf-8 -*-
""" init object """
from odoo import fields, models

import logging

LOGGER = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    leasee_contract_id = fields.Many2one(comodel_name="leasee.contract", index=True)
    leasee_installment_id = fields.Many2one(comodel_name="leasee.installment", string="", required=False, index=True)
    leasor_contract_id = fields.Many2one(comodel_name="leasor.contract", string="", required=False, )
    posting_date = fields.Date()
    is_installment_entry = fields.Boolean(default=False)

    def _post(self, soft=True):
        to_post = super(AccountMove, self)._post(soft)
        for move in to_post:
            move.posting_date = fields.Date.today()
        return to_post

    def _unlink_or_reverse(self):
        if not self:
            return
        to_reverse = self.env['account.move']
        to_unlink = self.env['account.move']
        lock_date = self.company_id._get_user_fiscal_lock_date()
        for move in self:
            if move.inalterable_hash or move.date <= lock_date:
                to_reverse += move
            else:
                to_unlink += move
        to_reverse._reverse_moves(cancel=True)
        to_unlink.filtered(lambda m: m.state in ('posted', 'cancel')).button_draft()
        to_unlink.filtered(lambda m: m.state == 'draft').sudo().unlink()


