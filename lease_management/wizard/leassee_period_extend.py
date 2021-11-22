# -*- coding: utf-8 -*-
""" init object """
from odoo import fields, models, api, _
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from dateutil.relativedelta import relativedelta

import logging

LOGGER = logging.getLogger(__name__)


class LeaseePeriodExtend(models.TransientModel):
    _name = 'leasee.period.extend'
    _description = 'Leasee Period Extend'

    # reassessment_start_Date = fields.Date(default=lambda self: fields.Date.today(), required=True, )
    leasee_contract_id = fields.Many2one(comodel_name="leasee.contract", string="", required=False,ondelete='cascade' )
    new_contract_period = fields.Integer(string="Extended Contract Period", default=1, required=True, )

    @api.model
    def default_get(self, fields):
        res = super(LeaseePeriodExtend, self).default_get(fields)
        leasee_contract_id = self.env.context.get('active_id')
        # leasee_contract = self.env['leasee.contract'].browse(leasee_contract_id)
        res['leasee_contract_id'] = leasee_contract_id
        return res

    def action_apply(self):
        contract = self.leasee_contract_id
        # prev_liability = contract.lease_liability
        # prev_period = contract.lease_contract_period
        self.action_create_extend_log()
        last_installment = self.env['leasee.installment'].search([
            ('leasee_contract_id', '=', self.leasee_contract_id.id),
        ], order='date desc', limit=1)
        installment_amount = last_installment.amount * (1 + contract.increasement_rate / 100)
        new_contract = contract.copy({
            'name': contract.name,
            'inception_date': contract.estimated_ending_date,
            'commencement_date': contract.estimated_ending_date,
            'installment_amount': installment_amount,
            'lease_contract_period': self.new_contract_period,
            'parent_id': contract.id,
            'asset_id': contract.asset_id.id,
        })
        contract.state = 'extended'
        new_contract.action_activate()
        self.update_asset_value(new_contract.rou_value)


    # def action_apply(self):
    #     contract = self.leasee_contract_id
    #     prev_liability = contract.lease_liability
    #     prev_period = contract.lease_contract_period
    #     self.action_create_extend_log()
    #     last_installment = self.env['leasee.installment'].search([
    #         ('leasee_contract_id', '=', self.leasee_contract_id.id),
    #     ], order='date desc', limit=1)
    #
    #     len_new_installments = self.new_contract_period - prev_period
    #     last_amount = last_installment.amount
    #     installment_date = last_installment.date
    #     installments = self.env['leasee.installment']
    #     if len_new_installments > 0:
    #         for i in range(len_new_installments):
    #             amount = last_amount * ( 1 + contract.increasement_rate / 100)
    #             installment_date = installment_date + (relativedelta(months=1) if contract.lease_contract_period_type == 'months' else relativedelta(years=1))
    #             if i == 0:
    #                 start_date = installment_date
    #             installments |= self.env['leasee.installment'].create({
    #                 'name': contract.name + ' installment - ' + installment_date.strftime(DF),
    #                 'amount': amount,
    #                 'date': installment_date,
    #                 'leasee_contract_id': contract.id,
    #             })
    #             last_amount = amount
    #
    #         new_liability = contract.lease_liability
    #         diff_liability = new_liability - prev_liability
    #         self.create_extend_move(contract, diff_liability, start_date)
    #         self.update_asset_value(diff_liability)
    #         # first_installment = installments[0]
    #         first_subsequent_amount = last_installment.subsequent_amount
    #         remaining_liability = first_subsequent_amount / (contract.interest_rate / 100) + diff_liability - last_installment.amount
    #
    #         for installment in installments:
    #             if contract.interest_rate:
    #                 installment.subsequent_amount = remaining_liability * contract.interest_rate / 100
    #                 remaining_liability = remaining_liability * ( 1 + contract.interest_rate / 100 ) - installment.amount
    #                 installment.remaining_lease_liability = remaining_liability
    #             else:
    #                 installment.subsequent_amount = 0
    #                 installment.remaining_lease_liability = remaining_liability
    #                 remaining_liability -= installment.amount
    #
    #         contract.state = 'extended'
    #         contract.expired_notified = False
    #         contract.lease_contract_period = self.new_contract_period

    def create_extend_move(self, contract, amount, update_date):
        rou_account = contract.asset_model_id.account_asset_id
        lines = [(0, 0, {
            'name': 'Extend contract number %s' % contract.name,
            'account_id': rou_account.id,
            'credit': 0,
            'debit': amount,
            'analytic_account_id': contract.analytic_account_id.id,
        }),(0, 0, {
            'name': 'Extend contract number %s' % contract.name,
            'account_id': contract.lease_liability_account_id.id,
            'debit': 0,
            'credit': amount,
            'analytic_account_id': contract.analytic_account_id.id,
            'project_site_id': contract.project_site_id.id,
            'type_id': contract.type_id.id,
            'location_id': contract.location_id.id,
        })]
        move = self.env['account.move'].create({
            'partner_id': contract.vendor_id.id,
            'move_type': 'entry',
            'currency_id': contract.leasee_currency_id.id,
            'ref': contract.name,
            'date': update_date,
            'journal_id': contract.asset_model_id.journal_id.id,
            'leasee_contract_id': contract.id,
            'line_ids': lines,
        })

    def update_asset_value(self, new_value):
        asset = self.leasee_contract_id.asset_id
        self.env['asset.modify'].create({
            'name': "Extend Leasee Contract",
            'date': asset.acquisition_date,
            'method_number': self.new_contract_period + self.leasee_contract_id.lease_contract_period,
            'asset_id': asset.id,
            'value_residual': new_value + asset.original_value,
            'salvage_value': asset.salvage_value,
            "account_asset_counterpart_id": self.leasee_contract_id.lease_liability_account_id.id,
        }).modify()

    def action_create_extend_log(self):
        self.env['leasee.extend.log'].create({
            'leasee_contract_id': self.leasee_contract_id.id,
            'old_period': self.leasee_contract_id.lease_contract_period,
            'new_period': self.new_contract_period,
        })























