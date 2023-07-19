from odoo.addons.analytic_account_types.models.account_move_line import \
    AccountMove

from odoo import api, models, fields


class AccountMoveLineBudgetIndexing(models.Model):
    _inherit = 'account.move.line'

    budget_id = fields.Many2one(comodel_name="crossovered.budget",
                                string="Budget", required=False, index=True)
    budget_line_id = fields.Many2one(comodel_name="crossovered.budget.lines",
                                     string="Budget Line", required=False,
                                     index=True)


@api.depends()
def check_out_budget(self):
    self.out_budget = False
    lines = self.line_ids.filtered(lambda x: x.budget_id is False)
    if lines.filtered(
            lambda x: x.remaining_amount < x.debit or x.remaining_amount < x.credit):
        self.out_budget = True


AccountMove.check_out_budget = check_out_budget
