from odoo import models, api, fields


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    co_location_id = fields.Many2one(comodel_name="account.analytic.account",
                                     string="Co location", domain=[(
            'analytic_account_type', '=', 'co_location')], required=False, )

    def _prepare_account_move_line(self, move=False):
        res = super()._prepare_account_move_line(move)
        if self.product_id.detailed_type == 'product':
            account_id = self.product_id.categ_id.property_stock_account_input_categ_id.id
        elif self.product_id.detailed_type == 'consu' or self.product_id.detailed_type == 'service':
            if self.t_budget == 'opex':
                if self.project_site_id and self.project_site_id.is_inventory:
                    account_id = self.product_id.inventory_account_id.id
                else:
                    account_id = self.product_id.property_account_expense_id.id
            elif self.t_budget == 'capex':
                if self.project_site_id and self.project_site_id.is_inventory:
                    account_id = self.product_id.inventory_account_id.id
                elif self.project_site_id and self.project_site_id.is_inventory:
                    if self.site_status == 'off_air':
                        account_id = self.product_id.cip_account_id.id
                    elif self.site_status == 'on_air':
                        account_id = self.product_id.asset_account_id.id
                    else:
                        account_id = self.product_id.asset_account_id.id
                else:
                    if self.site_status == 'off_air':
                        account_id = self.product_id.cip_account_id.id
                    elif self.site_status == 'on_air':
                        account_id = self.product_id.asset_account_id.id
                    else:
                        account_id = self.product_id.asset_account_id.id
            else:
                account_id = self.product_id.property_account_expense_id.id
        else:
            account_id = self.product_id.property_account_expense_id.id

        res.update({'analytic_account_id':self.cost_center_id.id,
            'project_site_id': self.project_site_id.id,
            'business_unit_id':self.business_unit_id.id,
            'type_id': self.type_id.id,
            'location_id': self.location_id.id,
            'co_location_id':self.co_location_id.id,
            'site_status': self.site_status,
            't_budget': self.t_budget,
            'account_id': account_id})
        return res

    @api.onchange('project_site_id', 'cost_center_id','business_unit_id')
    def onchange_project_site(self):
        analytic_dist = {}
        analytic_distributions = ''
        if self.business_unit_id:
            analytic_distributions = analytic_distributions + ',' + str(
                self.business_unit_id.id)
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
