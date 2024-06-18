from odoo import models, api, fields


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    co_location_id = fields.Many2one(comodel_name="account.analytic.account",
                                     string="Co location", domain=[(
            'analytic_account_type', '=', 'co_location')], required=False, )

    @api.onchange('project_site_id')
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


class AccountMove(models.Model):
    _inherit = 'account.move'

    def copy(self, default=None):
        if default is None:
            default = {}
        # Call the original copy method
        move = super(AccountMove, self).copy(default=default)

        # Trigger onchange for the field you want
        # Example: Assuming 'field_name' is the field you want to trigger onchange for
        if move.invoice_line_ids:
            for line in move.invoice_line_ids.filtered(lambda x: x.project_site_id):
                line.onchange_project_site()

        if move.line_ids:
            for line in move.line_ids.filtered(
                    lambda x: x.project_site_id):
                line.onchange_project_site()
        return move
