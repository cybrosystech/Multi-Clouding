# -*- coding: utf-8 -*-
""" init object """
from odoo import fields, models, api, _

import logging

LOGGER = logging.getLogger(__name__)


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    is_leasee_payment = fields.Boolean(default=False  )
    lease_contract_id = fields.Many2one(comodel_name="leasee.contract", )
