from odoo import models, api, fields


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    co_location_id = fields.Many2one(comodel_name="account.analytic.account",
                                     string="Co location", domain=[(
            'analytic_account_type', '=', 'co_location')], required=False, )

    def _prepare_account_move_line(self, move=False):
        self.ensure_one()
        aml_currency = move and move.currency_id or self.currency_id
        date = move and move.date or fields.Date.today()
        res = {
            'display_type': self.display_type or 'product',
            'name': '%s: %s' % (self.order_id.name, self.name),
            'product_id': self.product_id.id,
            'product_uom_id': self.product_uom.id,
            'quantity': self.qty_to_invoice,
            'discount': self.discount,
            'price_unit': self.currency_id._convert(self.price_unit, aml_currency, self.company_id, date, round=False),
            'tax_ids': [(6, 0, self.taxes_id.ids)],
            'purchase_line_id': self.id,
            'analytic_account_id':self.cost_center_id.id,
            'project_site_id': self.project_site_id.id,
            'type_id': self.type_id.id,
            'location_id': self.location_id.id,
            'co_location_id':self.co_location_id.id,
        }
        if self.analytic_distribution and not self.display_type:
            res['analytic_distribution'] = self.analytic_distribution
        return res


    # @api.onchange('project_site_id', 'cost_center_id')
    # def onchange_project_site(self):
    #     analytic_dist = {}
    #     analytic_distributions = ''
    #     if self.cost_center_id:
    #         analytic_distributions = analytic_distributions + ',' + str(
    #             self.cost_center_id.id)
    #     if self.project_site_id:
    #         analytic_distributions = analytic_distributions + ',' + str(
    #             self.project_site_id.id)
    #     if self.project_site_id.analytic_type_filter_id:
    #         analytic_distributions = analytic_distributions + ',' + str(
    #             self.project_site_id.analytic_type_filter_id.id)
    #     if self.project_site_id.analytic_location_id:
    #         analytic_distributions = analytic_distributions + ',' + str(
    #             self.project_site_id.analytic_location_id.id)
    #     if self.project_site_id.co_location:
    #         analytic_distributions = analytic_distributions + ',' + str(
    #             self.project_site_id.co_location.id)
    #     analytic_dist.update({analytic_distributions: 100})
    #     self.analytic_distribution = analytic_dist

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

    def copy(self, default=None):
        if default is None:
            default = {}
        # Call the original copy method
        order = super(PurchaseOrder, self).copy(default=default)

        # Trigger onchange for the field you want
        # Example: Assuming 'field_name' is the field you want to trigger onchange for

        for line in order.order_line.filtered(lambda x: x.project_site_id):
            line.onchange_project_site()
        return order