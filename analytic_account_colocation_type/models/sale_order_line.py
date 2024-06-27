from odoo import models, api, fields
from odoo.fields import Command
from odoo.tools import frozendict


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # @api.model_create_multi
    # def create(self, vals_list):
    #     order = super(SaleOrder, self).create(vals_list)
    #     for line in order.order_line.filtered(lambda x: x.project_site_id):
    #         line.onchange_project_site()
    #
    #     return order
    #
    # def write(self, vals_list):
    #     order = super(SaleOrder, self).write(vals_list)
    #     if self.order_line:
    #         for line in self.order_line.filtered(lambda x: x.project_site_id):
    #             line.onchange_project_site()
    #     return order
    #
    # def copy(self, default=None):
    #     if default is None:
    #         default = {}
    #     # Call the original copy method
    #     order = super(SaleOrder, self).copy(default=default)
    #
    #     # Trigger onchange for the field you want
    #     # Example: Assuming 'field_name' is the field you want to trigger onchange for
    #     # order.order_line.filtered(lambda x: x.project_site_id).onchange_project_site()
    #     for line in order.order_line.filtered(lambda x: x.project_site_id):
    #         line.onchange_project_site()
    #     return order

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    co_location_id = fields.Many2one(comodel_name="account.analytic.account",
                                     string="Co Location", domain=[
            ('analytic_account_type', '=', 'co_location')], required=False, )

    def _prepare_invoice_line(self, **optional_values):
        res = super(SaleOrderLine, self)._prepare_invoice_line(
            **optional_values)
        res.update({
            'budget_id': self.budget_id.id,
            'analytic_account_id': self.cost_center_id.id,
            'project_site_id': self.project_site_id.id,
            'type_id': self.type_id.id,
            'location_id': self.location_id.id,
            'co_location_id': self.co_location_id.id,
        })
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
        analytic_dist.update({analytic_distributions: 100})
        self.analytic_distribution = analytic_dist


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = 'sale.advance.payment.inv'

    def _prepare_down_payment_lines_values(self, order):
        """ Create one down payment line per tax or unique taxes combination.
            Apply the tax(es) to their respective lines.

            :param order: Order for which the down payment lines are created.
            :return:      An array of dicts with the down payment lines values.
        """
        self.ensure_one()

        if self.advance_payment_method == 'percentage':
            percentage = self.amount / 100
        else:
            percentage = self.fixed_amount / order.amount_total if order.amount_total else 1

        order_lines = order.order_line.filtered(lambda l: not l.display_type)
        base_downpayment_lines_values = self._prepare_base_downpayment_line_values(
            order)

        tax_base_line_dicts = [
            line._convert_to_tax_base_line_dict(
                analytic_distribution=line.analytic_distribution,
                handle_price_include=False
            )
            for line in order_lines
        ]
        computed_taxes = self.env['account.tax']._compute_taxes(
            tax_base_line_dicts)
        down_payment_values = []
        for line, tax_repartition in computed_taxes['base_lines_to_update']:
            taxes = line['taxes'].flatten_taxes_hierarchy()
            fixed_taxes = taxes.filtered(lambda tax: tax.amount_type == 'fixed')
            down_payment_values.append([
                taxes - fixed_taxes,
                line['analytic_distribution'],
                tax_repartition['price_subtotal'],
                line['record'].project_site_id.id,
                line['record'].cost_center_id.id,
                line['record'].type_id.id,
                line['record'].location_id.id,
                line['record'].co_location_id.id,
            ])
            for fixed_tax in fixed_taxes:
                # Fixed taxes cannot be set as taxes on down payments as they always amounts to 100%
                # of the tax amount. Therefore fixed taxes are removed and are replace by a new line
                # with appropriate amount, and non fixed taxes if the fixed tax affected the base of
                # any other non fixed tax.
                if fixed_tax.include_base_amount:
                    pct_tax = taxes[list(taxes).index(fixed_tax) + 1:] \
                        .filtered(lambda
                                      t: t.is_base_affected and t.amount_type != 'fixed')
                else:
                    pct_tax = self.env['account.tax']
                down_payment_values.append([
                    pct_tax,
                    line['analytic_distribution'],
                    line['quantity'] * fixed_tax.amount
                ])

        downpayment_line_map = {}
        for tax_id, analytic_distribution, price_subtotal, proejct_site, cost_center, type, location, co_location in down_payment_values:
            grouping_key = frozendict({
                'tax_id': tuple(sorted(tax_id.ids)),
                'analytic_distribution': analytic_distribution,
                'project_site_id': proejct_site,
                'cost_center_id': cost_center,
                'type_id': type,
                'location_id': location,
                'co_location_id': co_location,
            })
            downpayment_line_map.setdefault(grouping_key, {
                **base_downpayment_lines_values,
                **grouping_key,
                'product_uom_qty': 0.0,
                'price_unit': 0.0,
            })
            downpayment_line_map[grouping_key]['price_unit'] += \
                order.currency_id.round(price_subtotal * percentage)
        return list(downpayment_line_map.values())
