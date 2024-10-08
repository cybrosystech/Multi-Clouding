from odoo import models, api, fields


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    co_location_id = fields.Many2one(comodel_name="account.analytic.account",
                                     string="Co location", domain=[(
            'analytic_account_type', '=', 'co_location')], required=False, )

    def _prepare_account_move_line(self, move=False):
        res = super()._prepare_account_move_line(move)
        res.update({'analytic_account_id':self.cost_center_id.id,
            'project_site_id': self.project_site_id.id,
            'type_id': self.type_id.id,
            'location_id': self.location_id.id,
            'co_location_id':self.co_location_id.id,
            'site_status': self.site_status,
            't_budget': self.t_budget})
        return res

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
        a = analytic_distributions.strip()
        b = a.strip(",")
        analytic_dist.update({b: 100})
        self.analytic_distribution = analytic_dist


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    # def copy(self, default=None):
    #     if default is None:
    #         default = {}
    #     # Call the original copy method
    #     order = super(PurchaseOrder, self).copy(default=default)
    #
    #     # Trigger onchange for the field you want
    #     # Example: Assuming 'field_name' is the field you want to trigger onchange for
    #
    #     for line in order.order_line.filtered(lambda x: x.project_site_id):
    #         line.onchange_project_site()
    #     return order

    # @api.model_create_multi
    # def create(self, vals_list):
    #     order = super(PurchaseOrder, self).create(vals_list)
    #     for line in order.order_line.filtered(lambda x: x.project_site_id):
    #         line.onchange_project_site()
    #
    #     return order
    #
    # def write(self, vals_list):
    #     order = super(PurchaseOrder, self).write(vals_list)
    #     if self.order_line:
    #         for line in self.order_line.filtered(lambda x: x.project_site_id):
    #             line.onchange_project_site()
    #     return order