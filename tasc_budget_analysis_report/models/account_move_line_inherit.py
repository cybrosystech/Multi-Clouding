from odoo import models, api


class AccountMoveLineInherit(models.Model):
    _inherit = 'account.move.line'

    @api.onchange('account_id')
    def _onchange_account_id(self):
        res = super(AccountMoveLineInherit, self)._onchange_account_id()
        if self.account_id:
            filtered_budget = []
            budgetory_position = self.env['account.budget.post'].search([])
            filtered_budget = budgetory_position.filtered(
                lambda x: x.account_ids.filtered(
                    lambda y: y.id == self.account_id.id)).ids
            domain = [('general_budget_id', 'in', filtered_budget),
                      ('date_from', '<=', self.move_id.date),
                      ('date_to', '>=', self.move_id.date),
                      ('analytic_account_id', '=', False),
                      ('project_site_id', '=', False)]
            if self.analytic_account_id or self.project_site_id:
                domain = [('general_budget_id', 'in', filtered_budget),
                          ('date_from', '<=', self.move_id.date),
                          ('date_to', '>=', self.move_id.date)]
                if self.analytic_account_id and self.project_site_id:
                    domain += [('analytic_account_id', '=',
                                self.analytic_account_id.id),
                               (
                               'project_site_id', '=', self.project_site_id.id)]
                elif self.project_site_id:
                    domain += [('project_site_id', '=', self.project_site_id.id),
                               ('analytic_account_id', '=', False)]
                elif self.analytic_account_id:
                    domain += [('project_site_id', '=', False),
                               ('analytic_account_id', '=',
                                self.analytic_account_id.id)]
            result = self.env[
                'crossovered.budget.lines'].search(domain)
            if result:
                self.budget_id = result[0].crossovered_budget_id.id
                self.budget_line_id = result[0].id
                self.remaining_amount = result[0].remaining_amount
            else:
                if self.analytic_account_id or self.project_site_id:
                    domain = [('date_from', '<=', self.move_id.date),
                              ('date_to', '>=', self.move_id.date),
                              ('general_budget_id', 'in', filtered_budget),
                              ('project_site_id', '=', False),
                              ('analytic_account_id', '=',
                               self.analytic_account_id.id)]
                    result = self.env['crossovered.budget.lines'].search(domain)
                    if result:
                        self.budget_id = result[0].crossovered_budget_id.id
                        self.budget_line_id = result[0].id
                        self.remaining_amount = result[0].remaining_amount
                    else:
                        domain = [('date_from', '<=', self.move_id.date),
                                  ('date_to', '>=', self.move_id.date),
                                  ('general_budget_id', 'in', filtered_budget),
                                  ('project_site_id', '=', self.project_site_id.id),
                                  ('analytic_account_id', '=',
                                   False)]
                        result = self.env['crossovered.budget.lines'].search(domain)
                        if result:
                            self.budget_id = result[0].crossovered_budget_id.id
                            self.budget_line_id = result[0].id
                            self.remaining_amount = result[0].remaining_amount
                        else:
                            self.budget_id = ''
                            self.budget_line_id = ''
                            self.remaining_amount = 0
                else:
                    self.budget_id = ''
                    self.budget_line_id = ''
                    self.remaining_amount = 0
        return res

    @api.onchange('project_site_id', 'analytic_account_id')
    def _onchange_analytic_account_id(self):
        if self.account_id or self.analytic_account_id or self.project_site_id:
            filtered_budget = []
            domain = [('date_from', '<=', self.move_id.date),
                      ('date_to', '>=', self.move_id.date)]
            if self.account_id:
                budgetory_position = self.env['account.budget.post'].search([])
                filtered_budget = budgetory_position.filtered(
                    lambda x: x.account_ids.filtered(
                        lambda y: y.id == self.account_id.id)).ids
                domain += [('general_budget_id', 'in', filtered_budget)]
            if self.analytic_account_id and self.project_site_id:
                domain += [('analytic_account_id', '=',
                            self.analytic_account_id.id),
                           ('project_site_id', '=', self.project_site_id.id)]
            elif self.project_site_id:
                domain += [('project_site_id', '=', self.project_site_id.id),
                           ('analytic_account_id', '=', False)]
            elif self.analytic_account_id:
                domain += [('project_site_id', '=', False),
                           ('analytic_account_id', '=',
                            self.analytic_account_id.id)]
            result = self.env['crossovered.budget.lines'].search(domain)
            if result:
                self.budget_id = result[0].crossovered_budget_id.id
                self.budget_line_id = result[0].id
                self.remaining_amount = result[0].remaining_amount
            else:
                domain = [('date_from', '<=', self.move_id.date),
                          ('date_to', '>=', self.move_id.date),
                          ('general_budget_id', 'in', filtered_budget),
                          ('project_site_id', '=', False),
                          ('analytic_account_id', '=',
                           self.analytic_account_id.id)]
                result = self.env['crossovered.budget.lines'].search(domain)
                if result:
                    self.budget_id = result[0].crossovered_budget_id.id
                    self.budget_line_id = result[0].id
                    self.remaining_amount = result[0].remaining_amount
                else:
                    domain = [('date_from', '<=', self.move_id.date),
                              ('date_to', '>=', self.move_id.date),
                              ('general_budget_id', 'in', filtered_budget),
                              ('project_site_id', '=', self.project_site_id.id),
                              ('analytic_account_id', '=',
                               False)]
                    result = self.env['crossovered.budget.lines'].search(domain)
                    if result:
                        self.budget_id = result[0].crossovered_budget_id.id
                        self.budget_line_id = result[0].id
                        self.remaining_amount = result[0].remaining_amount
                    else:
                        domain = [('date_from', '<=', self.move_id.date),
                                  ('date_to', '>=', self.move_id.date),
                                  ('general_budget_id', 'in',
                                   filtered_budget),
                                  ('project_site_id', '=', False),
                                  ('analytic_account_id', '=',
                                   False)]
                        result = self.env['crossovered.budget.lines'].search(
                            domain)
                        if result:
                            self.budget_id = result[0].crossovered_budget_id.id
                            self.budget_line_id = result[0].id
                            self.remaining_amount = result[0].remaining_amount
                        else:
                            self.budget_id = ''
                            self.budget_line_id = ''
                            self.remaining_amount = 0
