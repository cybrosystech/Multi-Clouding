# -*- coding: utf-8 -*-
""" init object """
from odoo import fields, models, api, _

import logging

LOGGER = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    leasee_contract_id = fields.Many2one(comodel_name="leasee.contract", index=True)
    leasee_installment_id = fields.Many2one(comodel_name="leasee.installment", string="", required=False, )
    leasor_contract_id = fields.Many2one(comodel_name="leasor.contract", string="", required=False, )
    posting_date = fields.Date()
    is_installment_entry = fields.Boolean(default=False)

    def _post(self, soft=True):
        to_post = super(AccountMove, self)._post(soft)
        for move in to_post:
            move.posting_date = fields.Date.today()
        return to_post


