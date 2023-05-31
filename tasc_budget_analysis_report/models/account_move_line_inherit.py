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


def request_approval_button(self):
    self.configure_budget_line()
    lines = self.line_ids.filtered(
        lambda x: x.remaining_amount < x.debit or x.remaining_amount < x.credit)
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
    self.get_budgets_in_out_budget_tab()
    if self.out_budget and not self.purchase_approval_cycle_ids:
        out_budget_list = []
        out_budget = self.env['budget.in.out.check.invoice'].search(
            [('type', '=', 'out_budget'),
             ('company_id', '=', self.env.company.id)], limit=1)
        if self.budget_collect_ids:
            max_value = max(self.budget_collect_ids.mapped('demand_amount'))
        else:
            max_value = max(self.budget_collect_copy_ids.mapped('demand_amount_copy'))
        for rec in out_budget.budget_line_ids:
            if max_value >= rec.from_amount:
                out_budget_list.append((0, 0, {
                    'approval_seq': rec.approval_seq,
                    'user_approve_ids': rec.user_ids.ids,
                }))

        self.write({'purchase_approval_cycle_ids': out_budget_list})
        self.request_approve_bool = True
    if not self.out_budget and not self.purchase_approval_cycle_ids:
        in_budget_list = []
        in_budget = self.env['budget.in.out.check.invoice'].search(
            [('type', '=', 'in_budget'),
             ('company_id', '=', self.env.company.id)], limit=1)
        if self.move_type == 'entry':
            max_value = sum(self.line_ids.mapped('debit'))  # Old Field is debit
        else:
            max_value = sum(self.invoice_line_ids.mapped('local_subtotal'))
        for rec in in_budget.budget_line_ids:
            if max_value >= rec.from_amount:
                in_budget_list.append((0, 0, {
                    'approval_seq': rec.approval_seq,
                    'user_approve_ids': rec.user_ids.ids,
                }))

        self.write({'purchase_approval_cycle_ids': in_budget_list})
        self.request_approve_bool = True
    self.show_request_approve_button = True
    if self.purchase_approval_cycle_ids:
        min_seq_approval = min(
            self.purchase_approval_cycle_ids.mapped('approval_seq'))
        notification_to_user = self.purchase_approval_cycle_ids.filtered(
            lambda x: x.approval_seq == int(min_seq_approval))
        user = notification_to_user.user_approve_ids
        self.state = 'to_approve'
        self.send_user_notification(user)
        self.request_approve_bool = True


AccountMoveInherit.request_approval_button = request_approval_button
