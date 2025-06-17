from odoo import fields,models,_
from odoo.addons.stock_landed_costs.models.stock_landed_cost import AdjustmentLines

def _create_account_move_line(self, move, credit_account_id, debit_account_id, qty_out, already_out_account_id):
    """
    Generate the account.move.line values to track the landed cost.
    Afterwards, for the goods that are already out of stock, we should create the out moves
    """
    AccountMoveLine = []

    base_line = {
        'name': self.name,
        'product_id': self.product_id.id,
        'quantity': 0,
    }
    debit_line = dict(base_line, account_id=debit_account_id)
    credit_line = dict(base_line, account_id=credit_account_id)
    credit_line["t_budget"] = self.move_id.t_budget
    credit_line["analytic_account_id"] = self.move_id.purchase_line_id.cost_center_id.id
    credit_line["t_budget_name"] = self.move_id.t_budget_name
    credit_line["site_status"] = self.move_id.site_status
    credit_line["project_site_id"] = self.move_id.project_site_id.id
    debit_line["t_budget"] = self.move_id.t_budget
    debit_line["t_budget_name"] = self.move_id.t_budget_name
    debit_line["site_status"] = self.move_id.site_status
    debit_line["project_site_id"] = self.move_id.project_site_id.id
    debit_line["analytic_account_id"] = self.move_id.purchase_line_id.cost_center_id.id


    diff = self.additional_landed_cost
    if diff > 0:
        debit_line['debit'] = diff
        credit_line['credit'] = diff
    else:
        # negative cost, reverse the entry
        debit_line['credit'] = -diff
        credit_line['debit'] = -diff
    AccountMoveLine.append([0, 0, debit_line])
    AccountMoveLine.append([0, 0, credit_line])

    # Create account move lines for quants already out of stock
    if qty_out > 0:
        debit_line = dict(base_line,
                          name=(self.name + ": " + str(qty_out) + _(' already out')),
                          quantity=0,
                          account_id=already_out_account_id)
        credit_line = dict(base_line,
                           name=(self.name + ": " + str(qty_out) + _(' already out')),
                           quantity=0,
                           account_id=debit_account_id)
        diff = diff * qty_out / self.quantity
        if diff > 0:
            debit_line['debit'] = diff
            credit_line['credit'] = diff
        else:
            # negative cost, reverse the entry
            debit_line['credit'] = -diff
            credit_line['debit'] = -diff
        AccountMoveLine.append([0, 0, debit_line])
        AccountMoveLine.append([0, 0, credit_line])

        if self.env.company.anglo_saxon_accounting:
            expense_account_id = self.product_id.product_tmpl_id.get_product_accounts()['expense'].id
            debit_line = dict(base_line,
                              name=(self.name + ": " + str(qty_out) + _(' already out')),
                              quantity=0,
                              account_id=expense_account_id)
            credit_line = dict(base_line,
                               name=(self.name + ": " + str(qty_out) + _(' already out')),
                               quantity=0,
                               account_id=already_out_account_id)

            if diff > 0:
                debit_line['debit'] = diff
                credit_line['credit'] = diff
            else:
                # negative cost, reverse the entry
                debit_line['credit'] = -diff
                credit_line['debit'] = -diff
            AccountMoveLine.append([0, 0, debit_line])
            AccountMoveLine.append([0, 0, credit_line])

    return AccountMoveLine

AdjustmentLines._create_account_move_line = _create_account_move_line