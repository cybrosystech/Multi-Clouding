# -*- coding: utf-8 -*-
""" init object """
from odoo import fields, models, api, _
import logging

LOGGER = logging.getLogger(__name__)


class LeaseContractTemplate(models.Model):
    _name = 'leasee.contract.template'
    _rec_name = 'name'
    _description = 'Lease Contract Template'
    _inherit = ['mail.thread']

    name = fields.Char(string="Name", required=True, )
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
    increasement_rate = fields.Float()

    increasement_frequency_type = fields.Selection(string="Increasement Type",default="months", selection=[('years', 'Years'), ('months', 'Months'), ], required=True, )
    increasement_frequency = fields.Integer(default=1, required=False, )
    # discount = fields.Float(string="Discount %", default=0.0, required=False, )
    asset_model_id = fields.Many2one(comodel_name="account.asset", string="Asset Model", required=False, domain=[('asset_type', '=', 'purchase'), ('state', '=', 'model')] )

    lease_liability_account_id = fields.Many2one(comodel_name="account.account", string="", required=True, )
    provision_dismantling_account_id = fields.Many2one(comodel_name="account.account", string="", required=True, )
    terminate_account_id = fields.Many2one(comodel_name="account.account", string="", required=True, )
    interest_expense_account_id = fields.Many2one(comodel_name="account.account", string="", required=True, )
    # interest_expense_account_id = fields.Many2one(comodel_name="account.account", string="", required=True, )

    terminate_product_id = fields.Many2one(comodel_name="product.product", string="", required=True,domain=[('type', '=', 'service')] )
    installment_product_id = fields.Many2one(comodel_name="product.product", string="", required=True,domain=[('type', '=', 'service')] )
    extension_product_id = fields.Many2one(comodel_name="product.product", string="", required=True,domain=[('type', '=', 'service')] )

    installment_journal_id = fields.Many2one(comodel_name="account.journal", string="", required=True, )
    initial_journal_id = fields.Many2one(comodel_name="account.journal", string="", required=True, )
    analytic_account_id = fields.Many2one(comodel_name="account.analytic.account", string="", required=True, )

    # interest_expense_account_id = fields.Many2one(comodel_name="account.account", string="", required=True, )

    project_site_id = fields.Many2one(comodel_name="account.analytic.account", string="Project/Site",
                                      domain=[('analytic_account_type', '=', 'project_site')], required=False, )
    type_id = fields.Many2one(comodel_name="account.analytic.account", string="Type",
                              domain=[('analytic_account_type', '=', 'type')], required=False, )
    location_id = fields.Many2one(comodel_name="account.analytic.account", string="Location",
                                  domain=[('analytic_account_type', '=', 'location')], required=False, )
    prorata = fields.Boolean(default=False )

    incentives_account_id = fields.Many2one(comodel_name="account.account", string="", required=True, )
    incentives_product_id = fields.Many2one(comodel_name="product.product", string="", required=True, domain=[('type', '=', 'service')] )


