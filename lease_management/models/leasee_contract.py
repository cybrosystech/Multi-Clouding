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

    name = fields.Char(string="Name", required=True, )
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
    lease_contract_period_type = fields.Selection(string="Period Type", default="years",
                                              selection=[('years', 'Years'), ('months', 'Months'), ], required=True, )
    terminate_month_number = fields.Integer(string="Terminate At Month Number", default=0, required=False, )
    terminate_fine = fields.Float(string="", default=0.0, required=False, )
    type_terminate = fields.Selection(string="Percentage or Amount",default="amount", selection=[('percentage', 'Percentage'), ('amount', 'Amount'), ], required=True, )
    extendable = fields.Boolean(string="Extendable ?", default=False )
    interest_rate = fields.Float(string="Interest Rate %", default=0.0, required=False, )
    payment_frequency_type = fields.Selection(string="Payment Type",default="years", selection=[('years', 'Years'), ('months', 'Months'), ], required=True, )
    payment_frequency = fields.Integer(default=1, required=False, )

    increasement_frequency_type = fields.Selection(string="Increasement Type",default="years", selection=[('years', 'Years'), ('months', 'Months'), ], required=True, )
    increasement_frequency = fields.Integer(default=1, required=False, )
    increasement_rate = fields.Float(default=1, required=False, )
    # discount = fields.Float(string="Discount %", default=0.0, required=False, )
    asset_model_id = fields.Many2one(comodel_name="account.asset", string="Asset Model", required=False, domain=[('asset_type', '=', 'purchase'), ('state', '=', 'model')] )
    asset_id = fields.Many2one(comodel_name="account.asset", copy=False)

    leasee_currency_id = fields.Many2one(comodel_name="res.currency", string="", required=False, )
    asset_name = fields.Char(string="", default="", required=False, )
    asset_description = fields.Text(string="", default="", required=False, )
    initial_direct_cost = fields.Float()
    incentives_received = fields.Float()
    rou_value = fields.Float(string="ROU Asset Value",compute='compute_rou_value')
    # registered_paymen = fields.Float(string="Registered Payment Prior Commencement Date")

    estimated_cost_dismantling = fields.Float(string="Estimated Cost For Dismantling", default=0.0, required=False, )
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

    @api.depends('commencement_date', 'lease_contract_period')
    def compute_estimated_ending_date(self):
        for rec in self:
            if rec.lease_contract_period_type == 'years':
                rec.estimated_ending_date = rec.commencement_date + relativedelta(years=rec.lease_contract_period)
            else:
                rec.estimated_ending_date = rec.commencement_date + relativedelta(months=rec.lease_contract_period)

    def action_activate(self):
        self.create_commencement_move()
        self.create_initial_bill()
        # self.create_installments()
        self.create_rov_asset()
        self.create_installments()
        self.state = 'active'

    def action_view_asset(self):
        view_form = {
            'name': _('Asset'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.asset',
            'type': 'ir.actions.act_window',
            'res_id': self.asset_id.id,
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
            #     period_range = range(rec.lease_contract_period)
                start = 0
            else:
            #     period_range = range(1, rec.lease_contract_period + 1)
                start = 1
            if rec.installment_ids:
                increased_installments = rec.installment_ids.mapped('amount')
            else:
                increased_installments = [rec.get_future_value(rec.installment_amount, rec.increasement_rate, i) for i in period_range]
            net_present_value = sum([rec.get_present_value(installment, rec.interest_rate, i+start) for i, installment in enumerate(increased_installments)])
            rec.lease_liability = net_present_value

    @api.depends('state','lease_liability', 'initial_payment_value', 'initial_direct_cost', 'estimated_cost_dismantling', 'incentives_received')
    def compute_rou_value(self):
        for rec in self:
            if rec.state == 'terminated':
                rec.rou_value = 0
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
            vals = {
                'name': self.name,
                'model_id': self.asset_model_id.id,
                'original_value': self.rou_value,
                'asset_type': 'purchase',
                # 'partner_id': self.vendor_id.id,
                # 'company_id': record.move_id.company_id.id,
                # 'currency_id': self.env.user.company_id.currency_id.id,
                'acquisition_date': self.commencement_date,
                'method_number': self.lease_contract_period,
                'account_analytic_id': self.analytic_account_id.id,
                'project_site_id': self.project_site_id.id,
                'type_id': self.type_id.id,
                'location_id': self.location_id.id,
                # 'method_period': self.lease_contract_period_type,
            }
            # changed_vals = self.env['account.asset'].onchange_category_id_values(self.asset_model_id.category_id.id)
            # vals.update(changed_vals['value'])
            # vals.update({
            #     '':,
            # })
            if self.asset_model_id:
                asset = self.asset_model_id.copy(vals)
            else:
                asset = self.env['account.asset'].create(vals)
            # if self.asset_model_id.category_id.open_asset:
            #     asset.validate()
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
            rec.remaining_lease_liability = -1*balance

    def create_initial_bill(self):
        amount = self.initial_direct_cost + self.initial_payment_value
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
            'invoice_date': datetime.now(),
            'invoice_line_ids': invoice_lines,
            'journal_id': self.installment_journal_id.id,
            'leasee_contract_id': self.id,
        })

    def create_commencement_move(self):
        rou_account = self.asset_model_id.account_asset_id
        lines = [(0, 0, {
            'name': 'create contract number %s' % self.name,
            'account_id': rou_account.id,
            'credit': 0,
            'debit': self.rou_value - (self.initial_direct_cost + self.initial_payment_value),
            'analytic_account_id': self.analytic_account_id.id,
        }),(0, 0, {
            'name': 'create contract number %s' % self.name,
            'account_id': self.lease_liability_account_id.id,
            'debit': 0,
            'credit': self.lease_liability - self.incentives_received,
            'analytic_account_id': self.analytic_account_id.id,
        }),(0, 0, {
            'name': 'create contract number %s' % self.name,
            'account_id': self.provision_dismantling_account_id.id,
            'debit': 0,
            'credit': self.estimated_cost_dismantling,
            'analytic_account_id': self.analytic_account_id.id,
        })]
        move = self.env['account.move'].create({
            'partner_id': self.vendor_id.id,
            'move_type': 'entry',
            'currency_id': self.leasee_currency_id.id,
            'ref': self.name,
            'date': self.commencement_date,
            'journal_id': self.asset_model_id.journal_id.id,
            'leasee_contract_id': self.id,
            'line_ids': lines,
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

    def create_installments(self):
        start = self.commencement_date
        # remaining_lease_liability = self.lease_liability - self.incentives_received
        remaining_lease_liability = self.lease_liability
        num_installment = self.compute_installments_num()
        period_range = range(num_installment)
        payment_months = self.payment_frequency * (1 if self.payment_frequency_type == 'months' else 12)
        if self.payment_method == 'beginning':
            #     period_range = range(rec.lease_contract_period)
            start_p = 0
        else:
            #     period_range = range(1, rec.lease_contract_period + 1)
            start_p = 1

        for i in period_range:
            amount = self.get_future_value(self.installment_amount, self.increasement_rate, i )
            if start_p:
                new_start = start + relativedelta(months=(i+start_p)*payment_months, days=-1)
            else:
                new_start = start + relativedelta(months=i*payment_months)

            interest_recognition = remaining_lease_liability * self.interest_rate / 100
            if self.payment_method == 'beginning':
                if i == 0:
                    interest_recognition = 0
            remaining_lease_liability -= (amount - interest_recognition)
            self.env['leasee.installment'].create({
                'name': self.name + ' installment - ' + new_start.strftime(DF),
                'amount': amount,
                'date': new_start,
                'leasee_contract_id': self.id,
                'subsequent_amount': interest_recognition,
                'remaining_lease_liability': round(remaining_lease_liability,2),
            })

    def create_subsequent_measurement_move(self, date):
        amount = self.remaining_lease_liability * self.interest_rate / (100 * 12)
        lines = [(0, 0, {
            'name': 'Interest Recognition for %s' % date,
            'account_id': self.lease_liability_account_id.id,
            'debit': 0,
            'credit': amount,
            'analytic_account_id': self.analytic_account_id.id,
        }),(0, 0, {
            'name': 'Interest Recognition for %s' % date,
            'account_id': self.interest_expense_account_id.id,
            'debit': amount,
            'credit': 0,
            'analytic_account_id': self.analytic_account_id.id,
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
        })

    def action_create_payment(self):
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
        leasee_contracts = self.search([]).filtered(lambda rec: rec.estimated_ending_date <= fields.Date.today())
        for contract in leasee_contracts:
            contract.state = 'expired'

    @api.model
    def leasee_action_generate_installments_entries(self):
        instalments = self.env['leasee.installment'].search([
            ('installment_invoice_id','=', False),
            ('leasee_contract_id','!=', False),
        ]).filtered(lambda rec: rec.date <= date.today())
        for install in instalments:
            contract = install.leasee_contract_id
            invoice_lines = [(0, 0, {
                'product_id': contract.installment_product_id.id,
                'name': contract.installment_product_id.name,
                'product_uom_id': contract.installment_product_id.uom_id.id,
                'account_id': contract.installment_product_id.product_tmpl_id.get_product_accounts()['expense'].id,
                'price_unit': install.amount,
                'quantity': 1,
                'analytic_account_id': self.analytic_account_id.id,
                'project_site_id': self.project_site_id.id,
                'type_id': self.type_id.id,
                'location_id': self.location_id.id,
            })]
            invoice = self.env['account.move'].create({
                'partner_id': contract.vendor_id.id,
                'move_type': 'in_invoice',
                'currency_id': contract.leasee_currency_id.id,
                'ref': contract.name,
                'invoice_date': install.date,
                'invoice_line_ids': invoice_lines,
                'journal_id': contract.installment_journal_id.id,
                'leasee_contract_id': contract.id,
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
            ]).filtered(lambda rec: rec.date <= date_comparison)
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
                            supposed_dates = [installment.date - relativedelta(months=i) for i in range(delta) if (installment.date - relativedelta(months=i)) <= date.today()]
                        else:
                            supposed_dates = [installment.date - relativedelta(months=i) for i in range(delta) if (installment.date - relativedelta(months=i)) <= date.today()]

                        for move in installment.interest_move_ids:
                            for s_date in supposed_dates:
                                if s_date.year == move.date.year and s_date.month == move.date.month:
                                    del s_date
                                    break

                        for n_date in supposed_dates:
                            interest_amount = installment.subsequent_amount / delta
                            contract.create_interset_move(installment, n_date, interest_amount)

    def create_interset_move(self, installment, move_date, interest_amount):
        lines = [(0, 0, {
            'name': 'Interest Recognition for %s' % date,
            'account_id': self.lease_liability_account_id.id,
            'debit': 0,
            'credit': interest_amount,
            'analytic_account_id': self.analytic_account_id.id,
        }),(0, 0, {
            'name': 'Interest Recognition for %s' % date,
            'account_id': self.interest_expense_account_id.id,
            'debit': interest_amount,
            'credit': 0,
            'analytic_account_id': self.analytic_account_id.id,
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
        })









