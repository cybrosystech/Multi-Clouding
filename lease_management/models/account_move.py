# -*- coding: utf-8 -*-
""" init object """
from odoo import api,fields, models

import logging

LOGGER = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    leasee_contract_id = fields.Many2one(comodel_name="leasee.contract", index=True)
    leasee_installment_id = fields.Many2one(comodel_name="leasee.installment", string="", required=False, index=True)
    leasor_contract_id = fields.Many2one(comodel_name="leasor.contract", string="", required=False, )
    posting_date = fields.Date()
    is_installment_entry = fields.Boolean(default=False)
    dimension = fields.Selection([('rent', 'Rent'), ('security', 'Security'), ('electricity', 'Electricity')],string="Lease Type")

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

    @api.depends('asset_id', 'depreciation_value', 'asset_id.total_depreciable_value', 'asset_id.already_depreciated_amount_import', 'state')
    def _compute_depreciation_cumulative_value(self):
        self.asset_depreciated_value = 0
        self.asset_remaining_value = 0

        # make sure to protect all the records being assigned, because the
        # assignments invoke method write() on non-protected records, which may
        # cause an infinite recursion in case method write() needs to read one
        # of these fields (like in case of a base automation)
        fields = [self._fields['asset_remaining_value'], self._fields['asset_depreciated_value']]
        with self.env.protecting(fields, self.asset_id.depreciation_move_ids):
            for asset in self.asset_id:
                depreciated = 0
                remaining = asset.total_depreciable_value - asset.already_depreciated_amount_import
                for move in asset.depreciation_move_ids.sorted(lambda mv: (mv.date, mv._origin.id)):
                    # if move.state != 'cancel':
                    remaining -= move.depreciation_value
                    depreciated += move.depreciation_value
                    move.asset_remaining_value = remaining
                    move.asset_depreciated_value = depreciated
