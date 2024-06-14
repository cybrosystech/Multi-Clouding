from odoo import models, api, fields


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


class AccountMove(models.Model):
    _inherit = 'account.move'

    is_reset_to_draft_show = fields.Boolean(
        compute='compute_is_reset_to_draft_show')

    @api.depends('state')
    def compute_is_reset_to_draft_show(self):
        for rec in self:
            if self.env.user.user_has_groups(
                    'budget_approval_group.group_budget_check_approver') and rec.state == 'posted':
                rec.is_reset_to_draft_show = True
            else:
                rec.is_reset_to_draft_show = False
