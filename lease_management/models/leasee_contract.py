# -*- coding: utf-8 -*-
""" init object """
import math

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

import logging

LOGGER = logging.getLogger(__name__)


class LeaseeContract(models.Model):
    _name = 'leasee.contract'
    _rec_name = 'name'
    _description = 'Leasee Contract'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Name", required=True, copy=False, readonly=True, default='/' )
    leasee_template_id = fields.Many2one(comodel_name="leasee.contract.template", string="Leasee Contract Template", required=False, )

    external_reference_number = fields.Char()
    state = fields.Selection(string="Agreement Status",default="draft", selection=[('draft', 'Draft'), ('active', 'Active'), ('extended', 'Extended'), ('expired', 'Expired'), ('terminated', 'Terminated'), ], required=False, tracking=True )

    vendor_id = fields.Many2one(comodel_name="res.partner", string="Leassor Name", required=False, tracking=True)
    inception_date = fields.Date(default=lambda self: fields.Datetime.now(), required=False, )
    commencement_date = fields.Date(default=lambda self: fields.Datetime.now(), required=False, tracking=True)
    initial_payment_value = fields.Float(compute='compute_initial_payment_value', tracking=True)
    estimated_ending_date = fields.Date(compute='compute_estimated_ending_date')

    # lease_contract_period = fields.Float()
    lease_contract_period = fields.Integer(tracking=True)
    lease_contract_period_type = fields.Selection(string="Period Type", default="months",
                                              selection=[('years', 'Years'), ('months', 'Months'), ], required=True,tracking=True )
    terminate_month_number = fields.Integer(string="Terminate At Month Number", default=0, required=False, )
    terminate_fine = fields.Float(string="", default=0.0, required=False, )
    type_terminate = fields.Selection(string="Percentage or Amount",default="amount", selection=[('percentage', 'Percentage'), ('amount', 'Amount'), ], required=True, )
    extendable = fields.Boolean(string="Extendable ?", default=False )
    interest_rate = fields.Float(string="Interest Rate %", default=0.0, required=False, digits=(16, 5), tracking=True)
    payment_frequency_type = fields.Selection(string="Payment Type",default="months", selection=[('years', 'Years'), ('months', 'Months'), ], required=True,tracking=True )
    payment_frequency = fields.Integer(default=1, required=False, tracking=True)

    increasement_frequency_type = fields.Selection(string="Increasement Type",default="months", selection=[('years', 'Years'), ('months', 'Months'), ], required=True, tracking=True)
    increasement_frequency = fields.Integer(default=1, required=False, tracking=True)
    increasement_rate = fields.Float(default=1, required=False, digits=(16, 5), tracking=True )
    # discount = fields.Float(string="Discount %", default=0.0, required=False, )
    asset_model_id = fields.Many2one(comodel_name="account.asset", string="Asset Model", required=False, domain=[('asset_type', '=', 'purchase'), ('state', '=', 'model')] )
    asset_id = fields.Many2one(comodel_name="account.asset", copy=False)

    leasee_currency_id = fields.Many2one(comodel_name="res.currency", string="", required=True, )
    asset_name = fields.Char(string="", default="", required=False, )
    asset_description = fields.Text(string="", default="", required=False, )
    initial_direct_cost = fields.Float(copy=True, tracking=True)
    incentives_received = fields.Float(copy=True, tracking=True)
    incentives_received_type = fields.Selection(default="receivable", selection=[('receivable', 'Receivable'), ('rent_free', 'Rent Free - Advance Discount'), ], required=True, tracking=True)
    rou_value = fields.Float(string="ROU Asset Value",compute='compute_rou_value', tracking=True)
    # registered_paymen = fields.Float(string="Registered Payment Prior Commencement Date")

    estimated_cost_dismantling = fields.Float(string="Estimated Cost For Dismantling", default=0.0, required=False,copy=True, digits=(16, 5) )
    useful_life = fields.Integer(string="Useful Life Of The Right Of The Use Asset", default=0, required=False )
    lease_liability = fields.Float(compute='compute_lease_liability', digits=(16, 5))
    installment_amount = fields.Float(string="", default=0.0, required=False, digits=(16, 5) )
    remaining_lease_liability = fields.Float(compute='compute_remaining_lease_liability', digits=(16, 5) )
    remaining_short_lease_liability = fields.Float(compute='compute_remaining_lease_liability', digits=(16, 5) )
    remaining_long_lease_liability = fields.Float(compute='compute_remaining_lease_liability', digits=(16, 5) )

    account_move_ids = fields.One2many(comodel_name="account.move", inverse_name="leasee_contract_id", string="", required=False, )

    lease_liability_account_id = fields.Many2one(comodel_name="account.account", string="Short Lease Liability Account", required=True, )
    long_lease_liability_account_id = fields.Many2one(comodel_name="account.account", string="Long Lease Liability Account", required=True, )
    provision_dismantling_account_id = fields.Many2one(comodel_name="account.account", string="", required=True, )
    terminate_account_id = fields.Many2one(comodel_name="account.account", string="", required=True, )
    interest_expense_account_id = fields.Many2one(comodel_name="account.account", string="", required=True, )
    installment_journal_id = fields.Many2one(comodel_name="account.journal", string="", required=True, )
    initial_journal_id = fields.Many2one(comodel_name="account.journal", string="", required=True, )
    analytic_account_id = fields.Many2one(comodel_name="account.analytic.account", string="", required=True, )

    # interest_expense_account_id = fields.Many2one(comodel_name="account.account", string="", required=True, )

    terminate_product_id = fields.Many2one(comodel_name="product.product", string="", required=True,domain=[('type', '=', 'service')] )
    installment_product_id = fields.Many2one(comodel_name="product.product", string="", required=True,domain=[('type', '=', 'service')] )
    extension_product_id = fields.Many2one(comodel_name="product.product", string="", required=True,domain=[('type', '=', 'service')] )
    initial_product_id = fields.Many2one(comodel_name="product.product", string="", required=True,domain=[('type', '=', 'service')] )

    payment_method = fields.Selection(string="Payment Method",default="beginning", selection=[('beginning', 'Beginning of Period'), ('end', 'End Of Period'), ], required=False, tracking=True)

    notification_days = fields.Integer()
    payment_ids = fields.One2many(comodel_name="account.payment", inverse_name="lease_contract_id", string="", required=False, )
    installment_ids = fields.One2many(comodel_name="leasee.installment", inverse_name="leasee_contract_id", string="", required=False, )
    expired_notified = fields.Boolean(default=False  )

    project_site_id = fields.Many2one(comodel_name="account.analytic.account", string="Project/Site",
                                      domain=[('analytic_account_type', '=', 'project_site')], required=False, )
    type_id = fields.Many2one(comodel_name="account.analytic.account", string="Type",
                              domain=[('analytic_account_type', '=', 'type')], required=False, )
    location_id = fields.Many2one(comodel_name="account.analytic.account", string="Location",
                                  domain=[('analytic_account_type', '=', 'location')], required=False, )
    prorata = fields.Boolean(default=True, readonly=True)
    parent_id = fields.Many2one(comodel_name="leasee.contract", string="", required=False, copy=False)
    child_ids = fields.One2many(comodel_name="leasee.contract", inverse_name="parent_id", string="", required=False, copy=False)

    incentives_account_id = fields.Many2one(comodel_name="account.account", string="", required=True, )
    incentives_product_id = fields.Many2one(comodel_name="product.product", string="", required=True, domain=[('type', '=', 'service')] )
    leasor_type = fields.Selection(string="Leasor Type",default="single", selection=[('single', 'Single'), ('multi', 'Multi'), ], required=True, copy=True , tracking=True)
    multi_leasor_ids = fields.One2many(comodel_name="multi.leasor", inverse_name="leasee_contract_id", string="", required=False, copy=True, tracking=True)

    @api.depends('commencement_date', 'lease_contract_period')
    def compute_estimated_ending_date(self):
        for rec in self:
            if rec.lease_contract_period_type == 'years':
                rec.estimated_ending_date = rec.commencement_date + relativedelta(years=rec.lease_contract_period, days=-1)
            else:
                rec.estimated_ending_date = rec.commencement_date + relativedelta(months=rec.lease_contract_period, days=-1)

    @api.onchange('project_site_id')
    def get_location_and_types(self):
        for rec in self:
            rec.type_id = rec.project_site_id.analytic_type_filter_id.id
            rec.location_id = rec.project_site_id.analytic_location_id.id

    @api.onchange('leasee_template_id')
    def onchange_leasee_template_id(self):
        self.update({
            'lease_contract_period': self.leasee_template_id.lease_contract_period,
            'lease_contract_period_type': self.leasee_template_id.lease_contract_period_type,
            'terminate_month_number': self.leasee_template_id.terminate_month_number,
            'terminate_fine': self.leasee_template_id.terminate_fine,
            'type_terminate': self.leasee_template_id.type_terminate,
            'extendable': self.leasee_template_id.extendable,
            'interest_rate': self.leasee_template_id.interest_rate,
            'payment_frequency_type': self.leasee_template_id.payment_frequency_type,
            'payment_frequency': self.leasee_template_id.payment_frequency,
            'increasement_rate': self.leasee_template_id.increasement_rate,
            'increasement_frequency_type': self.leasee_template_id.increasement_frequency_type,
            'increasement_frequency': self.leasee_template_id.increasement_frequency,
            'prorata': self.leasee_template_id.prorata,
            'asset_model_id': self.leasee_template_id.asset_model_id.id,
            'lease_liability_account_id': self.leasee_template_id.lease_liability_account_id.id,
            'long_lease_liability_account_id': self.leasee_template_id.long_lease_liability_account_id.id,
            'provision_dismantling_account_id': self.leasee_template_id.provision_dismantling_account_id.id,
            'terminate_account_id': self.leasee_template_id.terminate_account_id.id,
            'interest_expense_account_id': self.leasee_template_id.interest_expense_account_id.id,
            'terminate_product_id': self.leasee_template_id.terminate_product_id.id,
            'installment_product_id': self.leasee_template_id.installment_product_id.id,
            'extension_product_id': self.leasee_template_id.extension_product_id.id,
            'installment_journal_id': self.leasee_template_id.installment_journal_id.id,
            'initial_journal_id': self.leasee_template_id.initial_journal_id.id,
            'analytic_account_id': self.leasee_template_id.analytic_account_id.id,
            'project_site_id': self.leasee_template_id.project_site_id.id,
            'type_id': self.leasee_template_id.type_id.id,
            'location_id': self.leasee_template_id.location_id.id,
            'incentives_account_id': self.leasee_template_id.incentives_account_id.id,
            'incentives_product_id': self.leasee_template_id.incentives_product_id.id,
            'initial_product_id': self.leasee_template_id.initial_product_id.id,
        })

    def write(self, vals):
        super(LeaseeContract, self).write(vals)
        if 'installment_ids' in vals and self.state == 'draft':
            self.update_reassessed_installments_before()
        # elif 'installment_ids' in vals and self.state in ['active', 'extended']:
        #     self.update_reassessed_installments_after(before_update_values_dict)

    def update_reassessed_installments_after(self, before_update_values_dict, assessment_date, remaining_lease_liability_before):
        first_installment = self.installment_ids.filtered(lambda i: i.date == assessment_date)

        if first_installment:
            first_period = first_installment.get_period_order()
            reassessment_installments = self.installment_ids.filtered(lambda i: i.date >= assessment_date).\
                sorted(key= lambda i: i.date)
            new_lease_liability = sum([self.get_present_value_modified(installment.amount, self.interest_rate, i+first_period, first_installment.date, installment.date, installment) for i, installment in enumerate(reassessment_installments)])
            interest_recognition = 0
            remaining_liability = new_lease_liability - (first_installment.amount - interest_recognition)
            first_installment.write({
                'remaining_lease_liability': remaining_liability,
                'subsequent_amount': interest_recognition,
            })
            prev_install = first_installment
            for i, installment in enumerate(reassessment_installments.filtered(lambda i: i.date > assessment_date)):
                period_ratio = ((installment.date - prev_install.date).days) / 365
                interest_recognition = remaining_liability * ((1 + self.interest_rate / 100) ** period_ratio - 1)
                remaining_liability -= (installment.amount - interest_recognition)
                installment.subsequent_amount = interest_recognition
                installment.remaining_lease_liability = remaining_liability
                prev_install = installment

            before_first = self.installment_ids.filtered(lambda i: i.get_period_order() == first_period - 1)
            after_first = self.installment_ids.filtered(lambda i: i.get_period_order() == first_period + 1)
            old_subsequent = before_update_values_dict[after_first.id]['subsequent_amount']
            days = (after_first.date - before_first.date).days
            days_before_reassessment = (first_installment.date - before_first.date).days
            days_after_reassessment = days - days_before_reassessment
            old_remaining_liability = before_first.remaining_lease_liability + old_subsequent * days_before_reassessment / days
            # remaining_lease_liability_before = self.get_reassessment_before_remaining_lease(reassessment_installments, days_before_reassessment, days)

            self.create_reassessment_move(self, new_lease_liability - old_remaining_liability, first_installment.date)
            self.update_reassessment_asset_value(new_lease_liability - old_remaining_liability, first_installment.date)
            self.with_context(reassessment=True).update_reassessment_related_journal_items(reassessment_installments, before_update_values_dict,reassessment_date=assessment_date)
            if first_installment.amount > 0:
                if self.leasor_type == 'single':
                    self.create_installment_bill(self, first_installment, self.vendor_id, first_installment.amount)
                else:
                    for leasor in self.multi_leasor_ids:
                        partner = leasor.partner_id
                        amount = (leasor.amount / self.installment_amount) * first_installment.amount if leasor.type == 'amount' else leasor.percentage * first_installment.amount / 100
                        self.create_installment_bill(self, first_installment, partner, amount)
            # self.update_reassessment_first_installment_entries(reassessment_installments[1], old_subsequent, days_after_reassessment, days, first_installment.date)
            self.adjust_first_interest_entry(after_first, first_installment, before_first, before_update_values_dict)
            remaining_lease_liability_after = self.get_reassessment_after_remaining_lease(reassessment_installments)
            stl_amount = remaining_lease_liability_after - remaining_lease_liability_before
            self.create_reassessment_installment_entry(stl_amount, first_installment.date)

            body = self.env.user.name + _(' reassess the contract ') +  _(' starting from ') + first_installment.date.strftime('%d/%m/%Y') + ' .'
            self.message_post(body=body)

    def adjust_first_interest_entry(self, after_first, first_installment, before_first, before_update_values_dict):
        first_entry = after_first.interest_move_ids.filtered(lambda m: m.date.month == first_installment.date.month and m.date.year == first_installment.date.year)
        installment_same = first_installment.date.month == before_first.date.month and first_installment.date.year == before_first.date.year
        num_days = (after_first.date - before_first.date).days
        old_interest = before_update_values_dict[after_first.id]['subsequent_amount']
        start_interest_adj = first_installment.date.replace(day=1) if not installment_same else before_first.date
        interest_adj_days = (first_installment.date - start_interest_adj).days
        adjustment_amount = old_interest * interest_adj_days / num_days
        if first_entry and after_first.amount > 0:
            entry = first_entry[0]
            first_entry[1:].unlink()
            debit_line = entry.line_ids.filtered(lambda l: l.debit > 0)
            credit_line = entry.line_ids.filtered(lambda l: l.credit > 0)
            entry.write({'line_ids': [(1, debit_line.id, {'debit': debit_line.debit + adjustment_amount}),
                                            (1, credit_line.id, {'credit': credit_line.credit + adjustment_amount})]})
        elif first_entry and not after_first.amount and after_first.is_long_liability:
            self.with_context(use_short=True).create_interset_move(after_first, first_installment.date, adjustment_amount)
        else:
            move_date = first_installment.date.replace(day=1) + relativedelta(days=-1,months=1)
            self.with_context(reassessment=True).create_interset_move(after_first, move_date, adjustment_amount)

    def update_reassessed_installments_before(self):
        new_lease_liability = self.lease_liability
        self.installment_ids[0].remaining_lease_liability = new_lease_liability
        first_installment = self.installment_ids[1]
        reassessment_installments = self.installment_ids
        period_ratio = ((first_installment.date - self.commencement_date).days) / 365
        interest_recognition = new_lease_liability * ((1 + self.interest_rate / 100) ** period_ratio - 1)
        remaining_liability = new_lease_liability - (first_installment.amount - interest_recognition)
        first_installment.write({
            'remaining_lease_liability': new_lease_liability,
            'subsequent_amount': interest_recognition,
        })
        prev_install = first_installment
        for i, installment in enumerate(reassessment_installments[2:]):
            # num_days_year = 365 if contract.is_contract_not_annual() else contract.get_days_per_year(installment.date)
            period_ratio = ((installment.date - prev_install.date).days) / 365
            interest_recognition = remaining_liability * ((1 + self.interest_rate / 100) ** period_ratio - 1)
            remaining_liability -= (installment.amount - interest_recognition)
            installment.subsequent_amount = interest_recognition
            installment.remaining_lease_liability = remaining_liability
            prev_install = installment

    def action_create_installments(self):
        if not self.installment_ids:
            remaining_lease_liability = self.lease_liability
            self.create_installments(remaining_lease_liability)

    def action_activate(self):
        for contract in self:
            contract.check_leasor()
            if contract.state == 'draft':
                if contract.name == '/':
                    contract.name = self.env['ir.sequence'].next_by_code('leasee.contract')
                remaining_lease_liability = contract.lease_liability
                if not self.installment_ids:
                    contract.create_installments(remaining_lease_liability)
                contract.create_commencement_move()
                contract.create_initial_bill()
                # self.create_installments()
                contract.create_rov_asset()
                contract.create_contract_installment_entries(contract.commencement_date)
                contract.state = 'active'

                contract.leasee_action_generate_installments_entries()
                contract.leasee_action_generate_interest_entries(contract.commencement_date)

    def check_leasor(self):
        percentage = 0
        if self.leasor_type == 'multi':
            for leasor in self.multi_leasor_ids:
                if leasor.type == 'percentage':
                    percentage += leasor.percentage
                else:
                    percentage += (leasor.amount / self.installment_amount * 100)
            if round(percentage,2) != 100.0:
                raise ValidationError(_('Leasors Total must be 100%'))

    def action_view_asset(self):
        view_id = self.env.ref('account_asset.view_account_asset_form')
        view_form = {
            'name': _('Asset'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.asset',
            'type': 'ir.actions.act_window',
            'res_id': self.asset_id.id,
            'view_id': view_id.id,
        }

        return view_form

    def is_contract_not_annual(self):
        res = True if self.payment_frequency_type == 'months' and self.payment_frequency < 12 else False
        return res

    def get_installments_per_year(self):
        if self.payment_frequency_type == 'months':
            return int(12/self.payment_frequency)
        else:
            return 1

    def compute_installments_num(self):
        for rec in self:
            if rec.lease_contract_period and rec.payment_frequency:
                total_contract_months = rec.lease_contract_period * (1 if rec.lease_contract_period_type == 'months' else 12)
                payment_freq_months = rec.payment_frequency * (1 if rec.payment_frequency_type == 'months' else 12)
                return math.floor(total_contract_months/payment_freq_months)
            else:
                return 0

    @api.model
    def get_days_per_year(self, date):
        if date.year % 4 == 0 and date.month > 2:
            return 366
        if date.year % 4 == 1 and date.month <= 2:
            return 366
        else:
            return 365

    def get_installment_period(self, i):
        if self.is_contract_not_annual():
            if self.payment_method == 'beginning':
                ins_date = self.commencement_date + relativedelta(months=i*self.payment_frequency)
            else:
                ins_date = self.commencement_date + relativedelta(months=(i)*self.payment_frequency,days=-1)
            return (ins_date - self.commencement_date).days / 365
        else:
            return i

    def get_increase_period(self, installment_num):
        if self.payment_frequency_type == 'months':
            payment_months_delta = self.payment_frequency
        else:
            payment_months_delta = 12 * self.payment_frequency

        if self.increasement_frequency_type == 'months':
            increase_months_delta = self.increasement_frequency
        else:
            increase_months_delta = 12 * self.increasement_frequency
        if payment_months_delta > increase_months_delta:
            raise ValidationError(_('Payment frequency can not be greater than increase frequency'))
        increase_period = int(math.ceil(installment_num * payment_months_delta / increase_months_delta)) - 1
        return increase_period

    @api.depends('installment_amount', 'lease_contract_period', 'increasement_rate', 'installment_ids', 'installment_ids.amount')
    def compute_lease_liability(self):
        monthly_freq = {'1': 12, '3': 4, '6': 2}
        for rec in self:
            period_range = range(rec.compute_installments_num())
            if rec.payment_method == 'beginning':
                # period_range = range(rec.lease_contract_period)
                start = 0
            else:
                # period_range = range(1, rec.lease_contract_period + 1)
                start = 1

            installments_count = rec.get_installments_per_year()
            if rec.installment_ids:
                installments = rec.installment_ids[1:]
                increased_installments = installments.mapped('amount')
            else:
                increased_installments = []
                present_value = self.installment_amount
                increasement_frequency = self.increasement_frequency
                if self.payment_frequency_type == 'months' and self.payment_frequency:
                    if self.payment_frequency not in [1, 3, 6]:
                        increasement_frequency = 0
                    else:
                        increasement_frequency = (
                                self.increasement_frequency * monthly_freq[
                            '' + str(self.payment_frequency)])
                for i in period_range:
                    amount = rec.get_future_value(present_value,
                                                  rec.increasement_rate,
                                                  math.floor(
                                                      i / installments_count),
                                                  i,
                                                  increasement_frequency)
                    if i == increasement_frequency:
                        present_value = round(amount, 5)
                    if increasement_frequency > 1:
                        if i == increasement_frequency:
                            if self.payment_frequency_type == 'months' and \
                                    monthly_freq[
                                        '' + str(self.payment_frequency)]:
                                increasement_frequency += self.increasement_frequency * \
                                                          monthly_freq['' + str(
                                                              self.payment_frequency)]
                            else:
                                increasement_frequency += self.increasement_frequency
                    increased_installments.append(round(amount, 5))

                remaining_advanced = rec.initial_payment_value
                if rec.incentives_received_type == 'rent_free':
                    remaining_advanced += rec.incentives_received
                
                if remaining_advanced:
                    for i in range(len(increased_installments)):
                        if remaining_advanced > 0:
                            if remaining_advanced >= increased_installments[i]:
                                remaining_advanced -= increased_installments[i]
                                increased_installments[i] = 0
                            else:
                                increased_installments[i] -= remaining_advanced
                                remaining_advanced = 0
            if self.state == 'draft':
                if rec.prorata:
                    # net_present_value = sum([rec.get_present_value_modified(installment, rec.interest_rate, i+start) for i, installment in enumerate(increased_installments)])
                    start = start if not self.installment_ids else 1
                    net_present_value = sum([rec.get_present_value_modified(installment, rec.interest_rate, i+start) for i, installment in enumerate(increased_installments)])
                else:
                    net_present_value = sum([rec.get_present_value(installment, rec.interest_rate, i+start) for i, installment in enumerate(increased_installments)])
            else:
                rou_move_lines = self.env['account.move.line'].search([
                    ('move_id.leasee_contract_id', '=', self.id),
                    ('account_id', '=', rec.asset_id.account_asset_id.id),
                ])
                moves = rou_move_lines.mapped('move_id')
                lease_move_lines = moves.line_ids.filtered(lambda l: l.account_id == rec.long_lease_liability_account_id or l.account_id == rec.lease_liability_account_id)
                net_present_value = -1*sum([(l.debit - l.credit) for l in lease_move_lines])
            rec.lease_liability = net_present_value

    @api.depends('state','lease_liability', 'initial_payment_value', 'initial_direct_cost', 'estimated_cost_dismantling', 'incentives_received')
    def compute_rou_value(self):
        for rec in self:
            if rec.state == 'terminated':
                rec.rou_value = 0
            else:
                if rec.state == 'draft':
                    if rec.incentives_received_type == 'rent_free':
                        rec.rou_value = rec.lease_liability + rec.initial_payment_value + rec.initial_direct_cost + rec.estimated_cost_dismantling
                    else:
                        rec.rou_value = rec.lease_liability + rec.initial_payment_value + rec.initial_direct_cost + rec.estimated_cost_dismantling - rec.incentives_received
                else:
                    rou_move_lines = self.env['account.move.line'].search([
                        # ('move_id.state', '=', 'posted'),
                        # ('move_id.state', 'in', ['posted', 'cancel']),
                        ('move_id.leasee_contract_id', '=', rec.id),
                        ('account_id', '=', rec.asset_model_id.account_asset_id.id),
                    ])
                    balance = sum([(l.debit - l.credit) for l in rou_move_lines])
                    rec.rou_value = balance

    @api.model
    def get_present_value(self, future_value, interest, period):
        present_value = future_value / (1 + interest/100) ** period
        return present_value

    def get_present_value_modified(self, future_value, interest, period, start_date=None, end_period=None, installment=None):
        start_date = start_date or self.commencement_date
        if not installment:
            installment = self.installment_ids.filtered(lambda i: i.get_period_order() == period)
        if not installment and not end_period:
            payment_months = self.payment_frequency * (1 if self.payment_frequency_type == 'months' else 12)
            end_period = end_period or start_date + relativedelta(months=period*payment_months)
        end_period = end_period or installment.date
        period_ratio = ((end_period - start_date).days ) / 365
        present_value = future_value / (1 + interest/100) ** period_ratio
        return present_value

    @api.model
    def get_future_value(self, present_value, interest, period, i,
                         increasement_frequency):
        if increasement_frequency > 1 and interest > 0:
            if i == increasement_frequency:
                future_value = present_value * (1 + interest / 100)
            else:
                future_value = present_value
        else:
            future_value = present_value * (1 + interest / 100) ** period
        return future_value

    def create_rov_asset(self):
        if not self.asset_id:
            method_number = self.lease_contract_period * (1 if self.lease_contract_period_type == 'months' else 12)
            vals = {
                'name': self.name,
                'model_id': self.asset_model_id.id,
                'original_value': self.rou_value,
                'asset_type': 'purchase',
                # 'partner_id': self.vendor_id.id,
                # 'company_id': record.move_id.company_id.id,
                # 'currency_id': self.env.user.company_id.currency_id.id,
                'acquisition_date': self.commencement_date,
                # 'method_number': self.lease_contract_period,
                'method_number': method_number,
                'account_analytic_id': self.analytic_account_id.id,
                'project_site_id': self.project_site_id.id,
                'type_id': self.type_id.id,
                'location_id': self.location_id.id,
                'prorata': self.prorata,
                'state': 'draft',
                'first_depreciation_date': self.commencement_date,
                # 'method_period': self.lease_contract_period_type,
                'method_period': '1',
            }
            # changed_vals = self.env['account.asset'].onchange_category_id_values(self.asset_model_id.category_id.id)
            # vals.update(changed_vals['value'])
            # vals.update({
            #     '':,
            # })
            if self.asset_model_id:
                # asset = self.asset_model_id.copy(vals)
                vals.update({
                    'account_asset_id': self.asset_model_id.account_asset_id.id,
                    'account_depreciation_id': self.asset_model_id.account_depreciation_id.id,
                    'account_depreciation_expense_id': self.asset_model_id.account_depreciation_expense_id.id,
                    'journal_id': self.asset_model_id.journal_id.id,
                    # 'account_analytic_id': self.asset_model_id.account_analytic_id.id,
                    'method': self.asset_model_id.method,
                })
            # else:
            asset = self.env['account.asset'].create(vals)
            asset.name = self.name
            asset.state = 'draft'
            # if self.asset_model_id.category_id.open_asset:
            #     asset.validate()
            if self.prorata:
                asset.prorata_date = self.commencement_date
            self.asset_id = asset.id

    # def action_create_bill(self):
    #     pass

    def compute_remaining_lease_liability(self):
        for rec in self:
            short_move_lines = self.env['account.move.line'].search([
                # ('move_id.state', '=', 'posted'),
                ('move_id.state', 'in', ['posted','cancel']),
                ('move_id.leasee_contract_id', '=', self.id),
                ('account_id', '=', rec.lease_liability_account_id.id),
            ])
            long_move_lines = self.env['account.move.line'].search([
                # ('move_id.state', '=', 'posted'),
                ('move_id.state', 'in', ['posted','cancel']),
                ('move_id.leasee_contract_id', '=', self.id),
                ('account_id', '=', rec.long_lease_liability_account_id.id),
            ])
            short_balance = sum([(l.debit - l.credit) for l in short_move_lines])
            long_balance = sum([(l.debit - l.credit) for l in long_move_lines])
            balance = short_balance + long_balance
            rec.remaining_short_lease_liability = -1 * short_balance
            rec.remaining_long_lease_liability = -1 * long_balance
            if rec.state == 'terminated':
                rec.remaining_lease_liability = 0
            else:
                rec.remaining_lease_liability = -1 * balance

    def create_initial_bill(self):
        amount = self.initial_direct_cost + self.initial_payment_value
        if self.leasor_type == 'single':
            self.create_single_initial_bill(self.vendor_id, self.initial_direct_cost, self.initial_payment_value, self.incentives_received)
        else:
            for leasor in self.multi_leasor_ids:
                partner = leasor.partner_id
                leasor_direct_cost = (leasor.amount / self.installment_amount) * self.initial_direct_cost if leasor.type == 'amount' else leasor.percentage * self.initial_direct_cost / 100
                leasor_payment_value = (leasor.amount / self.installment_amount) * self.initial_payment_value if leasor.type == 'amount' else leasor.percentage * self.initial_payment_value / 100
                incentives_received = (leasor.amount / self.installment_amount) * self.incentives_received if leasor.type == 'amount' else leasor.percentage * self.incentives_received / 100
                self.create_single_initial_bill(partner, leasor_direct_cost, leasor_payment_value, incentives_received)

    def create_single_initial_bill(self, partner, direct_cost, payment_value, incentives_received):
        if direct_cost or payment_value:
            invoice_lines = []
            if payment_value:
                invoice_lines.append((0, 0, {
                    'product_id': self.initial_product_id.id,
                    'name': self.initial_product_id.name,
                    'product_uom_id': self.initial_product_id.uom_id.id,
                    'account_id': self.initial_product_id.product_tmpl_id.get_product_accounts()['expense'].id,
                    'price_unit': payment_value,
                    'quantity': 1,
                    'analytic_account_id': self.analytic_account_id.id,
                    'project_site_id': self.project_site_id.id,
                    'type_id': self.type_id.id,
                    'location_id': self.location_id.id,
                }))
            if direct_cost:
                invoice_lines.append((0, 0, {
                    'product_id': self.extension_product_id.id,
                    'name': self.extension_product_id.name,
                    'product_uom_id': self.extension_product_id.uom_id.id,
                    'account_id': self.extension_product_id.product_tmpl_id.get_product_accounts()['expense'].id,
                    'price_unit': direct_cost,
                    'quantity': 1,
                    'analytic_account_id': self.analytic_account_id.id,
                    'project_site_id': self.project_site_id.id,
                    'type_id': self.type_id.id,
                    'location_id': self.location_id.id,
                }))
            invoice = self.env['account.move'].create({
                'partner_id': partner.id,
                'move_type': 'in_invoice',
                'currency_id': self.leasee_currency_id.id,
                'ref': self.name,
                'invoice_date': self.commencement_date,
                'invoice_line_ids': invoice_lines,
                'journal_id': self.installment_journal_id.id,
                'leasee_contract_id': self.id,
                'auto_post': True,
            })
            line = invoice.line_ids.filtered(lambda l : l.account_id == partner.property_account_payable_id)
            if line:
                line.write({
                    'analytic_account_id': self.analytic_account_id.id,
                    'project_site_id': self.project_site_id.id,
                    'type_id': self.type_id.id,
                    'location_id': self.location_id.id,
                })

        if incentives_received and self.incentives_received_type != 'rent_free':
            invoice_lines = [(0, 0, {
                'product_id': self.incentives_product_id.id,
                'name': self.incentives_product_id.name,
                'product_uom_id': self.incentives_product_id.uom_id.id,
                'account_id': self.incentives_product_id.product_tmpl_id.get_product_accounts()['expense'].id,
                'price_unit': incentives_received,
                'quantity': 1,
                'analytic_account_id': self.analytic_account_id.id,
                'project_site_id': self.project_site_id.id,
                'type_id': self.type_id.id,
                'location_id': self.location_id.id,
            })]
            invoice = self.env['account.move'].create({
                'partner_id': partner.id,
                'move_type': 'in_refund',
                'currency_id': self.leasee_currency_id.id,
                'ref': self.name,
                # 'invoice_date': datetime.now(),
                'invoice_date': self.commencement_date,
                'invoice_line_ids': invoice_lines,
                'journal_id': self.installment_journal_id.id,
                'leasee_contract_id': self.id,
                'auto_post': True,
            })
            line = invoice.line_ids.filtered(lambda l : l.account_id == partner.property_account_payable_id)
            if line:
                line.write({
                    'analytic_account_id': self.analytic_account_id.id,
                    'project_site_id': self.project_site_id.id,
                    'type_id': self.type_id.id,
                    'location_id': self.location_id.id,
                })

    def get_commencement_short_amount(self):
        total_amount = 0
        annual_ins = self.get_installments_per_year() or 1
        if self.payment_method == 'beginning':
            # installments = self.installment_ids.filtered(lambda i: 1 <= i.get_period_order() <= annual_ins)
            # for ins in installments:
            #     total_amount += (ins.amount - ins.subsequent_amount if ins else ins.amount)
            installment = self.installment_ids.filtered(lambda i: i.get_period_order() == 1 and not i.is_long_liability)
            total_amount = installment.amount - installment.subsequent_amount
            amount = total_amount
        else:
            installments = self.installment_ids.filtered(lambda i: 1 <= i.get_period_order() <= annual_ins and not i.is_long_liability)
            for ins in installments:
                total_amount += (ins.amount - ins.subsequent_amount)
            amount = total_amount
        return amount

    def create_commencement_move(self):
        rou_account = self.asset_model_id.account_asset_id
        short_lease_liability_amount = self.get_commencement_short_amount()
        short_lease_liability_amount = round(short_lease_liability_amount, 3)
        lines = [(0, 0, {
            'name': 'create contract number %s' % self.name,
            'account_id': rou_account.id,
            'credit': 0,
            'debit': self.rou_value - ( self.initial_direct_cost),
            'analytic_account_id': self.analytic_account_id.id,
            'project_site_id': self.project_site_id.id,
            'type_id': self.type_id.id,
            'location_id': self.location_id.id,
        }),(0, 0, {
            'name': 'create contract number %s' % self.name,
            'account_id': self.long_lease_liability_account_id.id or self.leasee_template_id.long_lease_liability_account_id.id,
            'debit': 0,
            'credit': self.lease_liability - short_lease_liability_amount,
            'analytic_account_id': self.analytic_account_id.id,
            'project_site_id': self.project_site_id.id,
            'type_id': self.type_id.id,
            'location_id': self.location_id.id,
        })]

        if short_lease_liability_amount or self.initial_payment_value:
            short_amount = short_lease_liability_amount + self.initial_payment_value
            lines.append((0, 0, {
            'name': 'create contract number %s' % self.name,
            'account_id': self.lease_liability_account_id.id,
            'debit': -short_amount if short_amount < 0 else 0,
            'credit': short_amount if short_amount > 0 else 0,
            'analytic_account_id': self.analytic_account_id.id,
            'project_site_id': self.project_site_id.id,
            'type_id': self.type_id.id,
            'location_id': self.location_id.id,
            }))

        if self.incentives_received and self.incentives_received_type != 'rent_free':
            lines.append( (0, 0, {
                'name': 'create contract number %s' % self.name,
                'account_id': self.incentives_account_id.id,
                'debit': self.incentives_received,
                'credit': 0,
                'analytic_account_id': self.analytic_account_id.id,
                'project_site_id': self.project_site_id.id,
                'type_id': self.type_id.id,
                'location_id': self.location_id.id,
            }) )

        if self.estimated_cost_dismantling:
            lines.append( (0, 0, {
                'name': 'create contract number %s' % self.name,
                'account_id': self.provision_dismantling_account_id.id,
                'debit': 0,
                'credit': self.estimated_cost_dismantling,
                'analytic_account_id': self.analytic_account_id.id,
                'project_site_id': self.project_site_id.id,
                'type_id': self.type_id.id,
                'location_id': self.location_id.id,
            }) )

        move = self.env['account.move'].create({
            'partner_id': self.vendor_id.id,
            'move_type': 'entry',
            'currency_id': self.leasee_currency_id.id,
            'ref': self.name,
            'date': self.commencement_date,
            # 'journal_id': self.asset_model_id.journal_id.id,
            'journal_id': self.initial_journal_id.id,
            'leasee_contract_id': self.id,
            'line_ids': lines,
            'auto_post': True,
        })
    # def create_commencement_move(self):
    #     rou_account = self.asset_model_id.account_asset_id
    #     lines = [(0, 0, {
    #         'name': 'create contract number %s' % self.name,
    #         'account_id': rou_account.id,
    #         'credit': 0,
    #         'debit': self.rou_value,
    #     }),(0, 0, {
    #         'name': 'create contract number %s' % self.name,
    #         'account_id': self.lease_liability_account_id.id,
    #         'debit': 0,
    #         'credit': self.lease_liability - self.incentives_received,
    #     }),(0, 0, {
    #         'name': 'create contract number %s' % self.name,
    #         'account_id': self.vendor_id.property_account_payable_id.id,
    #         'debit': 0,
    #         'credit': self.initial_direct_cost + self.initial_payment_value,
    #     }),(0, 0, {
    #         'name': 'create contract number %s' % self.name,
    #         'account_id': self.provision_dismantling_account_id.id,
    #         'debit': 0,
    #         'credit': self.estimated_cost_dismantling,
    #     })]
    #     move = self.env['account.move'].create({
    #         'partner_id': self.vendor_id.id,
    #         'move_type': 'entry',
    #         'currency_id': self.leasee_currency_id.id,
    #         'ref': self.name,
    #         'date': self.commencement_date,
    #         'journal_id': self.asset_model_id.journal_id.id,
    #         'leasee_contract_id': self.id,
    #         'line_ids': lines,
    #     })

    def get_annual_period(self, i):
        if self.is_contract_not_annual():
            res = math.floor(i / self.get_installments_per_year())
            return res
        else:
            return i

    def create_beginning_installments(self, remaining_lease_liability):
        # pr
        monthly_freq = {'1': 12, '3': 4, '6': 2}
        start = self.commencement_date
        # remaining_lease_liability = self.lease_liability - self.incentives_received
        # remaining_lease_liability = self.lease_liability
        num_installment = self.compute_installments_num()
        period_range = range(0, num_installment + 1)
        payment_months = self.payment_frequency * (1 if self.payment_frequency_type == 'months' else 12)
        remaining_advanced = self.initial_payment_value
        if self.incentives_received_type == 'rent_free':
            remaining_advanced += self.incentives_received
        increasement_frequency = self.increasement_frequency + 1
        if self.payment_frequency_type == 'months' and self.payment_frequency:
            if self.payment_frequency not in [1, 3, 6]:
                raise UserError(
                    _('Payment frequency for type months are quater: 3, semi: 6, and Monthly: 1'))
            increasement_frequency = (self.increasement_frequency *
                                      monthly_freq[
                                          '' + str(self.payment_frequency)]) + 1
        present_value = self.installment_amount
        amount = 0
        for i in period_range:
            if i != 1 and i != 0:
                new_start = start + relativedelta(months=(i - 1) * payment_months)
            else:
                new_start = start

            if i > 0:
                amount = self.get_future_value(present_value,
                                               self.increasement_rate,
                                               self.get_annual_period(i - 1), i,
                                               increasement_frequency)
                if i == increasement_frequency:
                    present_value = amount
            if remaining_advanced > 0:
                if amount <= remaining_advanced:
                    remaining_advanced -= amount
                    amount = 0
                else:
                    amount -= remaining_advanced
                    remaining_advanced = 0
            else:
                remaining_advanced = 0

            if i > 1:
                prev_start = start + relativedelta(months=(i - 2)* payment_months)
                period_ratio = ((new_start - prev_start).days)/ 365
                interest_recognition = remaining_lease_liability * ((1 + self.interest_rate / 100) ** period_ratio - 1)
            else:
                interest_recognition = 0

            remaining_lease_liability -= (amount - interest_recognition)
            if increasement_frequency > 1:
                if i == increasement_frequency:
                    if self.payment_frequency_type == 'months' and self.payment_frequency:
                        if self.payment_frequency not in [1, 3, 6]:
                            raise UserError(
                                _('Payment frequency for type months are quater: 3, semi: 6, and Monthly: 1'))
                        increasement_frequency += self.increasement_frequency * \
                                                  monthly_freq['' + str(
                                                      self.payment_frequency)]
                    else:
                        increasement_frequency += self.increasement_frequency
            if i == 0:
                journals = self.env['account.move'].search(
                    [('leasee_contract_id',
                      '=', self.id), ('date', '=', self.commencement_date)])
                if journals:
                    amount = journals.amount_total_signed

            self.env['leasee.installment'].create({
                'name': self.name + ' installment - ' + new_start.strftime(DF),
                'period': i,
                'amount': amount,
                'date': new_start,
                'leasee_contract_id': self.id,
                'subsequent_amount': interest_recognition,
                'remaining_lease_liability': remaining_lease_liability,
            })

    def create_end_installments(self, remaining_lease_liability):
        monthly_freq = {'1': 12, '3': 4, '6': 2}
        # remaining_lease_liability = self.lease_liability
        amount_advance = 0
        journals = self.env['account.move'].search(
            [('leasee_contract_id',
              '=', self.id), ('date', '=', self.commencement_date)])
        if journals:
            amount_advance = journals.amount_total_signed
        payment_months = self.payment_frequency * (
            1 if self.payment_frequency_type == 'months' else 12)
        self.env['leasee.installment'].create({
            'name': self.name + ' installment - ' + self.commencement_date.strftime(DF),
            'period': 0,
            'amount': amount_advance if amount_advance else 0,
            # 'date': self.commencement_date + relativedelta(months=payment_months, days=-1),
            'date': self.commencement_date,
            'leasee_contract_id': self.id,
            'subsequent_amount': 0,
            'remaining_lease_liability': remaining_lease_liability,
        })

        start = self.commencement_date
        # remaining_lease_liability = self.lease_liability
        num_installment = self.compute_installments_num()
        period_range = range(1, num_installment + 1)
        remaining_advanced = self.initial_payment_value
        if self.incentives_received_type == 'rent_free':
            remaining_advanced += self.incentives_received
        increasement_frequency = self.increasement_frequency + 1
        if self.payment_frequency_type == 'months' and self.payment_frequency:
            if str(self.payment_frequency) not in [1, 3, 6]:
                raise UserError(
                    _('Payment frequency for type months are quater: 3, semi: 6, and Monthly: 1'))
            increasement_frequency = (self.increasement_frequency *
                                      monthly_freq[
                                          '' + str(self.payment_frequency)]) + 1
        present_value = self.installment_amount
        for i in period_range:
            amount = self.get_future_value(present_value,
                                           self.increasement_rate,
                                           self.get_annual_period(i - 1), i,
                                           increasement_frequency)
            if i == increasement_frequency:
                present_value = amount

            if remaining_advanced > 0:
                if amount <= remaining_advanced:
                    remaining_advanced -= amount
                    amount = 0
                else:
                    amount -= remaining_advanced
                    remaining_advanced = 0

            new_start = start + relativedelta(months=i*payment_months)
            prev_start = start + relativedelta(months=(i - 1) * payment_months)
            period_ratio = ((new_start - prev_start).days) / 365
            interest_recognition = remaining_lease_liability * ((1 + self.interest_rate / 100) ** period_ratio - 1)
            remaining_lease_liability -= (amount - interest_recognition)
            if increasement_frequency > 1:
                if i == increasement_frequency:
                    if self.payment_frequency_type == 'months' and self.payment_frequency:
                        if self.payment_frequency not in [1, 3, 6]:
                            raise UserError(
                                _('Payment frequency for type months are quater: 3, semi: 6, and Monthly: 1'))
                        increasement_frequency += self.increasement_frequency * \
                                                  monthly_freq['' + str(
                                                      self.payment_frequency)]
                    else:
                        increasement_frequency += self.increasement_frequency
            self.env['leasee.installment'].create({
                'name': self.name + ' installment - ' + new_start.strftime(DF),
                'period': i,
                'amount': amount,
                'date': new_start,
                'leasee_contract_id': self.id,
                'subsequent_amount': interest_recognition,
                'remaining_lease_liability': remaining_lease_liability,
            })

    def create_installments(self, remaining_lease_liability):
        if self.payment_method == 'beginning':
            self.create_beginning_installments(remaining_lease_liability)
        else:
            self.create_end_installments(remaining_lease_liability)

    def create_subsequent_measurement_move(self, date):
        amount = self.remaining_lease_liability * self.interest_rate / (100 * 12)
        if amount:
            lines = [(0, 0, {
                'name': 'Interest Recognition for %s' % date.strftime(DF),
                'account_id': self.lease_liability_account_id.id,
                'debit': 0,
                'credit': amount,
                'analytic_account_id': self.analytic_account_id.id,
                'project_site_id': self.project_site_id.id,
                'type_id': self.type_id.id,
                'location_id': self.location_id.id,
            }),(0, 0, {
                'name': 'Interest Recognition for %s' % date.strftime(DF),
                'account_id': self.interest_expense_account_id.id,
                'debit': amount,
                'credit': 0,
                'analytic_account_id': self.analytic_account_id.id,
                'project_site_id': self.project_site_id.id,
                'type_id': self.type_id.id,
                'location_id': self.location_id.id,
            })]
            move = self.env['account.move'].create({
                'partner_id': self.vendor_id.id,
                'move_type': 'entry',
                'currency_id': self.leasee_currency_id.id,
                'ref': self.name,
                'date': date,
                'journal_id': self.asset_model_id.journal_id.id,
                'leasee_contract_id': self.id,
                'line_ids': lines,
                'auto_post': True,
            })

    def action_create_payment(self):
        if self.state != 'draft' and self.asset_id and self.asset_id.state != 'draft':
            raise ValidationError(_('The Related Asset is already running and its value can not be changed'))

        context = {
            'default_is_leasee_payment': True,
            'default_leasee_contract_id': self.id,
            'default_lease_contract_id': self.id,
            'default_partner_id': self.vendor_id.id,
            'default_payment_type': 'outbound',
            'default_partner_type': 'supplier',
        }
        view_form = {
            'name': _('Contract Payment'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.payment',
            'type': 'ir.actions.act_window',
            'context': context,
        }

        return view_form

    def action_open_journal_entries(self):
        domain = [('id', 'in', self.account_move_ids.ids),('move_type', '=', 'entry')]
        view_tree = {
            'name': _(' Journal Entries '),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'type': 'ir.actions.act_window',
            'domain': domain,
        }

        return view_tree

    def action_open_bills(self):
        domain = [('id', 'in', self.account_move_ids.ids), ('move_type', 'in', ['in_invoice', 'in_refund'])]
        view_tree = {
            'name': _(' Vendor Bills '),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'type': 'ir.actions.act_window',
            'domain': domain,
        }

        return view_tree

    def action_open_payments(self):
        domain = [('id', 'in', self.payment_ids.ids)]
        view_tree = {
            'name': _(' Payments '),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.payment',
            'type': 'ir.actions.act_window',
            'domain': domain,
        }

        return view_tree

    @api.depends('payment_ids')
    def compute_initial_payment_value(self):
        for rec in self:
            payments = rec.payment_ids.filtered(lambda p: p.is_leasee_payment)
            total_payments = sum(payments.mapped('amount'))
            rec.initial_payment_value = total_payments

    def action_terminate(self):
        today = date.today()
        diff_delta = today - self.commencement_date
        if self.lease_contract_period_type == 'months':
            diff = diff_delta.days / 30
        else:
            diff = diff_delta.days / 365.25
        if diff < self.terminate_month_number:
            raise ValidationError(_('Contract can not be terminated before the period number %s' %self.terminate_month_number) )

        return self.asset_id.action_set_to_close()

        # self.process_termination()
        # view_form = {
        #     'name': _('Dispose Asset and terminate contract'),
        #     'view_type': 'form',
        #     'view_mode': 'form',
        #     'res_model': 'account.payment',
        #     'type': 'ir.actions.act_window',
        #     'target': 'new',
        # }
        # return view_form

    def get_interest_amount_termination_amount(self, termination_date):
        current_installment = self.installment_ids.filtered(lambda i: i.date > termination_date)[0]
        prev_installment = self.installment_ids.filtered(lambda i: i.get_period_order() == current_installment.get_period_order() - 1)
        start_month = termination_date.replace(day=1)
        ratio = ((termination_date - start_month).days + 1) / ((current_installment.date - prev_installment.date).days)
        amount = ratio * current_installment.subsequent_amount
        return amount

    def process_termination(self):
        leasee_moves = self.env['account.move'].search([('leasee_contract_id', '=', self.id),('asset_id', '=', False)])
        moves_after_terminate = leasee_moves.filtered(lambda m: m.date >= date.today())
        for move in moves_after_terminate:
            if move.date > date.today():
                move.button_draft()
                move.button_cancel()
            else:
                accounts = move.line_ids.mapped('account_id')
                expense_account = self.interest_expense_account_id
                if expense_account not in accounts:
                    move.button_draft()
                    move.button_cancel()
        self.create_termination_fees()
        self.state = 'terminated'

    def create_termination_fees(self):
        amount = self.terminate_fine
        if self.leasor_type == 'single':
            self.create_termination_fees_bill( amount, self.vendor_id)
        else:
            for leasor in self.multi_leasor_ids:
                partner = leasor.partner_id
                leasor_amount = ( leasor.amount / self.installment_amount) * amount if leasor.type == 'amount' else leasor.percentage * amount / 100
                self.create_termination_fees_bill(leasor_amount, partner)

    def create_termination_fees_bill(self, amount, partner):
        invoice_lines = [(0, 0, {
            'product_id': self.terminate_product_id.id,
            'name': self.terminate_product_id.name,
            'product_uom_id': self.terminate_product_id.uom_id.id,
            'account_id': self.terminate_product_id.product_tmpl_id.get_product_accounts()['expense'].id,
            'price_unit': amount,
            'quantity': 1,
            'analytic_account_id': self.analytic_account_id.id,
            'project_site_id': self.project_site_id.id,
            'type_id': self.type_id.id,
            'location_id': self.location_id.id,
        })]
        invoice = self.env['account.move'].create({
            'partner_id': partner.id,
            'move_type': 'in_invoice',
            'currency_id': self.leasee_currency_id.id,
            'ref': self.name + ' Terminate Fine',
            'invoice_date': datetime.today(),
            'invoice_line_ids': invoice_lines,
            'journal_id': self.installment_journal_id.id,
            'leasee_contract_id': self.id,
            'auto_post': True,
        })
        line = invoice.line_ids.filtered(lambda l: l.account_id == self.vendor_id.property_account_payable_id)
        if line:
            line.write({
                'analytic_account_id': self.analytic_account_id.id,
                'project_site_id': self.project_site_id.id,
                'type_id': self.type_id.id,
                'location_id': self.location_id.id,
            })

    @api.model
    def leasee_expiration_notification(self):
        lease_notification_period = int(self.env['ir.config_parameter'].get_param('lease_notification_period'))
        start_notification_date = fields.Date.today() + relativedelta(days=lease_notification_period)
        contracts = self.search([
            ('expired_notified', '!=', True),
        ]).filtered(lambda l: l.estimated_ending_date <= start_notification_date)
        for contract in contracts:
            contract.activity_schedule(
                'lease_management.mail_activity_type_alert_date_expiration_reached',
                user_id=SUPERUSER_ID,
                note=_("The alert date for this contract has been reached")
            )
            contract.expired_notified = True

    @api.model
    def leasee_action_expired(self):
        leasee_contracts = self.search([]).filtered(lambda rec: rec.estimated_ending_date <= fields.Date.today() and rec.state != 'extended')
        for contract in leasee_contracts:
            contract.state = 'expired'

    @api.model
    def leasee_action_generate_installments_entries(self):
        instalments = self.env['leasee.installment'].search([
            ('installment_invoice_id','=', False),
            ('leasee_contract_id','!=', False),
            ('period', '>', 0),
        # ]).filtered(lambda rec: rec.date <= date.today())
        ])
        for install in instalments:
            contract = install.leasee_contract_id
            if install.amount > 0:
                if contract.leasor_type == 'single':
                    self.create_installment_bill(contract, install, contract.vendor_id, install.amount)
                else:
                    for leasor in contract.multi_leasor_ids:
                        partner = leasor.partner_id
                        amount = (leasor.amount / contract.installment_amount) * install.amount if leasor.type == 'amount' else leasor.percentage * install.amount / 100
                        self.create_installment_bill(contract, install, partner, amount)

    def create_installment_bill(self, contract, install, partner, amount):
        invoice_lines = [(0, 0, {
            'product_id': contract.installment_product_id.id,
            'name': contract.installment_product_id.name,
            'product_uom_id': contract.installment_product_id.uom_id.id,
            'account_id': contract.installment_product_id.product_tmpl_id.get_product_accounts()['expense'].id,
            'price_unit': amount,
            'quantity': 1,
            'analytic_account_id': contract.analytic_account_id.id,
            'project_site_id': contract.project_site_id.id,
            'type_id': contract.type_id.id,
            'location_id': contract.location_id.id,
            'tax_ids': [(4, tax_id) for tax_id in contract.installment_product_id.taxes_id.ids],
        })]
        invoice = self.env['account.move'].create({
            'partner_id': partner.id,
            'move_type': 'in_invoice',
            'currency_id': contract.leasee_currency_id.id,
            'ref': contract.name + ' - ' + install.date.strftime('%d/%m/%Y'),
            'invoice_date': install.date,
            'invoice_line_ids': invoice_lines,
            'journal_id': contract.installment_journal_id.id,
            'leasee_contract_id': contract.id,
            'auto_post': True,
        })
        line = invoice.line_ids.filtered(lambda l: l.account_id == partner.property_account_payable_id)
        if line:
            line.write({
                'analytic_account_id': contract.analytic_account_id.id,
                'project_site_id': contract.project_site_id.id,
                'type_id': contract.type_id.id,
                'location_id': contract.location_id.id,
            })
        install.installment_invoice_id = invoice.id

    def get_end_month(self, ins_date):
        start_month = ins_date.replace(day=1)
        end_month = start_month + relativedelta(months=1,days=-1)
        return end_month

    def leasee_action_generate_interest_entries(self, start_date):
        for contract in self:
            delta = contract.payment_frequency * (1 if contract.payment_frequency_type == 'months' else 12)
            instalments = self.env['leasee.installment'].search([
                ('leasee_contract_id', '=', contract.id),
            ]).filtered(lambda i: i.date >= start_date)
            for i, installment in enumerate(instalments):
                if installment.subsequent_amount:
                    if not contract.prorata:
                        if contract.payment_method == 'beginning':
                            supposed_dates = [installment.date + relativedelta(months=i,days=-1) for i in range(1, delta+1) ]
                        else:
                            supposed_dates = [installment.date - relativedelta(months=i) for i in range(delta)]

                        for n_date in supposed_dates:
                            interest_amount = installment.subsequent_amount / delta
                            contract.create_interset_move(installment, n_date, interest_amount)

                    else:
                        ins_period = installment.get_period_order()
                        interest_amount = installment.subsequent_amount
                        installment_date = installment.date
                        start_of_month = installment_date.replace(day=1)
                        end_of_month = start_of_month + relativedelta(months=1, days=-1)
                        remaining_of_month = (end_of_month - installment_date).days + 1
                        month_days = (end_of_month - start_of_month).days + 1

                        prev_install = contract.installment_ids.filtered(lambda i: i.get_period_order() == (ins_period - 1) and i.get_period_order() >= 1)
                        # if prev_install.is_advance:
                        #     prev_install = contract.installment_ids.filtered(lambda i: i.get_period_order() == (ins_period - 2) and i.get_period_order() >= 1)
                        prev_interest = prev_install.subsequent_amount if prev_install and prev_install.amount else 0

                        supposed_dates = [self.get_end_month(end_of_month - relativedelta(months=i)) for i in range(1, delta + 1)]
                        num_days = ( installment.date - (installment.date - relativedelta(months=delta))).days
                        num_days = (installment.date - prev_install.date).days if prev_install else num_days

                        for n_date in supposed_dates:
                            if n_date >= start_date:
                                # if contract.commencement_date.month == n_date.month:
                                if (ins_period == 1 and contract.commencement_date.month == n_date.month) or (prev_install and prev_install.date.month == n_date.month):
                                    start_month = n_date.replace(day=1)
                                    if prev_install:
                                        remaining_of_month = (n_date - prev_install.date).days + 1
                                        prev_num_days = (prev_install.date - (prev_install.date - relativedelta(months=delta))).days
                                        before_prev_install = self.installment_ids.filtered(lambda i: i.get_period_order() == ins_period - 2)
                                        prev_num_days = (prev_install.date - before_prev_install.date).days if before_prev_install and before_prev_install.get_period_order() else prev_num_days
                                    else:
                                        remaining_of_month = (n_date - contract.commencement_date).days + 1
                                        prev_num_days = 1
                                    month_days = (n_date - start_month).days + 1
                                    current_amount = interest_amount * remaining_of_month / num_days
                                    previous_amount = prev_interest * (month_days - remaining_of_month) / prev_num_days
                                    amount = current_amount
                                    if not prev_install.amount and prev_install.subsequent_amount:
                                        previous_amount = prev_install.subsequent_amount * (month_days - remaining_of_month) / prev_num_days
                                        contract.create_interset_move(prev_install, prev_install.date + relativedelta(days=-1), previous_amount)
                                    elif previous_amount and installment_date != start_date:
                                        contract.create_interset_move(prev_install, prev_install.date + relativedelta(days=-1), previous_amount)
                                else:
                                    start = n_date.replace(day=1)
                                    amount = interest_amount * ((n_date - start).days + 1) / num_days
                                contract.create_interset_move(installment, n_date, amount)
                        if installment.get_period_order() == len(contract.installment_ids) - 1 and end_of_month >= start_date:
                            amount = interest_amount * (month_days - remaining_of_month) / num_days
                            contract.create_interset_move(installment, end_of_month, amount)

    def leasee_action_generate_interest_entries_reassessment(self, start_date):
        for contract in self:
            delta = contract.payment_frequency * (1 if contract.payment_frequency_type == 'months' else 12)
            instalments = self.env['leasee.installment'].search([
                ('leasee_contract_id', '=', contract.id),
            ]).filtered(lambda i: i.date >= start_date)
            for i, installment in enumerate(instalments):
                if installment.subsequent_amount:
                    ins_period = installment.get_period_order()
                    interest_amount = installment.subsequent_amount
                    installment_date = installment.date
                    start_of_month = installment_date.replace(day=1)
                    end_of_month = start_of_month + relativedelta(months=1, days=-1)
                    remaining_of_month = (end_of_month - installment_date).days + 1
                    month_days = (end_of_month - start_of_month).days + 1

                    prev_install = contract.installment_ids.filtered(lambda i: i.get_period_order() == (ins_period - 1) and i.get_period_order() >= 1)
                    prev_interest = prev_install.subsequent_amount if prev_install and prev_install.amount else 0

                    supposed_dates = [self.get_end_month(end_of_month - relativedelta(months=i)) for i in range(1, delta + 1)]
                    num_days = ( installment.date - (installment.date - relativedelta(months=delta))).days
                    num_days = (installment.date - prev_install.date).days if prev_install else num_days

                    for n_date in supposed_dates:
                        if (ins_period == 1 and contract.commencement_date.month == n_date.month) or (prev_install and prev_install.date.month == n_date.month):
                            start_month = n_date.replace(day=1)
                            if prev_install:
                                remaining_of_month = (n_date - prev_install.date).days + 1
                                prev_num_days = (prev_install.date - (prev_install.date - relativedelta(months=delta))).days
                                before_prev_install = self.installment_ids.filtered(lambda i: i.get_period_order() == ins_period - 2)
                                prev_num_days = (prev_install.date - before_prev_install.date).days if before_prev_install and before_prev_install.get_period_order() else prev_num_days
                            else:
                                remaining_of_month = (n_date - contract.commencement_date).days + 1
                                prev_num_days = 1
                            month_days = (n_date - start_month).days + 1
                            current_amount = interest_amount * remaining_of_month / num_days
                            previous_amount = prev_interest * (month_days - remaining_of_month) / prev_num_days
                            amount = current_amount
                            if not prev_install.amount and prev_install.subsequent_amount:
                                previous_amount = prev_install.subsequent_amount * (month_days - remaining_of_month) / prev_num_days
                                contract.create_interset_move(prev_install, prev_install.date + relativedelta(days=-1), previous_amount)
                            elif previous_amount and installment_date != start_date:
                                contract.create_interset_move(prev_install, prev_install.date + relativedelta(days=-1), previous_amount)
                        else:
                            start = n_date.replace(day=1)
                            amount = interest_amount * ((n_date - start).days + 1) / num_days
                        contract.create_interset_move(installment, n_date, amount)
                    if installment.get_period_order() == len(contract.installment_ids) - 1:
                        amount = interest_amount * (month_days - remaining_of_month) / num_days
                        contract.create_interset_move(installment, end_of_month, amount)

    def create_interset_move(self, installment, move_date, interest_amount):
        if round(interest_amount, 3) > 0:
            # lease_account_id = self.lease_liability_account_id.id if (installment.amount or not installment or self._context.get('use_short') or (self._context.get('reassessment') and not installment.is_long_liability)) else self.long_lease_liability_account_id.id
            lease_account_id = self.lease_liability_account_id.id if (installment.amount or not installment or self._context.get('use_short') or not installment.is_long_liability) else self.long_lease_liability_account_id.id
            lines = [(0, 0, {
                'name': 'Interest Recognition for %s' % move_date.strftime(DF),
                'account_id': lease_account_id,
                'debit': 0,
                'credit': interest_amount,
                'analytic_account_id': self.analytic_account_id.id,
                'project_site_id': self.project_site_id.id,
                'type_id': self.type_id.id,
                'location_id': self.location_id.id,
            }),(0, 0, {
                'name': 'Interest Recognition for %s' % move_date.strftime(DF),
                'account_id': self.interest_expense_account_id.id,
                'debit': interest_amount,
                'credit': 0,
                'analytic_account_id': self.analytic_account_id.id,
                'project_site_id': self.project_site_id.id,
                'type_id': self.type_id.id,
                'location_id': self.location_id.id,
            })]
            move = self.env['account.move'].create({
                'partner_id': self.vendor_id.id,
                'move_type': 'entry',
                'currency_id': self.leasee_currency_id.id,
                'ref': self.name,
                'date': move_date,
                'journal_id': self.asset_model_id.journal_id.id,
                'leasee_contract_id': self.id,
                'line_ids': lines,
                'leasee_installment_id': installment.id,
                'auto_post': True,
            })
            return move

    def action_open_extended_contract(self):
        contracts = self.search([('id', 'in', self.child_ids.ids)])
        if len(contracts) > 1:
            domain = [('id', 'in', contracts.ids)]
            view_tree = {
                'name': _('Extended Leasee Contracts'),
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': self._name,
                'type': 'ir.actions.act_window',
                'domain': domain,
            }

            return view_tree
        else:
            view_form = {
                'name': _('Extended Leasee Contract'),
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': self._name,
                'type': 'ir.actions.act_window',
                'res_id': contracts[0].id,
            }

            return view_form

    def get_installment_entry_amount(self, installment):
        install_period = installment.get_period_order()
        installments_per_year = self.get_installments_per_year()
        if self.payment_method == 'beginning':
            # if self.is_contract_not_annual():
            #     next_installment = self.installment_ids.filtered(lambda i: i.get_period_order() == (install_period + installments_per_year) and i.get_period_order() > 1)
            #     current_installment = self.installment_ids.filtered(lambda i: i.get_period_order() == (install_period + installments_per_year - 1) and i.get_period_order() > 1)
            #     amount = next_installment.amount - current_installment.subsequent_amount if install_period >= 1 else 0
            # else:
            if install_period == 1:
                installments = self.installment_ids.filtered(lambda i: i.amount and i.get_period_order() <= (installments_per_year + 1) and i.get_period_order() > 1)
                amount = sum([ins.amount - ins.subsequent_amount for ins in installments])

            elif install_period > 1:
                next_installment = self.installment_ids.filtered(lambda i: i.amount and i.get_period_order() == (install_period + installments_per_year) and i.get_period_order() > 1)
                amount = next_installment.amount - next_installment.subsequent_amount if install_period > 1 and next_installment else 0
            else:
                amount = 0
        else:
            if install_period >= installments_per_year and installment.amount:
                # prev_installment = self.installment_ids.filtered(lambda i: i.get_period_order() == (install_period -1) and i.get_period_order() > 1)
                amount = installment.amount - installment.subsequent_amount
            else:
                amount = 0
        return amount

    def create_installment_single_entry(self, installment, amount):
        if round(abs(amount), 3) > 0:
            lines = [(0, 0, {
                'name': installment.name + ' Installment Entry',
                'account_id': self.long_lease_liability_account_id.id or self.leasee_template_id.long_lease_liability_account_id.id,
                'debit': amount if amount > 0 else 0,
                'credit': -amount if amount < 0 else 0,
                'analytic_account_id': self.analytic_account_id.id,
                'project_site_id': self.project_site_id.id,
                'type_id': self.type_id.id,
                'location_id': self.location_id.id,
            }),
             (0, 0, {
                 'name': installment.name + ' Installment Entry',
                 'account_id': self.lease_liability_account_id.id,
                 'credit': amount if amount > 0 else 0,
                 'debit': -amount if amount < 0 else 0,
                 'analytic_account_id': self.analytic_account_id.id,
                 'project_site_id': self.project_site_id.id,
                 'type_id': self.type_id.id,
                 'location_id': self.location_id.id,
             })]
            move = self.env['account.move'].create({
                'move_type': 'entry',
                'currency_id': self.leasee_currency_id.id,
                'ref': installment.name + ' Installment Entry',
                'date': installment.date,
                'journal_id': self.initial_journal_id.id,
                'leasee_contract_id': self.id,
                'leasee_installment_id': installment.id,
                'is_installment_entry': True,
                'line_ids': lines,
                'auto_post': True,
            })

    def create_contract_installment_entries(self, start_date):
        installments_count = len(self.installment_ids) - 1
        if not self.is_contract_not_annual():
            if self.payment_method == 'beginning':
                for installment in self.installment_ids.filtered(lambda i: i.date >= start_date):
                    amount = self.get_installment_entry_amount(installment)
                    if abs(amount) != 0 and not installment.is_advance:
                        self.create_installment_single_entry(installment, amount)
            else:
                for installment in self.installment_ids.filtered(lambda i: i.date >= start_date and i.get_period_order() > 0):
                    period = installment.get_period_order()
                    current_installment = self.installment_ids.filtered(
                        lambda i: i.get_period_order() <= installments_count and i.get_period_order() == (period + 1))
                    if current_installment:
                        amount = self.get_installment_entry_amount(current_installment)
                        if abs(amount) != 0 and not installment.is_advance:
                            self.create_installment_single_entry(installment, amount)
        else:
            installments_per_year = self.get_installments_per_year()
            if self.payment_method == 'beginning':
                for installment in self.installment_ids.filtered(lambda i: i.date >= start_date and i.get_period_order() > 0):
                    period = installment.get_period_order()
                    current_installment = installment
                    if current_installment:
                        amount = self.get_installment_entry_amount(current_installment)
                        if abs(amount) != 0 and not installment.is_advance:
                            self.create_installment_single_entry(installment, amount)
            else:
                for installment in self.installment_ids.filtered(lambda i: i.date >= start_date and i.get_period_order() > 0):
                    period = installment.get_period_order()
                    current_installment = self.installment_ids.filtered(lambda i: i.get_period_order() <= installments_count and i.get_period_order() == (period + installments_per_year))
                    if current_installment:
                        amount = self.get_installment_entry_amount(current_installment)
                        if abs(amount) != 0 and not installment.is_advance:
                            self.create_installment_single_entry(installment, amount)

    @api.model
    def create_installment_entry(self):
        installments_before_today = self.env['leasee.installment'].search(
            [('leasee_contract_id.state', '=', 'active')]
        ).filtered(lambda i: i.date <= fields.date.today() and i.get_period_order() > 0)

        installment_moves = self.env['account.move'].search([
            ('is_installment_entry', '=', True),
            ('state', '=', 'posted'),
        ]).filtered(lambda i: i.date <= fields.date.today())

        installments_with_done_moves = installment_moves.mapped('leasee_installment_id')
        installments_without_moves = installments_before_today - installments_with_done_moves

        for installment in installments_without_moves:
            contract = installment.leasee_contract_id
            amount = contract.get_installment_entry_amount(installment)
            if amount:
                contract.create_installment_single_entry(installment, amount)
                
    # Reassessment 
    @api.model
    def create_reassessment_move(self, contract, amount, reassessment_date):
        rou_account = contract.asset_model_id.account_asset_id
        if amount:
            lines = [(0, 0, {
                'name': 'Reassessment contract number %s' % contract.name,
                'account_id': rou_account.id,
                'credit': -amount if amount < 0 else 0,
                'debit': amount if amount > 0 else 0,
                'analytic_account_id': contract.analytic_account_id.id,
                'project_site_id': contract.project_site_id.id,
                'type_id': contract.type_id.id,
                'location_id': contract.location_id.id,
            }), (0, 0, {
                'name': 'Reassessment contract number %s' % contract.name,
                # 'account_id': contract.lease_liability_account_id.id,
                'account_id': contract.long_lease_liability_account_id.id,
                'debit': -amount if amount < 0 else 0,
                'credit': amount if amount > 0 else 0,
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
                'date': reassessment_date,
                'journal_id': contract.asset_model_id.journal_id.id,
                'leasee_contract_id': contract.id,
                'line_ids': lines,
                'auto_post': True,
            })

    def update_reassessment_asset_value(self, new_value, reassessment_date):
        asset = self.asset_id
        self.env['asset.modify'].create({
            'name': "Reassessment Leasee Contract",
            'date': reassessment_date,
            'asset_id': asset.id,
            'value_residual': new_value,
            'salvage_value': asset.salvage_value,
            "account_asset_counterpart_id": self.lease_liability_account_id.id,
        }).with_context(reasset_leasee_contract=True).modify()

    def update_reassessment_related_journal_items(self, installments_to_modify, old_installments_data=None, reassessment_date=None):
        installments_to_modify = installments_to_modify.sorted(key= lambda i: i.date)
        for i, ins in enumerate(installments_to_modify):
            new_date = None
            if old_installments_data:
                old_date = old_installments_data[ins.id]['date'] if ins.id in old_installments_data else None
                if old_date != ins.date:
                    new_date = ins.date
            if self.leasor_type == 'single':
                invoice = ins.installment_invoice_id
                self.update_reassessment_invoice_amount(invoice, ins.amount, new_date)
            else:
                for ml in self.multi_leasor_ids:
                    invoice = self.account_move_ids.filtered(lambda inv: inv.move_type == 'in_invoice' and ml.partner_id == inv.partner_id and ins.date == inv.date)
                    amount = (ml.amount / self.installment_amount) * ins.amount if ml.type == 'amount' else ml.percentage * ins.amount / 100
                    if invoice:
                        self.update_reassessment_invoice_amount(invoice, amount, new_date)
            if i:
                if reassessment_date:
                    ins.interest_move_ids.filtered(lambda m: m.date > reassessment_date).sudo().with_context(force_delete=True).unlink()
                else:
                    ins.interest_move_ids.sudo().unlink()
        if self._context.get('reassessment'):
            modify_date = installments_to_modify[0].date
        else:
            modify_date = installments_to_modify[1].date

        self.create_contract_installment_entries(modify_date)
        self.leasee_action_generate_interest_entries(modify_date)

    def update_reassessment_invoice_amount(self, invoice, new_amount, new_date=None):
        inv_state = invoice.state
        if invoice:
            if inv_state == 'posted':
                invoice.button_draft()

            invoice_line = invoice.invoice_line_ids
            new_invoice = invoice.new(invoice._convert_to_write(invoice._cache))
            if new_date:
                new_invoice.update({
                    'date': new_date,
                    'invoice_date': new_date,
                })
            line_values = {
                'product_id': invoice_line.product_id.id,
                'account_id': invoice_line.account_id.id,
                'analytic_account_id': invoice_line.analytic_account_id.id,
                'project_site_id': invoice_line.project_site_id.id,
                'type_id': invoice_line.type_id.id,
                'location_id': invoice_line.location_id.id,
                'tax_ids': [(4, tax_id) for tax_id in invoice_line.tax_ids.ids],
            }
            new_invoice.invoice_line_ids = [(5,), (0, 0, line_values)]
            new_invoice.invoice_line_ids.update({'price_unit': new_amount})
            new_invoice.invoice_line_ids._onchange_price_subtotal()

            new_invoice._compute_invoice_taxes_by_group()
            new_invoice._onchange_invoice_line_ids()
            new_invoice._compute_amount()
            values = new_invoice._convert_to_write(new_invoice._cache)
            if new_date:
                invoice.write({
                    'date': new_date,
                    'invoice_date': new_date,
                })
            invoice.write({'line_ids': values.get('line_ids')})

            if inv_state == 'posted':
                invoice.action_post()

    def update_reassessment_first_installment_entries(self, first_installment, old_subsequent, days_after_reassessment, days, reassessment_date):
        interest_move_accounts = [self.interest_expense_account_id.id, self.lease_liability_account_id.id]
        beginning_entries = first_installment.interest_move_ids.filtered(lambda
                                                                             m: m.date.month == reassessment_date.month and m.date.year == reassessment_date.year)
        after_reassessment_moves = first_installment.interest_move_ids.filtered(
            lambda m: m.date > reassessment_date and set(m.line_ids.mapped('account_id').ids) == set(
                interest_move_accounts))
        beginning_interest_move = beginning_entries.filtered(
            lambda m: set(m.line_ids.mapped('account_id').ids) == set(interest_move_accounts))
        if beginning_interest_move:
            after_reassessment_moves -= beginning_interest_move
            debit_line = beginning_interest_move.line_ids.filtered(lambda l: l.debit > 0)
            credit_line = beginning_interest_move.line_ids.filtered(lambda l: l.credit > 0)
            start_month = beginning_interest_move.date.replace(day=1)
            end_month = start_month + relativedelta(months=1, days=-1)
            prev_start = start_month
            prev_installment = self.installment_ids.filtered(
                lambda i: i.get_period_order() == first_installment.get_period_order() - 1)
            if prev_installment.date.month == reassessment_date.month and prev_installment.date.year == reassessment_date.year:
                prev_start = prev_installment.date
            interest_amount = old_subsequent * (
                        reassessment_date - prev_start).days / days + first_installment.subsequent_amount * (
                                          (end_month - reassessment_date).days + 1) / days_after_reassessment
            beginning_interest_move.write({'line_ids': [(1, debit_line.id, {'debit': interest_amount}),
                                                        (1, credit_line.id, {'credit': interest_amount})]})

        for move in after_reassessment_moves:
            debit_line = move.line_ids.filtered(lambda l: l.debit > 0)
            credit_line = move.line_ids.filtered(lambda l: l.credit > 0)
            start_month = move.date.replace(day=1)
            end_month = start_month + relativedelta(months=1, days=-1)
            if first_installment.date.month == move.date.month and first_installment.date.year == move.date.year:
                interest_amount = first_installment.subsequent_amount * (
                            first_installment.date - start_month).days / days_after_reassessment
            else:
                interest_amount = first_installment.subsequent_amount * (
                            (end_month - start_month).days + 1) / days_after_reassessment
            move.write({'line_ids': [(1, debit_line.id, {'debit': interest_amount}),
                                     (1, credit_line.id, {'credit': interest_amount})]})
        lease_liability_accounts = [self.long_lease_liability_account_id.id, self.lease_liability_account_id.id]
        amount = self.get_reassessment_installment_entry_amount(first_installment)
        if amount:
            installment_entry = first_installment.interest_move_ids.filtered(
                lambda m: set(m.line_ids.mapped('account_id').ids) == set(lease_liability_accounts))
            debit_line = installment_entry.line_ids.filtered(lambda l: l.debit > 0)
            credit_line = installment_entry.line_ids.filtered(lambda l: l.credit > 0)
            installment_entry.write(
                {'line_ids': [(1, debit_line.id, {'debit': amount}), (1, credit_line.id, {'credit': amount})]})

    def get_reassessment_installment_entry_amount(self, installment):
        installments_count = len(self.installment_ids) - 1
        if not self.is_contract_not_annual():
            if self.payment_method == 'beginning':
                amount = self.get_installment_entry_amount(installment)
            else:
                period = installment.get_period_order()
                current_installment = self.installment_ids.filtered(
                    lambda i: i.get_period_order() <= installments_count and i.get_period_order() == (period + 1))
                if current_installment:
                    amount = self.get_installment_entry_amount(current_installment)
                else:
                    amount = 0
        else:
            installments_per_year = self.get_installments_per_year()
            if self.payment_method == 'beginning':
                period = installment.get_period_order()
                current_installment = installment
                if current_installment:
                    amount = self.get_installment_entry_amount(current_installment)
                else:
                    amount = 0
            else:
                period = installment.get_period_order()
                current_installment = self.installment_ids.filtered(
                    lambda i: i.get_period_order() <= installments_count and i.get_period_order() == (
                                period + installments_per_year))
                if current_installment:
                    amount = self.get_installment_entry_amount(current_installment)
                else:
                    amount = 0

        return amount

    def create_reassessment_installment_entry(self, stl_amount, reassessment_date):
        amount = stl_amount
        if round(abs(amount), 3) > 0:
            lines = [(0, 0, {
                'name': 'Reassessment Installment Entry',
                'account_id': self.long_lease_liability_account_id.id or self.leasee_template_id.long_lease_liability_account_id.id,
                'debit': amount if amount > 0 else 0,
                'credit': -amount if amount < 0 else 0,
                'analytic_account_id': self.analytic_account_id.id,
                'project_site_id': self.project_site_id.id,
                'type_id': self.type_id.id,
                'location_id': self.location_id.id,
            }),
                     (0, 0, {
                         'name': 'Reassessment Installment Entry',
                         'account_id': self.lease_liability_account_id.id,
                         'credit': amount if amount > 0 else 0,
                         'debit': -amount if amount < 0 else 0,
                         'analytic_account_id': self.analytic_account_id.id,
                         'project_site_id': self.project_site_id.id,
                         'type_id': self.type_id.id,
                         'location_id': self.location_id.id,
                     })]
            move = self.env['account.move'].create({
                'move_type': 'entry',
                'currency_id': self.leasee_currency_id.id,
                'ref': 'Reassessment Installment Entry',
                'date': reassessment_date,
                'journal_id': self.initial_journal_id.id,
                'leasee_contract_id': self.id,
                'line_ids': lines,
                'auto_post': True,
            })

    def get_reassessment_before_remaining_lease(self, reassessment_installments, days_before_reassessment, days):
        first_installment = reassessment_installments[0]
        if self.is_contract_not_annual():
            num_installments = self.get_installments_per_year()
            lease_liability = first_installment.subsequent_amount / days * days_before_reassessment
            for ins in reassessment_installments[:num_installments]:
                lease_liability += ins.amount - ins.subsequent_amount
        else:
            lease_liability = first_installment.amount - first_installment.subsequent_amount + first_installment.subsequent_amount / days * days_before_reassessment
        return lease_liability

    def get_reassessment_after_remaining_lease(self, reassessment_installments):
        # if self.is_contract_not_annual():
        #     num_installments = self.get_installments_per_year()
        #     lease_liability = 0
        #     for ins in reassessment_installments[:num_installments]:
        #         lease_liability += ins.amount - ins.subsequent_amount
        # else:
        #     first_installment = reassessment_installments[0]
        #     lease_liability = first_installment.amount - first_installment.subsequent_amount
        first_installment = reassessment_installments[0]
        lease_liability = first_installment.amount - first_installment.subsequent_amount
        return lease_liability

    def unlink(self):
        not_draft_contracts = self.filtered(lambda c: c.state != 'draft')
        if not_draft_contracts:
            raise ValidationError(_('You can delete only draft orders'))
        super(LeaseeContract, self).unlink()


class MultiLeasor(models.Model):
    _name = 'multi.leasor'
    _description = 'Multi Leasor'

    leasee_contract_id = fields.Many2one(comodel_name="leasee.contract",ondelete='cascade')
    partner_id = fields.Many2one(comodel_name="res.partner",required=True )
    type = fields.Selection(default="percentage", selection=[('percentage', 'Percentage'), ('amount', 'Amount'), ], required=True, )
    amount = fields.Float(string="", default=0.0, required=False)
    percentage = fields.Float(string="", default=0.0, required=False)











