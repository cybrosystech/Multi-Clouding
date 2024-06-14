# -*- coding: utf-8 -*-
from odoo import fields, models, _
import logging

_logger = logging.getLogger(__name__)


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    account_id = fields.Many2one(
        'account.analytic.account',
        'Cost Center',
        ondelete='restrict',
        index=True,
        check_company=True,
    )
    project_site_id = fields.Many2one(comodel_name="account.analytic.account",
                                      string="Project/Site",
                                      domain=[('analytic_account_type', '=',
                                               'project_site')], required=False,
                                      readonly=False)
    type_id = fields.Many2one(comodel_name="account.analytic.account",
                              string="Type",
                              domain=[('analytic_account_type', '=', 'type')],
                              required=False,
                              store=True, readonly=False)
    location_id = fields.Many2one(comodel_name="account.analytic.account",
                                  string="Location",
                                  domain=[('analytic_account_type', '=',
                                           'location')], required=False,
                                  readonly=False)
