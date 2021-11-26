# -*- coding: utf-8 -*-
""" init object """
from odoo import fields, models, api, _

import logging

LOGGER = logging.getLogger(__name__)


class LeaseeInstallment(models.Model):
    _name = 'leasee.installment'
    _order = 'date,period'
    _description = 'Leasee Installment'

    name = fields.Char(string="", default="", required=True, )

    amount = fields.Float(string="", default=0.0, required=False, )
    period = fields.Integer(string="", default=0, required=False, )
    date = fields.Date(string="", )
    leasee_contract_id = fields.Many2one(comodel_name="leasee.contract", string="", required=False,ondelete='cascade' )
    installment_invoice_id = fields.Many2one(comodel_name="account.move", string="", required=False, )
    subsequent_amount = fields.Float()
    remaining_lease_liability = fields.Float()
    # installment_move_id = fields.Many2one(comodel_name="account.move", string="", required=False, )
    # interest_move_id = fields.Many2one(comodel_name="account.move", string="", required=False, )
    interest_move_ids = fields.One2many(comodel_name="account.move", inverse_name="leasee_installment_id", string="", required=False, )

    def get_period_order(self):
        if not max(self.leasee_contract_id.installment_ids.mapped('period')):
            i = 0
            for inst in self.leasee_contract_id.installment_ids:
                i += 1
                if inst == self:
                    return i
        else:
            return self.period


