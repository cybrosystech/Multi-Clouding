# -*- coding: utf-8 -*-
""" init object """
import math

from dateutil.relativedelta import relativedelta
from odoo import fields, models, api, _

import logging

LOGGER = logging.getLogger(__name__)


class LeaseeInstallment(models.Model):
    _name = 'leasee.installment'
    _order = 'date,period'
    _description = 'Leasee Installment'

    name = fields.Char(string="", default="", required=True, )

    amount = fields.Float(string="", default=0.0, required=False, digits=(16, 5) )
    period = fields.Integer(string="Installment", default=0, required=False, )
    date = fields.Date(string="", )
    leasee_contract_id = fields.Many2one(comodel_name="leasee.contract", string="", required=False,ondelete='cascade' )
    installment_invoice_id = fields.Many2one(comodel_name="account.move", string="", required=False, )
    subsequent_amount = fields.Float(digits=(16, 5))
    interest_amount = fields.Float(digits=(16, 5), compute="compute_interest_amount")
    remaining_lease_liability = fields.Float(digits=(16, 5))
    interest_move_ids = fields.One2many(comodel_name="account.move", inverse_name="leasee_installment_id", string="", required=False, index=True)
    is_advance = fields.Boolean(default=False)
    is_long_liability = fields.Boolean(compute='compute_is_long_liability')

    def get_period_order(self):
        if not max(self.leasee_contract_id.installment_ids.mapped('period')):
            i = 0
            for inst in self.leasee_contract_id.installment_ids:
                i += 1
                if inst == self:
                    return i
        else:
            return self.period

    def compute_is_long_liability(self):
        for rec in self:
            if rec.amount:
                rec.is_long_liability = False
            else:
                current_period = rec.get_period_order()
                periods_per_year = rec.leasee_contract_id.get_installments_per_year()
                if current_period == 1 and periods_per_year == 1:
                    rec.is_long_liability = False
                else:
                    if periods_per_year > 1 and 0 < current_period <= periods_per_year:
                        rec.is_long_liability = True
                    else:
                        next_installments = self.leasee_contract_id.installment_ids.filtered(lambda i: i.get_period_order() > current_period)
                        next_installment_amount = sum(next_installments.mapped('amount'))
                        if not next_installment_amount:
                            rec.is_long_liability = False
                        else:
                            rec.is_long_liability = True

    def compute_interest_amount(self):
        for ins in self:
            if ins.interest_move_ids:
                ins.interest_amount = sum(ins.interest_move_ids.filtered(lambda i: ins.leasee_contract_id.interest_expense_account_id in i.line_ids.mapped('account_id')).mapped('amount_total'))
            else:
                ins.interest_amount = ins.subsequent_amount
