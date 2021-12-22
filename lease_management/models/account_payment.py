# -*- coding: utf-8 -*-
""" init object """
from odoo import fields, models, api, _

import logging

LOGGER = logging.getLogger(__name__)


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    is_leasee_payment = fields.Boolean(default=False  )
    lease_contract_id = fields.Many2one(comodel_name="leasee.contract", )

    def action_post(self):
        super(AccountPayment, self).action_post()
        for rec in self:
            if rec.lease_contract_id and rec.lease_contract_id.asset_id:
                asset = rec.lease_contract_id.asset_id
                asset.write({'original_value': asset.original_value + rec.amount })