from odoo import models, fields, api


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _generate_valuation_lines_data(self, partner_id, qty, debit_value, credit_value, debit_account_id, credit_account_id, svl_id, description):
        rslt = super()._generate_valuation_lines_data(partner_id, qty, debit_value, credit_value, debit_account_id, credit_account_id, svl_id, description)
        if self.purchase_line_id:
            if self.picking_id.is_dropship and qty > 0:
                account_id = debit_account_id
            else:
                if self.t_budget == 'opex':
                    if self.project_site_id and self.project_site_id.is_inventory:
                        account_id = self.product_id.inventory_account_id.id
                    else:
                        account_id = self.product_id.property_account_expense_id.id
                elif self.t_budget == 'capex':
                    if self.project_site_id and self.project_site_id.is_inventory:
                        account_id = self.product_id.inventory_account_id.id
                    elif self.project_site_id and not self.project_site_id.is_inventory:
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

            rslt['credit_line_vals']['analytic_account_id'] = self.purchase_line_id.cost_center_id.id
            rslt['credit_line_vals']['project_site_id'] = self.purchase_line_id.project_site_id.id
            rslt['credit_line_vals']['business_unit_id'] = self.purchase_line_id.business_unit_id.id
            rslt['credit_line_vals']['analytic_distribution'] = self.purchase_line_id.analytic_distribution
            rslt['credit_line_vals']['t_budget'] = self.purchase_line_id.t_budget
            rslt['credit_line_vals']['t_budget_name'] = self.purchase_line_id.t_budget_name
            rslt['credit_line_vals']['site_status'] = self.purchase_line_id.site_status
            rslt['debit_line_vals']['analytic_account_id'] = self.purchase_line_id.cost_center_id.id
            rslt['debit_line_vals']['project_site_id'] = self.purchase_line_id.project_site_id.id
            rslt['debit_line_vals']['business_unit_id'] = self.purchase_line_id.business_unit_id.id
            rslt['debit_line_vals']['analytic_distribution'] = self.purchase_line_id.analytic_distribution
            rslt['debit_line_vals']['t_budget'] = self.purchase_line_id.t_budget
            rslt['debit_line_vals']['t_budget_name'] = self.purchase_line_id.t_budget_name
            rslt['debit_line_vals']['site_status'] = self.purchase_line_id.site_status
            rslt['debit_line_vals']['account_id'] = account_id
        else:
            if self.t_budget == 'opex':
                if self.project_site_id and self.project_site_id.is_inventory:
                    account_id = self.product_id.inventory_account_id.id
                else:
                    account_id = self.product_id.property_account_expense_id.id
            elif self.t_budget == 'capex':
                if self.project_site_id and self.project_site_id.is_inventory:
                    account_id = self.product_id.inventory_account_id.id
                elif self.project_site_id and not self.project_site_id.is_inventory:
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
            rslt['credit_line_vals']['project_site_id'] = self.project_site_id.id
            rslt['credit_line_vals']['t_budget'] = self.t_budget
            rslt['credit_line_vals']['t_budget_name'] = self.t_budget_name
            rslt['credit_line_vals']['site_status'] = self.site_status
            rslt['debit_line_vals']['project_site_id'] = self.project_site_id.id
            rslt['debit_line_vals']['t_budget'] = self.t_budget
            rslt['debit_line_vals']['t_budget_name'] = self.t_budget_name
            rslt['debit_line_vals']['site_status'] = self.site_status
            rslt['debit_line_vals']['account_id'] = account_id

        return rslt

