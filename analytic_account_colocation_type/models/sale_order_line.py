from odoo import models, api, fields


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    co_location_id = fields.Many2one(comodel_name="account.analytic.account",
                                     string="Co Location", domain=[
            ('analytic_account_type', '=', 'co_location')], required=False, )

    @api.onchange('project_site_id', 'cost_center_id')
    def onchange_project_site(self):
        analytic_dist = {}
        analytic_distributions = ''
        if self.cost_center_id:
            analytic_distributions = analytic_distributions + ',' + str(
                self.cost_center_id.id)
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
        analytic_dist.update({analytic_distributions: 100})
        self.analytic_distribution = analytic_dist

