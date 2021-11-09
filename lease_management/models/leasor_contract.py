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

import logging

LOGGER = logging.getLogger(__name__)


class LeasorContract(models.Model):
    _name = 'leasor.contract'
    _rec_name = 'name'
    _description = 'Leasor Contract'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Name", required=True, )
    # leasee_template_id = fields.Many2one(comodel_name="leasor.contract.template", string="Leasor Contract Template", required=False, )

    external_reference_number = fields.Char()
    state = fields.Selection(string="Agreement Status",default="draft", selection=[('draft', 'Draft'), ('active', 'Active'), ('expired', 'Expired'), ('terminated', 'Terminated'), ], required=False, )

    customer_id = fields.Many2one(comodel_name="res.partner", string="Leasee Name", required=True, )
    inception_date = fields.Date(default=lambda self: fields.Datetime.now(), required=False, )
    commencement_date = fields.Date(default=lambda self: fields.Datetime.now(), required=False, )
    # initial_payment_value = fields.Float(compute='compute_initial_payment_value')
    estimated_ending_date = fields.Date(compute='compute_estimated_ending_date')

    # lease_contract_period = fields.Float()
    lease_contract_period = fields.Integer()
    lease_contract_period_type = fields.Selection(string="Period Type", default="years",
                                              selection=[('years', 'Years'), ('months', 'Months'), ], required=True, )
    type_terminate = fields.Selection(string="Percentage or Amount",default="amount", selection=[('percentage', 'Percentage'), ('amount', 'Amount'), ], required=True, )
    extendable = fields.Boolean(string="Extendable ?", default=False )
    interest_rate = fields.Float(string="Interest Rate %", default=0.0, required=False, )
    payment_frequency_type = fields.Selection(string="Payment Type",default="years", selection=[('years', 'Years'), ('months', 'Months'), ], required=True, )
    payment_frequency = fields.Integer(default=1, required=False, )

    leasee_contract_id = fields.Many2one(comodel_name="leasee.contract",domain=[('state', 'in', ['active', 'extended'])], copy=False, string="Leased Asset",required=True)

    lease_currency_id = fields.Many2one(comodel_name="res.currency", string="", required=True, )

    account_move_ids = fields.One2many(comodel_name="account.move", inverse_name="leasor_contract_id", string="", required=False, )
    annual_payment = fields.Float(string="", default=0.0, required=False, )
    installment_product_id = fields.Many2one(comodel_name="product.product", string="", required=True, domain=[('type', '=', 'service')] )
    installment_journal_id = fields.Many2one(comodel_name="account.journal", domain=[('type', '=', 'sale')], required=True )
    prorate = fields.Boolean(string="Prorate Calculation", default=False  )
    account_analytic_id = fields.Many2one(comodel_name="account.analytic.account", string="", required=False, )
    project_site_id = fields.Many2one(comodel_name="account.analytic.account", string="Project/Site",
                                      domain=[('analytic_account_type', '=', 'project_site')], required=False, )
    type_id = fields.Many2one(comodel_name="account.analytic.account", string="Type",
                              domain=[('analytic_account_type', '=', 'type')], required=False, )
    location_id = fields.Many2one(comodel_name="account.analytic.account", string="Location",
                                  domain=[('analytic_account_type', '=', 'location')], required=False, )

    @api.constrains('estimated_ending_date', 'leasee_contract_id')
    def check_end_dates(self):
        if self.leasee_contract_id and self.leasee_contract_id.estimated_ending_date < self.estimated_ending_date:
            raise ValidationError(_('Leased Contact End Date Can not be after This contract End Date'))

    @api.depends('commencement_date', 'lease_contract_period')
    def compute_estimated_ending_date(self):
        for rec in self:
            if rec.lease_contract_period_type == 'years':
                rec.estimated_ending_date = rec.commencement_date + relativedelta(years=rec.lease_contract_period)
            else:
                rec.estimated_ending_date = rec.commencement_date + relativedelta(months=rec.lease_contract_period)

    def action_activate(self):
        self.action_generate_installments_entries()
        self.state = 'active'


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

    def action_open_invoices(self):
        domain = [('id', 'in', self.account_move_ids.ids), ('move_type', 'in', ['out_invoice', 'out_refund'])]
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

    def action_generate_installments_entries(self):
        if self.payment_frequency_type == 'months':
            pay_delta = relativedelta(months=self.payment_frequency)
        else:
            pay_delta = relativedelta(years=self.payment_frequency)

        invoice_date_due = (self.commencement_date + pay_delta).replace(day=1)
        for i in range(self.lease_contract_period):
            if self.lease_contract_period_type == 'months':
                delta = relativedelta(months=i)
                amount = self.annual_payment / 12
            else:
                delta = relativedelta(years=i)
                amount = self.annual_payment
            installment_date = self.commencement_date + delta
            if installment_date > invoice_date_due:
                invoice_date_due += pay_delta

            invoice_lines = [(0, 0, {
                'product_id': self.installment_product_id.id,
                'name': self.installment_product_id.name,
                'product_uom_id': self.installment_product_id.uom_id.id,
                'account_id': self.installment_product_id.product_tmpl_id.get_product_accounts()['expense'].id,
                'price_unit': amount,
                'quantity': 1,
                'account_analytic_id': self.account_analytic_id.id,
                'project_site_id': self.project_site_id.id,
                'type_id': self.type_id.id,
                'location_id': self.location_id.id,
            })]
            invoice = self.env['account.move'].create({
                'partner_id': self.customer_id.id,
                'move_type': 'out_invoice',
                'currency_id': self.lease_currency_id.id,
                'ref': self.name,
                'invoice_date_due': invoice_date_due,
                'invoice_date': installment_date,
                'invoice_line_ids': invoice_lines,
                'journal_id': self.installment_journal_id.id,
                'leasor_contract_id': self.id,
            })










