from odoo import models, fields


class PurchaseOrderInheritApproval(models.Model):
    _inherit = 'purchase.order'

    request_approve_bool = fields.Boolean(default=False)

    def request_approval_button(self):
        self.get_budgets_in_out_budget_tab()
        if self.out_budget and not self.purchase_approval_cycle_ids:
            out_budget_list = []
            out_budget = self.env['budget.in.out.check'].search(
                [('type', '=', 'out_budget'),
                 ('company_id', '=', self.env.company.id)], limit=1)
            if self.budget_collect_ids.mapped('demand_amount'):
                max_value = max(self.budget_collect_ids.mapped('demand_amount'))
            else:
                max_value = 0
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
            in_budget = self.env['budget.in.out.check'].search(
                [('type', '=', 'in_budget'),
                 ('company_id', '=', self.env.company.id)], limit=1)
            max_value = max(self.order_line.mapped(
                'local_subtotal'))  # Old Field is amount_total
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
            self.send_user_notification(user)
            self.state = 'to_approve'
            self.request_approve_bool = True
        else:
            self.show_button_confirm = True
            self.request_approve_bool = True

    def button_draft(self):
        res = super(PurchaseOrderInheritApproval, self).button_draft()
        self.request_approve_bool = False
        return res


class SaleOrderRequestApproval(models.Model):
    _inherit = 'sale.order'

    request_approve_bool = fields.Boolean(default=False)

    def request_approval_button(self):
        self.get_budgets_in_out_budget_tab()
        if self.out_budget and not self.sale_approval_cycle_ids:
            out_budget_list = []
            out_budget = self.env['budget.in.out.check.sales'].search(
                [('type', '=', 'out_budget'),
                 ('company_id', '=', self.env.company.id)], limit=1)
            if self.budget_collect_ids.mapped('demand_amount'):
                max_value = max(self.budget_collect_ids.mapped('demand_amount'))

            else:
                max_value = 0
            for rec in out_budget.budget_line_ids:
                if max_value >= rec.from_amount:
                    out_budget_list.append((0, 0, {
                        'approval_seq': rec.approval_seq,
                        'user_approve_ids': rec.user_ids.ids,
                    }))
        self.request_approve_bool = True

    def action_draft(self):
        res = super(SaleOrderRequestApproval, self).action_draft()
        self.request_approve_bool = False
        return res
