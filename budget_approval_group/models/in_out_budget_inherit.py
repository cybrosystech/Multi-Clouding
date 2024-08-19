from odoo import models, api, fields, _
from odoo.addons.account.models.account_move import AccountMove

from odoo.exceptions import UserError


def button_cancel(self):
    # Shortcut to move from posted to cancelled directly. This is useful for E-invoices that must not be changed
    # when sent to the government.
    moves_to_reset_draft = self.filtered(lambda x: x.state == 'posted')
    if moves_to_reset_draft:
        moves_to_reset_draft.button_draft()

    if any(move.state not in ['draft', 'to_approve'] for move in self):
        raise UserError(_("Only draft journal entries can be cancelled."))

    self.write(
        {'auto_post': 'no', 'state': 'cancel', 'request_approve_bool': False,
         'purchase_approval_cycle_ids': [(5, 0, 0)]
         })


AccountMove.button_cancel = button_cancel


class BudgetInOutLinesInvoicesInherit(models.Model):
    _inherit = 'budget.in.out.check.invoice'

    def user_group_update(self):
        budget_invoices = self.env['budget.in.out.check.invoice'].search(
            []).mapped(lambda x: x.budget_line_ids.user_ids)
        budget_purchase = self.env['budget.in.out.check'].search([]).mapped(
            lambda x: x.budget_line_ids.user_ids)
        budget_sales = self.env['budget.in.out.check.sales'].search([]).mapped(
            lambda x: x.budget_line_ids.user_ids)
        invoce_user_ids = [i.id for i in budget_invoices]
        purchase_user_ids = [i.id for i in budget_purchase]
        sales_user_ids = [i.id for i in budget_sales]
        invoce_user_ids = invoce_user_ids + purchase_user_ids + sales_user_ids
        group = self.env.ref(
            'budget_approval_group.group_budget_check_approver')
        res_users = self.env['res.users'].search(
            [('id', 'in', invoce_user_ids)]).mapped('id')
        group_users = [i.id for i in group.mapped('users')]
        for i in res_users:
            if i in group_users:
                res_users.remove(i)
        group.update({
            'users': [(4, user_id) for user_id in res_users]
        })


class AccountMoveCustom(models.Model):
    _inherit = 'account.move'

    is_reset_to_draft_show = fields.Boolean(
        compute='compute_is_reset_to_draft_show'
        )

    @api.depends('state', 'payment_state', 'deferred_move_ids', 'asset_ids')
    def compute_is_reset_to_draft_show(self):
        for rec in self:
            if self.env.user.user_has_groups(
                    'budget_approval_group.group_budget_check_approver') and rec.state in [
                'posted',
                'to_approve'] and not rec.deferred_move_ids and not rec.asset_ids:
                if rec.move_type == 'entry':
                    rec.is_reset_to_draft_show = True
                elif rec.payment_state in ['not_paid']:
                    rec.is_reset_to_draft_show = True
                else:
                    rec.is_reset_to_draft_show = False

            else:
                if rec.move_type == 'entry':
                    rec.is_reset_to_draft_show = True
                elif rec.payment_state in ['not_paid']:
                    rec.is_reset_to_draft_show = True
                else:
                    rec.is_reset_to_draft_show = False
