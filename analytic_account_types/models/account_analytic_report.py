# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict
from odoo import api, fields, models
from odoo.osv import expression


class Acc(models.Model):
    _inherit = 'account.analytic.account'

    crossovered_budget_proj_line = fields.One2many('crossovered.budget.lines',
                                                   'project_site_id',
                                                   'Budget Lines')
    crossovered_budget_type_line = fields.One2many('crossovered.budget.lines',
                                                   'type_id', 'Budget Lines')
    crossovered_budget_loc_line = fields.One2many('crossovered.budget.lines',
                                                  'location_id', 'Budget Lines')
    analytic_location_id = fields.Many2one(
        comodel_name="account.analytic.account", string="Location",
        required=False, domain=[('analytic_account_type', '=', 'location')], )
    analytic_type_filter_id = fields.Many2one(
        comodel_name="account.analytic.account", string="Type", required=False,
        domain=[('analytic_account_type', '=', 'type')], )

    site_address = fields.Char(string='Site Address')
    group_id = fields.Selection([
        ('managed', 'Managed'),
        ('owned', 'Owned')], 'Group',)
    site_status = fields.Selection(
        [('active', 'ACTIVE'), ('inactive', 'INACTIVE'), ('rfi', 'RFI'),
         ('in_progress', 'IN PROGRESS')],
        string='Site Status', default='active')
