# -*- coding: utf-8 -*-
""" init object """
from odoo import fields, models, _
import logging
LOGGER = logging.getLogger(__name__)


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    is_leasee_payment = fields.Boolean(default=False  )
    lease_contract_id = fields.Many2one(comodel_name="leasee.contract", )

    def action_post(self):
        super(AccountPayment, self).action_post()
        for rec in self:
            if rec.lease_contract_id:
                body = self.env.user.name + _(' add payment ') + self.name + ' with amount ' + str(self.amount) + ' .'
                rec.lease_contract_id.message_post(body=body)
                if rec.lease_contract_id.asset_id:
                    asset = rec.lease_contract_id.asset_id
                    asset.write({'original_value': asset.original_value + rec.amount })
