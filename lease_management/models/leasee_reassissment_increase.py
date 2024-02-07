# -*- coding: utf-8 -*-
""" init object """
from odoo import fields, models
import logging
LOGGER = logging.getLogger(__name__)


class LeaseeReassissmentIncrease(models.Model):
    _name = 'leasee.reassessment.increase'
    _description = 'Leasee Reassessment Increase'

    leasee_contract_id = fields.Many2one(comodel_name="leasee.contract", string="", required=False,ondelete='cascade' )
    installment_amount = fields.Float()
    installment_date = fields.Date()
