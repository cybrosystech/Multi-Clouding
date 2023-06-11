# -*- coding: utf-8 -*-
""" init object """
from odoo import fields, models, api, _ ,tools, SUPERUSER_ID
from odoo.exceptions import ValidationError,UserError
from datetime import datetime , date ,timedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DTF
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from dateutil.relativedelta import relativedelta
from odoo.fields import Datetime as fieldsDatetime
import calendar
from odoo import http
from odoo.http import request
from odoo import tools


class AdvanceLeaseeWizard(models.TransientModel):
    _name = 'advance.leasee.wizard'
    _description = 'Advance Leasee Wizard'

    date = fields.Date(string="", default=lambda self: fields.Datetime.now(), required=True, )
    amount = fields.Float(string="", default=0.0, required=True, )

    installment_ids = fields.One2many(comodel_name="advance.leasee.line.wizard", inverse_name='wizard_id')

    @api.onchange('amount', 'date')
    def compute_installment_ids(self):
        contract = self.env['leasee.contract'].browse(self._context.get('active_id'))
        for rec in self:
            installments = contract.installment_ids.filtered(lambda i: i.date >= self.date)
            installment_data = installments.search_read([('id', 'in', installments.ids)], ['date', 'amount'], order='date ASC')
            new_installments = [(0, 0, {'amount': d['amount'], 'date': d['date'], 'installment_id': d['id']}) for d in installment_data]
            new_installments.insert(0, (5,) )
            rec.installment_ids = new_installments

    def action_apply(self):
        reduction_amount = 0
        ins_values = []
        adv_instalment = self.installment_ids.filtered(lambda x:x.date.year == self.date.year)
        print('adv_instalment', adv_instalment)
        if adv_instalment:
            if adv_instalment.installment_id.amount == 0:
                print(adv_instalment, self.date)
                abc = adv_instalment.date - self.date
                reduction_amount = (adv_instalment.installment_id.subsequent_amount * abc.days)/365
        contract = self.env['leasee.contract'].browse(self._context.get('active_id'))
        reassessment_installments = contract.installment_ids.filtered(lambda i: i.date > self.date).sorted(key=lambda i: i.date)
        first_installment = reassessment_installments[0]
        before_first = contract.installment_ids.filtered(lambda i: i.get_period_order() == first_installment.get_period_order() - 1)
        days = (reassessment_installments[0].date - before_first.date).days
        days_before_reassessment = (self.date - before_first.date).days
        remaining_lease_liability_before = contract.get_reassessment_before_remaining_lease(reassessment_installments,
                                                                                        days_before_reassessment, days)
        before_update_values_dict = {}
        before_update_values = self.env['leasee.installment'].search_read([('id', 'in', contract.installment_ids.ids)], ['period', 'amount', 'date', 'subsequent_amount', 'remaining_lease_liability'])
        prev_installment = contract.installment_ids.filtered(lambda i: i.date < self.date)[-1]
        prev_period = prev_installment.get_period_order()
        for row in before_update_values:
            before_update_values_dict[row['id']] = row
        for ins in self.installment_ids:
            ins_values.append((1, ins.installment_id.id, {
                'date': ins.date,
                'amount': ins.amount,
                'period': ins.installment_id.get_period_order() + 1,
            }))
        ins_values.append((0, 0, {'date': self.date, 'amount': self.amount, 'period': prev_period + 1, 'is_advance': True}))
        contract.installment_ids = ins_values
        contract.update_reassessed_installments_after(before_update_values_dict, self.date, remaining_lease_liability_before, reduction_amount)


class AdvanceLeaseeLineWizard(models.TransientModel):
    _name = 'advance.leasee.line.wizard'
    _description = 'Advance Leasee Line Wizard'

    amount = fields.Float(digits=(16, 5))
    date = fields.Date()
    installment_id = fields.Many2one('leasee.installment')
    wizard_id = fields.Many2one(comodel_name="advance.leasee.wizard")
