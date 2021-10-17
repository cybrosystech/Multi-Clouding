# -*- coding: utf-8 -*-

from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    budget_collect_ids = fields.One2many(comodel_name="budget.collect", inverse_name="sale_id", string="",
                                         required=False, )
    sale_approval_cycle_ids = fields.One2many(comodel_name="purchase.approval.cycle", inverse_name="sale_id",
                                                  string="", required=False, )
    out_budget = fields.Boolean(string="Out Budget", compute="check_out_budget")
    show_approve_button = fields.Boolean(string="", compute='check_show_approve_button')
    show_request_approve_button = fields.Boolean(string="", )
    show_button_confirm = fields.Boolean(string="", )
    mail_link = fields.Text(string="", required=False, )
    state = fields.Selection(selection_add=[('to_approve', 'To Approve'),('sent',), ], ondelete={'to_approve': 'set default','draft': 'set default',})


    def action_cancel(self):
        res = super(SaleOrder, self).action_cancel()
        self.sale_approval_cycle_ids = False
        return res

    def action_draft(self):
        res = super(SaleOrder, self).action_draft()
        self.show_request_approve_button = False
        return res

    @api.depends()
    def check_show_approve_button(self):
        self.show_approve_button = False
        current_approve = self.sale_approval_cycle_ids.filtered(lambda x:x.is_approved).mapped('approval_seq')

        last_approval = max(current_approve) if current_approve else 0
        check_last_approval_is_approved = self.sale_approval_cycle_ids.filtered(lambda x: x.approval_seq == int(last_approval))
        for rec in self.sale_approval_cycle_ids:
            if check_last_approval_is_approved:
                if not rec.is_approved and self.env.user.id in rec.user_approve_ids.ids and check_last_approval_is_approved.is_approved:
                    self.show_approve_button = True
                    break
            else:
                if not rec.is_approved and self.env.user.id in rec.user_approve_ids.ids:
                    self.show_approve_button = True
                    break
                break

    @api.depends('budget_collect_ids')
    def check_out_budget(self):
        self.out_budget = False
        out_budget = self.budget_collect_ids.filtered(lambda x: x.difference_amount > 0)
        if out_budget:
            self.out_budget = True

    @api.onchange('order_line')
    def get_budgets_in_out_budget_tab(self):
        self.budget_collect_ids = False
        budgets = self.order_line.mapped('budget_id')
        budget_lines = []
        budgets = set(budgets)
        for bud in budgets:
            if bud not in self.budget_collect_ids.mapped('budget_id'):
                budget_lines.append((0, 0, {
                    'budget_id': bud.id
                }))
        self.write({'budget_collect_ids': budget_lines})
        # self.budget_collect_ids = budget_lines

    def send_user_notification(self, user):
        for use in user:
            reseiver = use.partner_id
            if reseiver:
                for purchase in self:
                    thread_pool = self.sudo().env['mail.thread']
                    thread_pool.message_notify(
                        partner_ids=[reseiver.id],
                        subject=str('Sales Approval Needed'),
                        body=str('This Sale Order ' + str(
                            purchase.name) + ' Need Your Approval ') + ' click here to open: <a target=_BLANK href="/web?#id=' + str(
                            purchase.id) + '&view_type=form&model=sale.order&action=" style="font-weight: bold">' + str(
                            purchase.name) + '</a>',
                        email_from=self.env.user.company_id.catchall_formatted or self.env.user.company_id.email_formatted, )
                    email_template_id = self.env.ref('analytic_account_types.email_template_send_mail_approval_sales')
                    ctx = self._context.copy()
                    ctx.update({'name': use.name})
                    if email_template_id:
                        email_template_id.with_context(ctx).send_mail(self.id, email_values={'email_to': use.email, })

    def request_approval_button(self):
        if self.out_budget and not self.sale_approval_cycle_ids:
            out_budget_list = []
            out_budget = self.env['budget.in.out.check.sales'].search([('type', '=', 'out_budget')], limit=1)
            if self.budget_collect_ids.mapped('difference_amount'):
                max_value = max(self.budget_collect_ids.mapped('difference_amount'))
            else:
                max_value = 0
            for rec in out_budget.budget_line_ids:
                if rec.to_amount >= max_value >= rec.from_amount:
                    out_budget_list.append((0, 0, {
                        'approval_seq': rec.approval_seq,
                        'user_approve_ids': rec.user_ids.ids,
                    }))
                elif rec.to_amount <= max_value >= rec.from_amount:
                    out_budget_list.append((0, 0, {
                        'approval_seq': rec.approval_seq,
                        'user_approve_ids': rec.user_ids.ids,
                    }))
            self.write({'sale_approval_cycle_ids': out_budget_list})
        if not self.out_budget and not self.sale_approval_cycle_ids:
            in_budget_list = []
            in_budget = self.env['budget.in.out.check.sales'].search([('type', '=', 'in_budget')], limit=1)
            max_value = self.amount_total
            for rec in in_budget.budget_line_ids:
                if rec.to_amount >= max_value >= rec.from_amount:
                    in_budget_list.append((0, 0, {
                        'approval_seq': rec.approval_seq,
                        'user_approve_ids': rec.user_ids.ids,
                    }))
                elif rec.to_amount <= max_value >= rec.from_amount:
                    in_budget_list.append((0, 0, {
                        'approval_seq': rec.approval_seq,
                        'user_approve_ids': rec.user_ids.ids,
                    }))
            self.write({'sale_approval_cycle_ids': in_budget_list})
        self.show_request_approve_button = True
        if self.sale_approval_cycle_ids:
            min_seq_approval = min(self.sale_approval_cycle_ids.mapped('approval_seq'))
            notification_to_user = self.sale_approval_cycle_ids.filtered(
                lambda x: x.approval_seq == int(min_seq_approval))
            user = notification_to_user.user_approve_ids
            self.send_user_notification(user)
            self.state = 'to_approve'
        else:
            self.show_button_confirm = True

    def button_approve_sales_cycle(self):
        max_seq_approval = max(self.sale_approval_cycle_ids.mapped('approval_seq'))
        approval_levels = len(self.sale_approval_cycle_ids.ids)
        last_approval = self.sale_approval_cycle_ids.filtered(lambda x: x.approval_seq == int(max_seq_approval))
        last_approval_user = last_approval
        for line in self.sale_approval_cycle_ids:
            if not line.is_approved:
                line.is_approved = True
                notification_to_user = self.sale_approval_cycle_ids.filtered(
                    lambda x: x.approval_seq == int(line.approval_seq + 1))
                if notification_to_user:
                    user = notification_to_user.user_approve_ids
                    self.send_user_notification(user)
                if line == last_approval_user:
                    self.action_confirm()
                break


