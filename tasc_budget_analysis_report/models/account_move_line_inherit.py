from odoo import models, api, fields
from odoo.addons.approve_status.model.account_move_inherit import \
    AccountMoveInherit


class AccountMoveBudgetConf(models.Model):
    _inherit = 'account.move'

    budget_collect_copy_ids = fields.One2many(
        comodel_name="budget.collect.copy",
        inverse_name="move_id", string="",
        required=False, )
    leasee_contract_id = fields.Many2one(comodel_name="leasee.contract",
                                         index=True)

    def configure_budget_line(self):
        if self.line_ids:
            for line in self.line_ids:
                if line.account_id or line.analytic_account_id or line.project_site_id:
                    budgetory_position = self.env['account.budget.post'].search(
                        [])
                    filtered_budget = budgetory_position.filtered(
                        lambda x: x.account_ids.filtered(
                            lambda y: y.id == line.account_id.id)).ids
                    domain = [('date_from', '<=', line.move_id.date),
                              ('date_to', '>=', line.move_id.date),
                              ('general_budget_id', 'in', filtered_budget),
                              ('project_site_id', '=', line.project_site_id.id),
                              ('analytic_account_id', '=',
                               line.analytic_account_id.id)]
                    result = line.env['crossovered.budget.lines'].search(domain)
                    if result:
                        line.budget_id = result[0].crossovered_budget_id.id
                        line.budget_line_id = result[0].id
                        line.remaining_amount = result[0].remaining_amount
                    else:
                        domain = [('date_from', '<=', line.move_id.date),
                                  ('date_to', '>=', line.move_id.date),
                                  ('general_budget_id', 'in', filtered_budget),
                                  ('project_site_id', '=',
                                   False),
                                  ('analytic_account_id', '=',
                                   line.analytic_account_id.id)]
                        result = line.env['crossovered.budget.lines'].search(
                            domain)
                        if result:
                            line.budget_id = result[0].crossovered_budget_id.id
                            line.budget_line_id = result[0].id
                            line.remaining_amount = result[0].remaining_amount
                        else:
                            domain = [('date_from', '<=', line.move_id.date),
                                      ('date_to', '>=', line.move_id.date),
                                      ('general_budget_id', 'in',
                                       filtered_budget),
                                      ('project_site_id', '=',
                                       line.project_site_id.id),
                                      ('analytic_account_id', '=',
                                       False)]
                            result = line.env[
                                'crossovered.budget.lines'].search(domain)
                            if result:
                                line.budget_id = result[
                                    0].crossovered_budget_id.id
                                line.budget_line_id = result[0].id
                                line.remaining_amount = result[
                                    0].remaining_amount
                            else:
                                domain = [
                                    ('date_from', '<=', line.move_id.date),
                                    ('date_to', '>=', line.move_id.date),
                                    ('general_budget_id', 'in',
                                     filtered_budget),
                                    ('project_site_id', '=',
                                     False),
                                    ('analytic_account_id', '=',
                                     False)]
                                result = line.env[
                                    'crossovered.budget.lines'].search(domain)
                                if result:
                                    line.budget_id = result[
                                        0].crossovered_budget_id.id
                                    line.budget_line_id = result[0].id
                                    line.remaining_amount = result[
                                        0].remaining_amount


class AccountMoveRequest(AccountMoveInherit):

    def request_approval_button(self):
        res = super(AccountMoveRequest, self).request_approval_button()
        lines = self.line_ids.filtered(lambda x: x.remaining_amount < x.debit or x.remaining_amount < x.credit)
        self.budget_collect_copy_ids = [(6, 0, [])]
        for line in lines:
            if line.budget_id:
                self.env['budget.collect.copy'].create({
                    'budget_id': line.budget_id.id,
                    'budget_line_id': line.budget_line_id.id,
                    'remaining_amount_copy': line.remaining_amount,
                    'demand_amount_copy': line.debit,
                    'difference_amount_copy': line.remaining_amount - line.debit,
                    'move_id': self.id
                })
        return res
