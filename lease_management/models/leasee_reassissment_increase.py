# -*- coding: utf-8 -*-
""" init object """
from odoo import fields, models, api, _

import logging

LOGGER = logging.getLogger(__name__)


class LeaseeReassissmentIncrease(models.Model):
    _name = 'leasee.reassessment.increase'
    _description = 'Leasee Reassessment Increase'

    leasee_contract_id = fields.Many2one(comodel_name="", string="", required=False, )
    installment_amount = fields.Float()
    installment_date = fields.Date()





