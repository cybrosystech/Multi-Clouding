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
    state = fields.Selection(string="Agreement Status",default="draft", selection=[('draft', 'Draft'), ('active', 'Active'), ('extended', 'Extended'), ('expired', 'Expired'), ('terminated', 'Terminated'), ], required=False, )

    vendor_id = fields.Many2one(comodel_name="res.partner", string="Leassor Name", required=True, )
    inception_date = fields.Date(default=lambda self: fields.Datetime.now(), required=False, )
    commencement_date = fields.Date(default=lambda self: fields.Datetime.now(), required=False, )
    initial_payment_value = fields.Float(compute='compute_initial_payment_value')
    estimated_ending_date = fields.Date(compute='compute_estimated_ending_date')

    # lease_contract_period = fields.Float()
    lease_contract_period = fields.Integer()
    lease_contract_period_type = fields.Selection(string="Period Type", default="months",
                                              selection=[('years', 'Years'), ('months', 'Months'), ], required=True, )
    terminate_month_number = fields.Integer(string="Terminate At Month Number", default=0, required=False, )
    terminate_fine = fields.Float(string="", default=0.0, required=False, )
    type_terminate = fields.Selection(string="Percentage or Amount",default="amount", selection=[('percentage', 'Percentage'), ('amount', 'Amount'), ], required=True, )
    extendable = fields.Boolean(string="Extendable ?", default=False )
    interest_rate = fields.Float(string="Interest Rate %", default=0.0, required=False, )
    payment_frequency_type = fields.Selection(string="Payment Type",default="months", selection=[('years', 'Years'), ('months', 'Months'), ], required=True, )
    payment_frequency = fields.Integer(default=1, required=False, )

    increasement_frequency_type = fields.Selection(string="Increasement Type",default="months", selection=[('years', 'Years'), ('months', 'Months'), ], required=True, )
    increasement_frequency = fields.Integer(default=1, required=False, )
    increasement_rate = fields.Float(default=1, required=False, )
    # discount = fields.Float(string="Discount %", default=0.0, required=False, )
    asset_model_id = fields.Many2one(comodel_name="account.asset", string="Asset Model", required=False, domain=[('asset_type', '=', 'purchase'), ('state', '=', 'model')] )
    asset_id = fields.Many2one(comodel_name="account.asset", copy=False)

    leasee_currency_id = fields.Many2one(comodel_name="res.currency", string="", required=False, )
    asset_name = fields.Char(string="", default="", required=False, )
    asset_description = fields.Text(string="", default="", required=False, )
    initial_direct_cost = fields.Float(copy=True)
    incentives_received = fields.Float(copy=True)
    incentives_received_type = fields.Selection(default="receivable", selection=[('receivable', 'Receivable'), ('rent_free', 'Rent Free'), ], required=True, )
    rou_value = fields.Float(string="ROU Asset Value",compute='compute_rou_value')
    # registered_paymen = fields.Float(string="Registered Payment Prior Commencement Date")

    estimated_cost_dismantling = fields.Float(string="Estimated Cost For Dismantling", default=0.0, required=False,copy=True )
    useful_life = fields.Integer(string="Useful Life Of The Right Of The Use Asset", default=0, required=False, )
    lease_liability = fields.Float(compute='compute_lease_liability')
    installment_amount = fields.Float(string="", default=0.0, required=False, )
    remaining_lease_liability = fields.Float(compute='compute_remaining_lease_liability' )

    account_move_ids = fields.One2many(comodel_name="account.move", inverse_name="leasee_contract_id", string="", required=False, )

    lease_liability_account_id = fields.Many2one(comodel_name="account.account", string="", required=True, )
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

    payment_method = fields.Selection(string="Payment Method",default="beginning", selection=[('beginning', 'Beginning of Period'), ('end', 'End Of Period'), ], required=False, )

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
    prorata = fields.Boolean(default=False )
    parent_id = fields.Many2one(comodel_name="leasee.contract", string="", required=False, copy=False)
    child_ids = fields.One2many(comodel_name="leasee.contract", inverse_name="parent_id", string="", required=False, copy=False)

    incentives_account_id = fields.Many2one(comodel_name="account.account", string="", required=True, )
    incentives_product_id = fields.Many2one(comodel_name="product.product", string="", required=True, domain=[('type', '=', 'service')] )

    # @api.model
    # def create(self, vals):
    #     name = self.env['ir.sequence'].next_by_code('leasee.contract')
    #     vals['name'] = name
    #     vals['external_reference_number'] = name
    #     return super(LeaseeContract, self).create(vals)

    @api.depends('commencement_date', 'lease_contract_period')
    def compute_estimated_ending_date(self):
        for rec in self:
            if rec.lease_contract_period_type == 'years':
                rec.estimated_ending_date = rec.commencement_date + relativedelta(years=rec.lease_contract_period)
            else:
                rec.estimated_ending_date = rec.commencement_date + relativedelta(months=rec.lease_contract_period)

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

    def action_activate(self):
        for contract in self:
            if contract.state == 'draft':
                if contract.name == '/':
                    contract.name = self.env['ir.sequence'].next_by_code('leasee.contract')
                contract.create_commencement_move()
                contract.create_initial_bill()
                # self.create_installments()
                contract.create_rov_asset()
                contract.create_installments()
                contract.state = 'active'

            contract.leasee_action_generate_installments_entries()
            contract.leasee_action_generate_interest_entries()

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

    def compute_installments_num(self):
        for rec in self:
            if rec.lease_contract_period and rec.payment_frequency:
                total_contract_months = rec.lease_contract_period * (1 if rec.lease_contract_period_type == 'months' else 12)
                payment_freq_months = rec.payment_frequency * ( 1 if rec.payment_frequency_type == 'months' else 12)
                return math.floor(total_contract_months/payment_freq_months)
            else:
                return 0

    @api.depends('installment_amount', 'lease_contract_period', 'increasement_rate', 'installment_ids', 'installment_ids.amount')
    def compute_lease_liability(self):
        for rec in self:
            period_range = range(rec.compute_installments_num())
            if rec.payment_method == 'beginning':
                # period_range = range(rec.lease_contract_period)
                start = 0
            else:
                # period_range = range(1, rec.lease_contract_period + 1)
                start = 1
            if rec.installment_ids:
                installments = rec.installment_ids[1:]
                increased_installments = installments.mapped('amount')
            else:
                increased_installments = [rec.get_future_value(rec.installment_amount, rec.increasement_rate, i) for i in period_range]

                if rec.incentives_received_type == 'rent_free':
                    remaining_incentives = rec.incentives_received
                    for i in range(len(increased_installments)):
                        if remaining_incentives > 0:
                            if remaining_incentives >= increased_installments[i]:
                                remaining_incentives -= increased_installments[i]
                                increased_installments[i] = 0
                            else:
                                increased_installments[i] -= remaining_incentives
                                remaining_incentives = 0

            net_present_value = sum([rec.get_present_value(installment, rec.interest_rate, i+start) for i, installment in enumerate(increased_installments)])
            rec.lease_liability = net_present_value

    @api.depends('state','lease_liability', 'initial_payment_value', 'initial_direct_cost', 'estimated_cost_dismantling', 'incentives_received')
    def compute_rou_value(self):
        for rec in self:
            if rec.state == 'terminated':
                rec.rou_value = 0
            else:
                if self.incentives_received_type == 'rent_free':
                    rec.rou_value = rec.lease_liability + rec.initial_payment_value + rec.initial_direct_cost + rec.estimated_cost_dismantling
                else:
                    rec.rou_value = rec.lease_liability + rec.initial_payment_value + rec.initial_direct_cost + rec.estimated_cost_dismantling - rec.incentives_received

    @api.model
    def get_present_value(self, future_value, interest, period):
        present_value = future_value / (1 + interest/100) ** period
        return present_value

    @api.model
    def get_future_value(self, present_value, interest, period):
        future_value = present_value * (1 + interest/100) ** period
        return future_value

    def create_rov_asset(self):
        if not self.asset_id:
            method_number = self.lease_contract_period * ( 1 if self.lease_contract_period_type == 'months' else 12)
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
            move_lines = self.env['account.move.line'].search([
                ('move_id.state', '=', 'posted'),
                ('move_id.leasee_contract_id', '=', self.id),
                ('account_id', '=', self.lease_liability_account_id.id),
            ])
            balance = sum([(l.debit - l.credit) for l in move_lines ])
            if rec.state == 'terminated':
                rec.remaining_lease_liability = 0
            else:
                rec.remaining_lease_liability = -1*balance

    def create_initial_bill(self):
        amount = self.initial_direct_cost + self.initial_payment_value
        if amount:
            invoice_lines = [(0, 0, {
                'product_id': self.initial_product_id.id,
                'name': self.initial_product_id.name,
                'product_uom_id': self.initial_product_id.uom_id.id,
                'account_id': self.initial_product_id.product_tmpl_id.get_product_accounts()['expense'].id,
                'price_unit': amount,
                'quantity': 1,
                'analytic_account_id': self.analytic_account_id.id,
                'project_site_id': self.project_site_id.id,
                'type_id': self.type_id.id,
                'location_id': self.location_id.id,
            })]
            invoice = self.env['account.move'].create({
                'partner_id': self.vendor_id.id,
                'move_type': 'in_invoice',
                'currency_id': self.leasee_currency_id.id,
                'ref': self.name,
                'invoice_date': self.commencement_date,
                'invoice_line_ids': invoice_lines,
                'journal_id': self.installment_journal_id.id,
                'leasee_contract_id': self.id,
                'auto_post': True,
            })
            line = invoice.line_ids.filtered(lambda l : l.account_id == self.vendor_id.property_account_payable_id)
            if line:
                line.write({
                    'analytic_account_id': self.analytic_account_id.id,
                    'project_site_id': self.project_site_id.id,
                    'type_id': self.type_id.id,
                    'location_id': self.location_id.id,
                })

        if self.incentives_received and self.incentives_received_type != 'rent_free':
            invoice_lines = [(0, 0, {
                'product_id': self.incentives_product_id.id,
                'name': self.incentives_product_id.name,
                'product_uom_id': self.incentives_product_id.uom_id.id,
                'account_id': self.incentives_product_id.product_tmpl_id.get_product_accounts()['expense'].id,
                'price_unit': self.incentives_received,
                'quantity': 1,
                'analytic_account_id': self.analytic_account_id.id,
                'project_site_id': self.project_site_id.id,
                'type_id': self.type_id.id,
                'location_id': self.location_id.id,
            })]
            invoice = self.env['account.move'].create({
                'partner_id': self.vendor_id.id,
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
            line = invoice.line_ids.filtered(lambda l : l.account_id == self.vendor_id.property_account_payable_id)
            if line:
                line.write({
                    'analytic_account_id': self.analytic_account_id.id,
                    'project_site_id': self.project_site_id.id,
                    'type_id': self.type_id.id,
                    'location_id': self.location_id.id,
                })

    def create_commencement_move(self):
        rou_account = self.asset_model_id.account_asset_id
        lines = [(0, 0, {
            'name': 'create contract number %s' % self.name,
            'account_id': rou_account.id,
            'credit': 0,
            'debit': self.rou_value - (self.initial_direct_cost + self.initial_payment_value),
            'analytic_account_id': self.analytic_account_id.id,
            'project_site_id': self.project_site_id.id,
            'type_id': self.type_id.id,
            'location_id': self.location_id.id,
        }),(0, 0, {
            'name': 'create contract number %s' % self.name,
            'account_id': self.lease_liability_account_id.id,
            'debit': 0,
            'credit': self.lease_liability,
            'analytic_account_id': self.analytic_account_id.id,
            'project_site_id': self.project_site_id.id,
            'type_id': self.type_id.id,
            'location_id': self.location_id.id,
        })]

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

    def create_beginning_installments(self):
        start = self.commencement_date
        # remaining_lease_liability = self.lease_liability - self.incentives_received
        remaining_lease_liability = self.lease_liability
        num_installment = self.compute_installments_num()
        period_range = range(0, num_installment + 1)
        payment_months = self.payment_frequency * (1 if self.payment_frequency_type == 'months' else 12)
        if self.incentives_received_type == 'receivable':
            for i in period_range:
                if i > 0:
                    amount = self.get_future_value(self.installment_amount, self.increasement_rate, i-1 )
                    interest_recognition = (remaining_lease_liability - amount) * self.interest_rate / 100
                else:
                    amount = 0
                    interest_recognition = 0
                if i != 1 and i != 0:
                    new_start = start + relativedelta(months=(i-1)*payment_months)
                else:
                    new_start = start

                remaining_lease_liability -= (amount - interest_recognition)
                self.env['leasee.installment'].create({
                    'name': self.name + ' installment - ' + new_start.strftime(DF),
                    'period': i,
                    'amount': amount,
                    'date': new_start,
                    'leasee_contract_id': self.id,
                    'subsequent_amount': interest_recognition,
                    'remaining_lease_liability': round(remaining_lease_liability,2),
                })
        else:
            remaining_incentives = self.incentives_received
            for i in period_range:
                if i > 0:
                    amount = self.get_future_value(self.installment_amount, self.increasement_rate, i - 1)
                else:
                    amount = 0

                if remaining_incentives > 0:
                    if amount <= remaining_incentives:
                        remaining_incentives -= amount
                        amount = 0
                    else:
                        amount -= remaining_incentives
                else:
                    remaining_incentives = 0

                if i > 0:
                    interest_recognition = (remaining_lease_liability - amount) * self.interest_rate / 100
                else:
                    interest_recognition = 0
                if i != 1 and i != 0:
                    new_start = start + relativedelta(months=(i - 1) * payment_months)
                else:
                    new_start = start

                remaining_lease_liability -= (amount - interest_recognition)
                self.env['leasee.installment'].create({
                    'name': self.name + ' installment - ' + new_start.strftime(DF),
                    'period': i,
                    'amount': amount,
                    'date': new_start,
                    'leasee_contract_id': self.id,
                    'subsequent_amount': interest_recognition,
                    'remaining_lease_liability': round(remaining_lease_liability, 2),
                })

    def create_end_installments(self):
        remaining_lease_liability = self.lease_liability
        payment_months = self.payment_frequency * (1 if self.payment_frequency_type == 'months' else 12)
        self.env['leasee.installment'].create({
            'name': self.name + ' installment - ' + self.commencement_date.strftime(DF),
            'period': 0,
            'amount': 0,
            'date': self.commencement_date + relativedelta(months=payment_months, days=-1),
            'leasee_contract_id': self.id,
            'subsequent_amount': 0,
            'remaining_lease_liability': round(remaining_lease_liability, 2),
        })

        if self.incentives_received_type == 'receivable':
            start = self.commencement_date

            num_installment = self.compute_installments_num()
            period_range = range(1, num_installment + 1)

            for i in period_range:
                amount = self.get_future_value(self.installment_amount, self.increasement_rate, i - 1)
                new_start = start + relativedelta(months=i*payment_months, days=-1)
                interest_recognition = remaining_lease_liability * self.interest_rate / 100
                remaining_lease_liability -= (amount - interest_recognition)
                self.env['leasee.installment'].create({
                    'name': self.name + ' installment - ' + new_start.strftime(DF),
                    'period': i,
                    'amount': amount,
                    'date': new_start,
                    'leasee_contract_id': self.id,
                    'subsequent_amount': interest_recognition,
                    'remaining_lease_liability': round(remaining_lease_liability,2),
                })
        else:
            start = self.commencement_date
            # remaining_lease_liability = self.lease_liability
            num_installment = self.compute_installments_num()
            period_range = range(1, num_installment + 1)
            remaining_incentives = self.incentives_received
            for i in period_range:
                amount = self.get_future_value(self.installment_amount, self.increasement_rate, i - 1)

                if remaining_incentives > 0:
                    if amount <= remaining_incentives:
                        remaining_incentives -= amount
                        amount = 0
                    else:
                        amount -= remaining_incentives
                        remaining_incentives = 0

                new_start = start + relativedelta(months=i*payment_months, days=-1)
                interest_recognition = remaining_lease_liability * self.interest_rate / 100
                remaining_lease_liability -= (amount - interest_recognition)
                self.env['leasee.installment'].create({
                    'name': self.name + ' installment - ' + new_start.strftime(DF),
                    'period': i,
                    'amount': amount,
                    'date': new_start,
                    'leasee_contract_id': self.id,
                    'subsequent_amount': interest_recognition,
                    'remaining_lease_liability': round(remaining_lease_liability,2),
                })

    def create_installments(self):
        if self.payment_method == 'beginning':
            self.create_beginning_installments()
        else:
            self.create_end_installments()

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

    def process_termination(self):
        leasee_moves = self.env['account.move'].search([('leasee_contract_id', '=', self.id),('asset_id', '=', False)])
        moves_after_terminate = leasee_moves.filtered(lambda m: m.date >= date.today())
        for move in moves_after_terminate:
            move.button_draft()
            move.button_cancel()
        self.create_termination_fees()
        self.state = 'terminated'

    def create_termination_fees(self):
        amount = self.terminate_fine
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
            'partner_id': self.vendor_id.id,
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
                invoice_lines = [(0, 0, {
                    'product_id': contract.installment_product_id.id,
                    'name': contract.installment_product_id.name,
                    'product_uom_id': contract.installment_product_id.uom_id.id,
                    'account_id': contract.installment_product_id.product_tmpl_id.get_product_accounts()['expense'].id,
                    'price_unit': install.amount,
                    'quantity': 1,
                    'analytic_account_id': contract.analytic_account_id.id,
                    'project_site_id': contract.project_site_id.id,
                    'type_id': contract.type_id.id,
                    'location_id': contract.location_id.id,
                    'tax_ids': [(4, tax_id) for tax_id in contract.installment_product_id.taxes_id.ids],
                })]
                invoice = self.env['account.move'].create({
                    'partner_id': contract.vendor_id.id,
                    'move_type': 'in_invoice',
                    'currency_id': contract.leasee_currency_id.id,
                    'ref': contract.name + ' - ' + install.date.strftime('%d/%m/%Y'),
                    'invoice_date': install.date,
                    'invoice_line_ids': invoice_lines,
                    'journal_id': contract.installment_journal_id.id,
                    'leasee_contract_id': contract.id,
                    'auto_post': True,
                })
                line = invoice.line_ids.filtered(lambda l: l.account_id == contract.vendor_id.property_account_payable_id)
                if line:
                    line.write({
                        'analytic_account_id': contract.analytic_account_id.id,
                        'project_site_id': contract.project_site_id.id,
                        'type_id': contract.type_id.id,
                        'location_id': contract.location_id.id,
                    })
                install.installment_invoice_id = invoice.id

    @api.model
    def leasee_action_generate_interest_entries(self):
        contracts = self.search([]).filtered(lambda c: c.commencement_date <= date.today() )
        for contract in contracts:
            delta = contract.payment_frequency * (1 if contract.payment_frequency_type == 'months' else 12)
            date_comparison = date.today() + relativedelta(months=delta)
            instalments = self.env['leasee.installment'].search([
                ('leasee_contract_id', '=', contract.id),
            ])
            # ]).filtered(lambda rec: rec.date <= date_comparison and rec.period)
            for installment in instalments:
                if installment.subsequent_amount:
                    # if contract.payment_frequency_type == 'months':
                    #     if not installment.interest_move_ids:
                    #         if contract.payment_method == 'beginning':
                    #             move_date = installment.date
                    #         else:
                    #             move_date = installment.date + relativedelta(days=-1)
                    #         contract.create_interset_move(installment, move_date, installment.subsequent_amount)
                    # else:
                    if installment.subsequent_amount and len(installment.interest_move_ids) < delta:
                        if contract.payment_method == 'beginning':
                            # supposed_dates = [installment.date + relativedelta(months=i,days=-1) for i in range(1, delta+1) if (installment.date + relativedelta(months=i,days=-1)) <= date.today()]
                            supposed_dates = [installment.date + relativedelta(months=i,days=-1) for i in range(1, delta+1) ]
                        else:
                            # supposed_dates = [installment.date - relativedelta(months=i) for i in range(delta) if (installment.date - relativedelta(months=i)) <= date.today()]
                            supposed_dates = [installment.date - relativedelta(months=i) for i in range(delta) ]

                        removed_dates = []
                        for move in installment.interest_move_ids:
                            for s_date in supposed_dates:
                                if s_date.year == move.date.year and s_date.month == move.date.month:
                                    removed_dates.append(s_date)
                                    break
                        supposed_dates = list(set(supposed_dates) - set(removed_dates))
                        for n_date in supposed_dates:
                            interest_amount = installment.subsequent_amount / delta
                            contract.create_interset_move(installment, n_date, interest_amount)

    def create_interset_move(self, installment, move_date, interest_amount):
        if interest_amount > 0:
            lines = [(0, 0, {
                'name': 'Interest Recognition for %s' % move_date.strftime(DF),
                'account_id': self.lease_liability_account_id.id,
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











