# -*- coding: utf-8 -*-
""" init object """
from odoo import fields, models
import logging

LOGGER = logging.getLogger(__name__)


class LeaseeExtendLog(models.Model):
    _name = 'leasee.extend.log'
    _description = 'Leasee Extend Log'

    leasee_contract_id = fields.Many2one(comodel_name="leasee.contract", string="", required=False,ondelete='cascade' )
    date = fields.Date(string="", default=lambda self: fields.Datetime.now(), required=False, )
    old_period = fields.Integer()
    new_period = fields.Integer()
