from odoo import models, api, fields


class AccountAsset(models.Model):
    _inherit = 'account.asset'

    co_location = fields.Many2one('account.analytic.account',
                                  string="Co location",
                                  domain=[('analytic_account_type', '=',
                                           'co_location')],
                                  required=False)
    site_address = fields.Char(string='Site Address',
                               related='project_site_id.site_address')

    @api.model_create_multi
    def create(self, vals_list):
        asset = super(AccountAsset, self).create(vals_list)
        if asset.project_site_id or asset.analytic_account_id:
            asset.onchange_project_site()
        return asset

    def write(self, vals_list):
        asset = super().write(vals_list)
        if vals_list.get('analytic_account_id') or vals_list.get('project_site_id'):
            self.onchange_project_site()
        return asset

    def copy(self, default=None):
        if default is None:
            default = {}
        # Call the original copy method
        asset = super(AccountAsset, self).copy(default=default)

        # Trigger onchange for the field you want
        # Example: Assuming 'field_name' is the field you want to trigger onchange for
        asset.onchange_project_site()
        return asset

    @api.onchange('project_site_id', 'analytic_account_id')
    def onchange_project_site(self):
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
        a = analytic_distributions.strip()
        b = a.strip(",")
        analytic_dist.update({b: 100})
        self.analytic_distribution = analytic_dist
        if self.depreciation_move_ids:
            for mv in self.depreciation_move_ids:
                if mv.state !='posted':
                    for line in  mv.line_ids:
                        line.project_site_id = self.project_site_id.id
                        line.analytic_account_id = self.analytic_account_id