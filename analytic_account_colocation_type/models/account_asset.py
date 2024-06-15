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
