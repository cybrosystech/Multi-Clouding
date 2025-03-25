# -*- coding: utf-8 -*-
""" init object """
from odoo import fields, models, api, _
from dateutil.relativedelta import relativedelta

import logging

from odoo.exceptions import ValidationError, UserError

LOGGER = logging.getLogger(__name__)


class LeaseePeriodExtend(models.TransientModel):
    _name = 'leasee.period.extend'
    _description = 'Leasee Period Extend'

    leasee_contract_id = fields.Many2one(comodel_name="leasee.contract",
                                         string="", required=False,
                                         ondelete='cascade')
    new_contract_period = fields.Integer(string="Extended Contract Period",
                                         default=1, required=True, )
    estimated_cost_dismantling = fields.Float(string="", default=0.0,
                                              required=False, )
    incentives_received = fields.Float(string="", default=0.0, required=False, )
    incentives_received_type = fields.Selection(default="receivable",
                                                selection=[('receivable',
                                                            'Receivable'), (
                                                           'rent_free',
                                                           'Rent Free'), ],
                                                required=True, )
    initial_direct_cost = fields.Float(string="", default=0.0, required=False, )
    installment_amount = fields.Float(string="", default=0.0, required=False, )
    increasement_rate = fields.Float(default=0, required=False, )
    increasement_frequency = fields.Integer(default=1, required=False, )
    inception_date = fields.Date(required=False, )
    security_amount = fields.Float(string="Security Amount",
                                   help="Security Amount")
    interest_rate = fields.Float(string="Interest Rate %", default=0.0,
                                 required=False, digits=(16, 5), tracking=True)

    @api.onchange('new_contract_period')
    def onchange_new_contract_period(self):
        interest_rate = self.env['leasee.interest.rate'].search(
            [('years', '=', self.new_contract_period),
             ('company_id', '=', self.leasee_contract_id.company_id.id)])
        if interest_rate:
            self.interest_rate = interest_rate.rate
        else:
            self.interest_rate = 0.0

    @api.model
    def default_get(self, fields):
        res = super(LeaseePeriodExtend, self).default_get(fields)
        leasee_contract_id = self.env.context.get('active_id')
        res['leasee_contract_id'] = leasee_contract_id
        lease = self.env['leasee.contract'].browse(leasee_contract_id)
        res['installment_amount'] = lease.installment_amount
        res['interest_rate'] = lease.interest_rate
        res["security_amount"] = lease.security_amount
        return res

    @api.constrains('installment_amount')
    def on_save_installment_amount(self):
        if self.installment_amount == 0.0:
            raise ValidationError(_('Please enter installment amount'))

    @api.constrains('interest_rate')
    def on_save_interest_rate(self):
        if self.interest_rate == 0.0:
            raise ValidationError(_('Please enter interest rate'))

    def action_apply(self):
        contract = self.leasee_contract_id
        if contract.child_ids:
            raise UserError('The lease has already been extended; go to the latest child lease for further extension.')
        self.action_create_extend_log()
        last_installment = self.env['leasee.installment'].search([
            ('leasee_contract_id', '=', self.leasee_contract_id.id),
            ('amount', '>', 0.0),
        ], order='date desc', limit=1)
        if self.inception_date:
            new_contract = contract.with_context(lease_extension=True).copy({
                'name': contract.name,
                'inception_date': self.inception_date,
                'commencement_date': contract.estimated_ending_date + relativedelta(
                    days=1),
                'installment_amount': self.installment_amount,
                'lease_contract_period': self.new_contract_period,
                'parent_id': contract.id,
                'asset_id': contract.asset_id.id,
                'estimated_cost_dismantling': self.estimated_cost_dismantling,
                'incentives_received': self.incentives_received,
                'incentives_received_type': self.incentives_received_type,
                'initial_direct_cost': self.initial_direct_cost,
                'increasement_rate': self.increasement_rate,
                'increasement_frequency': self.increasement_frequency,
                'company_id': self.env.company.id,
                'security_amount': self.security_amount,
                'security_prepaid_account': contract.leasee_template_id.security_prepaid_account.id,
                'security_deferred_account': contract.leasee_template_id.security_deferred_account.id,
                'interest_rate': self.interest_rate,
                'useful_life': self.new_contract_period,

            })
        else:
            new_contract = contract.copy({
                'name': contract.name,
                'inception_date': contract.estimated_ending_date + relativedelta(
                    days=1),
                'commencement_date': contract.estimated_ending_date + relativedelta(
                    days=1),
                'installment_amount': self.installment_amount,
                'lease_contract_period': self.new_contract_period,
                'parent_id': contract.id,
                'asset_id': contract.asset_id.id,
                'estimated_cost_dismantling': self.estimated_cost_dismantling,
                'incentives_received': self.incentives_received,
                'incentives_received_type': self.incentives_received_type,
                'initial_direct_cost': self.initial_direct_cost,
                'increasement_rate': self.increasement_rate,
                'increasement_frequency': self.increasement_frequency,
                'company_id': self.env.company.id,
                'security_amount': self.security_amount,
                'security_prepaid_account': contract.leasee_template_id.security_prepaid_account.id,
                'security_deferred_account': contract.leasee_template_id.security_deferred_account.id,
                'interest_rate': self.interest_rate,
                'useful_life': self.new_contract_period,
            })
        contract.state = 'extended'
        for leasor in new_contract.multi_leasor_ids:
            if leasor.type != 'percentage':
                percentage = leasor.amount / contract.installment_amount * 100
                new_amount = new_contract.installment_amount * (
                            percentage / 100)
                leasor.amount = new_amount

        new_contract.action_activate()
        self.update_asset_value(new_contract.rou_value)

    def create_extend_move(self, contract, amount, update_date):
        rou_account = contract.asset_model_id.account_asset_id
        lines = [(0, 0, {
            'name': 'Extend contract number %s' % contract.name,
            'account_id': rou_account.id,
            'credit': 0,
            'debit': amount,
            'display_type': 'product',

            'analytic_account_id': contract.analytic_account_id.id,
            'project_site_id': contract.project_site_id.id,
            'type_id': contract.type_id.id,
            'location_id': contract.location_id.id,
        }), (0, 0, {
            'name': 'Extend contract number %s' % contract.name,
            'account_id': contract.lease_liability_account_id.id,
            'debit': 0,
            'credit': amount,
            'display_type': 'product',

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
            'auto_post': True,
        })

    def update_asset_value(self, new_value):
        contract = self.leasee_contract_id
        asset = contract.asset_id
        new_period = (self.new_contract_period) * (
            1 if contract.lease_contract_period_type == 'months' else 12)
        self.env['asset.modify'].create({
            'name': "Extend Leasee Contract",
            'date': contract.estimated_ending_date + relativedelta(days=1),
            'method_number': new_period,
            'asset_id': asset.id,
            'value_residual': new_value,
            'salvage_value': asset.salvage_value,
            "account_asset_counterpart_id": self.leasee_contract_id.lease_liability_account_id.id,
        }).with_context(extend_leasee_contract=True).modify()

    def action_create_extend_log(self):
        self.env['leasee.extend.log'].create({
            'leasee_contract_id': self.leasee_contract_id.id,
            'old_period': self.leasee_contract_id.lease_contract_period,
            'new_period': self.new_contract_period,
        })
