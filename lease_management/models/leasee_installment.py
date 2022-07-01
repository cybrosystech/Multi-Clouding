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
    remaining_lease_liability = fields.Float(digits=(16, 5))
    # installment_move_id = fields.Many2one(comodel_name="account.move", string="", required=False, )
    # interest_move_id = fields.Many2one(comodel_name="account.move", string="", required=False, )
    interest_move_ids = fields.One2many(comodel_name="account.move", inverse_name="leasee_installment_id", string="", required=False, )
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
            # elif not rec.leasee_contract_id.is_contract_not_annual():
            #     rec.is_long_liability = True
            # else:
            #     annual_amount = rec.get_total_amount_installment_annual()
            #     if annual_amount:
            #         rec.is_long_liability = False
            #     else:
            #         rec.is_long_liability = True
            else:
                rec.is_long_liability = True

    #
    # def get_total_amount_installment_annual(self):
    #     advance_ins_by_date = {}
    #     contract = self.leasee_contract_id
    #     advance_installments = contract.installment_ids.filtered(lambda i: i.is_advance).sorted(key=lambda i: i.date)
    #     start_date = contract.commencement_date
    #     for ins in advance_installments:
    #         if ins.date > self.date:
    #             break
    #         else:
    #             start_date = ins.date
    #             advance_ins_by_date[start_date] = ins
    #
    #     period = self.get_period_order()
    #     num_installments = contract.get_installments_per_year()
    #     if advance_ins_by_date:
    #         last_advance = advance_ins_by_date[start_date]
    #         diff_period = period - last_advance.get_period_order()
    #         ins_year = math.ceil(diff_period / num_installments)
    #         first_period = last_advance.get_period_order() + (ins_year - 1) * num_installments + 1
    #         last_period = last_advance.get_period_order() + ins_year * num_installments
    #         installments = contract.installment_ids.filtered(lambda i: first_period <= i.get_period_order() <= last_period and not i.is_advance)
    #     else:
    #         current_year = math.ceil(period / num_installments)
    #         start_year = contract.commencement_date + relativedelta(years=current_year - 1)
    #         end_year = contract.commencement_date + relativedelta(years=current_year)
    #         if contract.payment_method == 'beginning':
    #             installments = contract.installment_ids.filtered(lambda i: start_year <= i.date < end_year and not i.is_advance)
    #         else:
    #             installments = contract.installment_ids.filtered(lambda i: start_year < i.date <= end_year and not i.is_a