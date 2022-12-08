# -*- coding: utf-8 -*-
""" init object """
from odoo import fields, models, api, _

import logging

LOGGER = logging.getLogger(__name__)


class NameModel(models.TransientModel):
    _inherit = 'account.asset.sell'

    from_leasee_contract = fields.Boolean(default=False)
    contract_end_date = fields.Date(required=False,)

    # def do_action(self):
    #     if self._context['active_model'] == 'leasee.contract':
    #         leasee_contract = self.env['leasee.contract'].browse(
    #             int(self._context['active_id']))
    #         leasee_contract.termination_date = self.contract_end_date
    #     return super(NameModel, self.with_context(
    #         disposal_date=self.contract_end_date)).do_action()
