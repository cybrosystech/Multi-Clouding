# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class AccountAsset(models.Model):
    _inherit = 'account.asset'

    project_site_id = fields.Many2one(comodel_name="account.analytic.account",
                                      string="Project/Site",
                                      domain=[('analytic_account_type', '=',
                                               'project_site')],
                                      required=False, )
    analytic_account_id = fields.Many2one(
        comodel_name="account.analytic.account",
        string="Cost Center",
        required=False, domain=[
            ('analytic_account_type', '=',
             'cost_center')], )
    site_address = fields.Char(string='Site Address',
                               compute='compute_site_address')

    @api.depends('analytic_distribution')
    def compute_site_address(self):
        for rec in self:
            rec.site_address = False

    def action_oe_validate(self):
        if self.filtered(lambda aa: aa.state != 'draft'):
            raise UserError(_('Only draft assets can be confirm.'))
        for asset in self:
            asset.validate()

    def write(self, vals):
        res = super(AccountAsset, self).write(vals)
        if 'analytic_distribution' in vals:
            moves = self.depreciation_move_ids.filtered(
                lambda line: line.state == 'draft')
            for move in moves:
                for line in move.line_ids:
                    line.write({
                        'analytic_distribution': self.analytic_distribution if self.analytic_distribution else False,
                    })
        return res

    @api.onchange('model_id')
    def _onchange_model_id(self):
        model = self.model_id
        if model:
            self.method = model.method
            self.method_number = model.method_number
            self.method_period = model.method_period
            self.method_progress_factor = model.method_progress_factor
            self.prorata_date = fields.Date.today()
            if model.analytic_distribution:
                self.analytic_distribution = model.analytic_distribution
            self.account_asset_id = model.account_asset_id.id
            self.account_depreciation_id = model.account_depreciation_id
            self.account_depreciation_expense_id = model.account_depreciation_expense_id
            self.journal_id = model.journal_id

    @api.constrains('original_move_line_ids')
    def check_assets(self):
        for asset in self:
            for line in asset.original_move_line_ids:
                asset.analytic_distribution = line.analytic_distribution
