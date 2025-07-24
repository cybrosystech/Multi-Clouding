# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AccountMoveLine(models.Model):
    """ This model represents cip.account.move.line."""
    _name = 'cip.account.move.line'
    _description = 'CIPAccountMoveLine'

    product_id = fields.Many2one('product.product')
    quantity = fields.Float()
    company_currency_id = fields.Many2one(related='cip_account_asset_id.company_id.currency_id')
    amount = fields.Monetary(
        currency_field='company_currency_id',
    )
    analytic_account_id = fields.Many2one('account.analytic.account',
                                          string="Cost Center")
    project_site_id = fields.Many2one('account.analytic.account',
                                     domain=[('analytic_account_type', '=',
                                               'project_site')],)
    site_status = fields.Selection(
        [('on_air', 'ON AIR'), ('off_air', 'OFF AIR'), ])
    t_budget = fields.Selection(
        [('capex', 'CAPEX'), ('opex', 'OPEX'), ],
        string='T.Budget')
    cip_account_id = fields.Many2one('account.account',required=True)
    asset_account_id = fields.Many2one('account.account',required=True)
    item_id = fields.Many2one('account.move.line')
    cip_account_asset_id = fields.Many2one('cip.account.asset')
