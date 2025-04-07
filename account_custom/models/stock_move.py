from odoo import models, fields, api


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _generate_valuation_lines_data(self, partner_id, qty, debit_value, credit_value, debit_account_id, credit_account_id, svl_id, description):
        rslt = super()._generate_valuation_lines_data(partner_id, qty, debit_value, credit_value, debit_account_id, credit_account_id, svl_id, description)
        if self.purchase_line_id:
            rslt['credit_line_vals']['analytic_account_id'] = self.purchase_line_id.cost_center_id.id
            rslt['credit_line_vals']['project_site_id'] = self.purchase_line_id.project_site_id.id
            rslt['credit_line_vals']['business_unit_id'] = self.purchase_line_id.business_unit_id.id
            rslt['credit_line_vals']['analytic_distribution'] = self.purchase_line_id.analytic_distribution
            rslt['debit_line_vals']['analytic_account_id'] = self.purchase_line_id.cost_center_id.id
            rslt['debit_line_vals']['project_site_id'] = self.purchase_line_id.project_site_id.id
            rslt['debit_line_vals']['business_unit_id'] = self.purchase_line_id.business_unit_id.id
            rslt['debit_line_vals']['analytic_distribution'] = self.purchase_line_id.analytic_distribution
        return rslt