class SalesOrderLine(models.Model):
    _inherit = 'sale.order.line'

    cost_center_id = fields.Many2one(comodel_name="account.analytic.account", string="Cost Center",domain=[('analytic_account_type','=','cost_center')], required=False, )
    project_site_id = fields.Many2one(comodel_name="account.analytic.account", string="Project/Site",domain=[('analytic_account_type','=','project_site')], required=False, )
    type_id = fields.Many2one(comodel_name="account.analytic.account", string="Type",domain=[('analytic_account_type','=','type')], required=False, )
    location_id = fields.Many2one(comodel_name="account.analytic.account", string="Location",domain=[('analytic_account_type','=','location')], required=False, )
    budget_id = fields.Many2one(comodel_name="crossovered.budget", string="Budget", required=False, )
    remaining_amount = fields.Float(string="Remaining Amount", required=False, compute='get_budget_remaining_amount')

    @api.depends('budget_id')
    def get_budget_remaining_amount(self):
        for rec in self:
            order_lines_without_inv = sum(self.env['sale.order.line'].search([('order_id.state','=','sale')]).filtered(lambda x:not x.order_id.invoice_ids and x.budget_id == self.budget_id).mapped('price_subtotal'))
            print('order_lines_without_inv',order_lines_without_inv)
            sales_with_inv = self.env['sale.order'].search([('state','=','sale')]).filtered(lambda x:x.invoice_ids)
            invoices_budget = 0.0
            for order in sales_with_inv:
                for inv in order.invoice_ids:
                    if inv.state == 'draft':
                        for line in inv.invoice_line_ids.filtered(lambda x:x.budget_id == self.budget_id):
                            invoices_budget += line.price_subtotal
            print(invoices_budget,'invoices_budget')

            rec.remaining_amount = 0.0
            if rec.order_id.date_order:
                budget_lines = rec.budget_id.crossovered_budget_line.filtered(lambda x: rec.order_id.date_order.date() >= x.date_from and rec.order_id.date_order.date() <= x.date_to and x.analytic_account_id == rec.cost_center_id and x.project_site_id == rec.project_site_id and x.type_id == rec.type_id and x.location_id == rec.location_id)
                rec.remaining_amount = sum(budget_lines.mapped('remaining_amount')) - order_lines_without_inv - invoices_budget

    @api.onchange('project_site_id')
    def get_location_and_types(self):
        for rec in self:
            rec.type_id = rec.project_site_id.analytic_type_filter_id.id
            rec.location_id = rec.project_site_id.analytic_location_id.id

    def open_account_analytic_types(self):
        return {
            'name': 'Analytic Account Types',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'wizard.analytic.account.types',
            'context': {'default_so_line': self.id},
            'target': 'new',
        }

    def _prepare_invoice_line(self, **optional_values):
        res = super(SalesOrderLine, self)._prepare_invoice_line(**optional_values)
        res.update({'analytic_account_id':self.cost_center_id.id if self.cost_center_id else self.order_id.analytic_account_id.id
                    , 'project_site_id':self.project_site_id.id,'type_id':self.type_id.id,'location_id':self.location_id.id,'budget_id':self.budget_id.id,})
        return res

