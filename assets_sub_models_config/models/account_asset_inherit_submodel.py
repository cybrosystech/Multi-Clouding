from odoo import models, fields, api
import logging
_logger = logging.getLogger(__name__)


class AccountAssetSubModel(models.Model):
    _inherit = 'account.asset'

    asset_sub_model_id = fields.Many2one('assets.sub.model', tracking=True)

    @api.onchange('model_id')
    def _onchange_model_id(self):
        model = self.model_id
        if model:
            _logger.info("mmmmmmmm")

            self.method = model.method
            self.method_number = model.method_number
            self.method_period = model.method_period
            self.method_progress_factor = model.method_progress_factor
            self.prorata = model.prorata
            self.prorata_date = fields.Date.today()
            if model.account_analytic_id:
                self.account_analytic_id = model.account_analytic_id.id
            if model.project_site_id:
                self.project_site_id = model.project_site_id.id
            if model.type_id:
                self.type_id = model.type_id.id
            if model.location_id:
                self.location_id = model.location_id.id
            self.analytic_tag_ids = [(6, 0, model.analytic_tag_ids.ids)]
            self.account_asset_id = model.account_asset_id.id
            self.account_depreciation_id = model.account_depreciation_id
            self.account_depreciation_expense_id = model.account_depreciation_expense_id
            self.journal_id = model.journal_id
            return {'domain': {'asset_sub_model_id': [('asset_model_id', '=', model.id)]}}
