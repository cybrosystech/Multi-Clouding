from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class AccountAssetSubModel(models.Model):
    _inherit = 'account.asset'

    value_residual_original = fields.Monetary(compute='check_value_residual')
    model_id = fields.Many2one('account.asset', string='Model',
                               change_default=True)
    asset_sub_models_ids = fields.Many2many('assets.sub.model',
                                            compute='compute_asset_sub_models_ids')

    asset_sub_model_id = fields.Many2one('assets.sub.model', tracking=True,
                                         domain="[('id','in',asset_sub_models_ids)]")
    prorata_date = fields.Date(
        string='Prorata Date',
        compute='_compute_prorata_date', store=True, readonly=False,
        help='Starting date of the period used in the prorata calculation of the first depreciation',
        required=False, precompute=True,
        copy=True,
    )

    @api.depends('model_id')
    def compute_asset_sub_models_ids(self):
        for rec in self:
            if rec.model_id:
                asset_sub_models = self.env['assets.sub.model'].sudo().search([])
                sub_models = asset_sub_models.sudo().filtered(
                    lambda x: self.model_id.id in x.asset_model_id.ids)
                rec.asset_sub_models_ids = sub_models.ids
            else:
                rec.asset_sub_models_ids = False

    @api.depends()
    def check_value_residual(self):
        for rec in self:
            depreciation_lines = rec.depreciation_move_ids.filtered(
                lambda x: x.state == 'posted')
            if depreciation_lines:
                rec.value_residual_original = rec.original_value - sum(
                    depreciation_lines.mapped('amount_total'))
            else:
                rec.value_residual_original = rec.original_value

    @api.onchange('model_id')
    def _onchange_model_id(self):
        model = self.model_id
        if model:
            _logger.info("mmmmmmmm")
            self.method = model.method
            self.method_number = model.method_number
            self.method_period = model.method_period
            self.method_progress_factor = model.method_progress_factor
            self.prorata_computation_type = model.prorata_computation_type
            if not self.env.context.get('auto_create_asset'):
                self.prorata_date = fields.Date.today()
                self.analytic_account_id = model.analytic_account_id.id
                self.project_site_id = model.project_site_id.id
                self.business_unit_id = model.business_unit_id.id
                if model.analytic_distribution:
                    self.analytic_distribution = model.analytic_distribution
            self.account_asset_id = model.account_asset_id.id
            self.account_depreciation_id = model.account_depreciation_id
            self.account_depreciation_expense_id = model.account_depreciation_expense_id
            self.journal_id = model.journal_id

            return {'domain': {
                'asset_sub_model_id': [('asset_model_id', '=', model.id)]}}
