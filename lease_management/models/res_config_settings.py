# -*- coding: utf-8 -*-
""" init object """
from odoo import fields, models

import logging

LOGGER = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    lease_notification_period = fields.Integer(string="Lease's Before Expiration Notification", default=10, required=True, config_parameter='lease_notification_period' )
