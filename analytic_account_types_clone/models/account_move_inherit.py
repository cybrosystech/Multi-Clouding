from odoo.addons.analytic_account_types.models.account_move_line import \
    AccountMove
from odoo.exceptions import UserError

from odoo import api, models, fields


class AccountMoveLineBudgetIndexing(models.Model):
    _inherit = 'account.move.line'

    budget_id = fields.Many2one(comodel_name="crossovered.budget",
                                string="Budget", required=False, index=True,
                                copy=False)
    budget_line_id = fields.Many2one(comodel_name="crossovered.budget.lines",
                                     string="Budget Line", required=False,
                                     index=True, copy=False)


@api.depends()
def check_out_budget(self):
    self.out_budget = False
    lines = self.line_ids.filtered(lambda x: x.budget_id is False)
    if lines.filtered(
            lambda x: x.remaining_amount < x.debit or x.remaining_amount < x.credit):
        self.out_budget = True


def button_approve_purchase_cycle(self):
    for journal in self:
        min_seq_approval = min(
            journal.purchase_approval_cycle_ids.filtered(
                lambda x: x.is_approved is not True).mapped('approval_seq'))
        last_approval = journal.purchase_approval_cycle_ids.filtered(
            lambda x: x.approval_seq == int(min_seq_approval))
        if journal.env.user not in last_approval.user_approve_ids:
            raise UserError(
                'You cannot approve this record' + ' ' + str(journal.name))
        last_approval.is_approved = True
        journal.send_user_notification(last_approval.user_approve_ids)
        if not journal.purchase_approval_cycle_ids.filtered(
                lambda x: x.is_approved is False):
            journal.action_post()
        message = 'Level ' + str(
            last_approval.approval_seq) + ' Approved by :' + str(
            journal.env.user.name)
        journal.message_post(body=message)


AccountMove.button_approve_purchase_cycle = button_approve_purchase_cycle

AccountMove.check_out_budget = check_out_budget
