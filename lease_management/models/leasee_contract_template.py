# -*- coding: utf-8 -*-
""" init object """
from odoo import fields, models, api, _
import logging

LOGGER = logging.getLogger(__name__)


class LeaseContractTemplate(models.Model):
    _name = 'leasee.contract.template'
    _rec_name = 'name'
    _description = 'Lease Contract Template'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'analytic.mixin']

    name = fields.Char(string="Name", required=True, )
    lease_contract_period = fields.Integer()
    lease_contract_period_type = fields.Selection(string="Period Type",
                                                  default="months",
                                                  selection=[('years', 'Years'),
                                                             ('months',
                                                              'Months'), ],
                                                  required=True, )
    terminate_month_number = fields.Integer(string="Terminate At Month Number",
                                            default=0, required=False, )
    terminate_fine = fields.Float(string="", default=0.0, required=False, )
    type_terminate = fields.Selection(string="Percentage or Amount",
                                      default="amount",
                                      selection=[('percentage', 'Percentage'),
                                                 ('amount', 'Amount'), ],
                                      required=True, )
    extendable = fields.Boolean(string="Extendable ?", default=False)
    interest_rate = fields.Float(string="Interest Rate %", default=0.0,
                                 required=False, )
    payment_frequency_type = fields.Selection(string="Payment Type",
                                              default="months",
                                              selection=[('years', 'Years'), (
                                                  'months', 'Months'), ],
                                              required=True, )
    payment_frequency = fields.Integer(default=1, required=False, )
    increasement_rate = fields.Float()
    initial_product_id = fields.Many2one(comodel_name="product.product",
                                         string="", required=True,
                                         domain=[('type', '=', 'service')])

    increasement_frequency_type = fields.Selection(string="Increasement Type",
                                                   default="months", selection=[
            ('years', 'Years'), ('months', 'Months'), ], required=True, )
    increasement_frequency = fields.Integer(default=1, required=False, )
    asset_model_id = fields.Many2one(comodel_name="account.asset",
                                     string="Asset Model", required=False,
                                     domain=[('state', '=', 'model')])

    lease_liability_account_id = fields.Many2one(comodel_name="account.account",
                                                 string="Short Lease Liability Account",
                                                 required=True, )
    long_lease_liability_account_id = fields.Many2one(
        comodel_name="account.account", string="Long Lease Liability Account",
        required=True, )
    provision_dismantling_account_id = fields.Many2one(
        comodel_name="account.account", string="", required=True, )
    terminate_account_id = fields.Many2one(comodel_name="account.account",
                                           string="", required=True, )
    interest_expense_account_id = fields.Many2one(
        comodel_name="account.account", string="", required=True, )
    terminate_product_id = fields.Many2one(comodel_name="product.product",
                                           string="", required=True,
                                           domain=[('type', '=', 'service')])
    installment_product_id = fields.Many2one(comodel_name="product.product",
                                             string="", required=True,
                                             domain=[('type', '=', 'service')])
    extension_product_id = fields.Many2one(comodel_name="product.product",
                                           string="", required=True,
                                           domain=[('type', '=', 'service')])

    installment_journal_id = fields.Many2one(comodel_name="account.journal",
                                             string="", required=True, )
    initial_journal_id = fields.Many2one(comodel_name="account.journal",
                                         string="", required=True, )
    analytic_account_id = fields.Many2one(
        comodel_name="account.analytic.account", string="Cost Center",
        required=True, domain=[
            ('analytic_account_type', '=',
             'cost_center')], )
    project_site_id = fields.Many2one(comodel_name="account.analytic.account",
                                      string="Project/Site",
                                      domain=[('analytic_account_type', '=',
                                               'project_site')],
                                      required=True, )
    analytic_distribution = fields.Json()

    incentives_account_id = fields.Many2one(comodel_name="account.account",
                                            string="", required=True, )
    incentives_product_id = fields.Many2one(comodel_name="product.product",
                                            string="", required=True,
                                            domain=[('type', '=', 'service')])
    prorata_computation_type = fields.Selection(
        selection=[
            ('none', 'No Prorata'),
            ('constant_periods', 'Constant Periods'),
            ('daily_computation', 'Based on days per period'),
        ],
        string="Computation",
        required=True, default='constant_periods',
    )

    @api.onchange('lease_contract_period', 'company_id')
    def onchange_lease_contract_period(self):
        if self.lease_contract_period_type == 'years':
            interest_rate = self.env['leasee.interest.rate'].search(
                [('years', '=', self.lease_contract_period),
                 ('company_id', '=', self.company_id.id)])
            if interest_rate:
                self.interest_rate = interest_rate.rate
            else:
                self.interest_rate = 0.0

    @api.onchange('project_site_id', 'analytic_account_id')
    def onchange_project_site(self):
        type = self.project_site_id.analytic_type_filter_id.id
        location = self.project_site_id.analytic_location_id.id
        co_location = self.project_site_id.co_location.id
        analytic_dist = {}
        analytic_distributions = ''
        if self.analytic_account_id:
            analytic_distributions = analytic_distributions + ',' + str(
                self.analytic_account_id.id)
        if self.project_site_id:
            analytic_distributions = analytic_distributions + ',' + str(
                self.project_site_id.id)
        if self.project_site_id.analytic_type_filter_id:
            analytic_distributions = analytic_distributions + ',' + str(
                self.project_site_id.analytic_type_filter_id.id)
        if self.project_site_id.analytic_location_id:
            analytic_distributions = analytic_distributions + ',' + str(
                self.project_site_id.analytic_location_id.id)
        if self.project_site_id.co_location:
            analytic_distributions = analytic_distributions + ',' + str(
                self.project_site_id.co_location.id)
        analytic_dist.update({analytic_distributions: 100})
        self.analytic_distribution = analytic_dist
