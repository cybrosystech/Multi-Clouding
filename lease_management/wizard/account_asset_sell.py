# -*- coding: utf-8 -*-
""" init object """
from odoo import fields, models, api, _

import logging

LOGGER = logging.getLogger(__name__)


class NameModel(models.TransientModel):
    _inherit = 'account.asset.sell'

    from_leasee_contract = fields.Boolean(default=False)
    contract_end_date = fields.Date(required=False,)
