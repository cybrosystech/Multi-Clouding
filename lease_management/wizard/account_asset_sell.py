# -*- coding: utf-8 -*-
""" init object """
from odoo import fields, models

import logging

LOGGER = logging.getLogger(__name__)


class NameModel(models.TransientModel):
    _inherit = 'asset.modify'

    from_leasee_contract = fields.Boolean(default=False)
