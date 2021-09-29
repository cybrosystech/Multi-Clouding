# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from odoo import api, fields, models, _
import logging
_logger = logging.getLogger(__name__)

class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'
    account_id = fields.Many2one(string='Cost Center')
    project_site_id = fields.Many2one(comodel_name="account.analytic.account", string="Project/Site",
                                      domain=[('analytic_account_type', '=', 'project_site')], required=False,
                                      related='move_id.project_site_id',inverse='_set_project_site',store=True,readonly=False)
    type_id = fields.Many2one(comodel_name="account.analytic.account", string="Type",
                              domain=[('analytic_account_type', '=', 'type')], required=False,
                              related='move_id.type_id',inverse='_set_typeid',store=True,readonly=False)
    location_id = fields.Many2one(comodel_name="account.analytic.account", string="Location",
                                  domain=[('analytic_account_type', '=', 'location')], required=False,
                                  related='move_id.location_id',inverse='_set_location',store=True,readonly=False)

    def _set_project_site(self):
        _logger.info("Project/Site Changed")
    def _set_typeid(self):
        _logger.info("Type Changed")
    def _set_location(self):
        _logger.info("Location Changed")
