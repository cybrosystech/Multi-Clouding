# -*- coding: utf-8 -*-

from odoo import models, fields, api, _,SUPERUSER_ID
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    budget_collect_ids = fields.One2many(comodel_name="budget.collect",
                                         inverse_name="sale_id", string="",
                                         required=False, )
    sale_approval_cycle_ids = fields.One2many(
        comodel_name="purchase.approval.cycle", inverse_name="sale_id",
        string="", required=False, copy=False)
    out_budget = fields.Boolean(string="Out Budget", compute="check_out_budget",
                                copy=False)
    show_approve_button = fields.Boolean(string="",
                                         compute='check_show_approve_button',
                                         copy=False)
    show_request_approve_button = fields.Boolean(string="", copy=False)
    show_button_confirm = fields.Boolean(string="", copy=False)
    state = fields.Selection(
        selection_add=[('to_approve', 'To Approve'), ('sent',), ],
        ondelete={'to_approve': 'set default', 'draft': 'set default', })
    is_admin = fields.Boolean(string="Is Admin", compute='compute_is_admin')

    @api.depends_context('uid')
    def compute_is_admin(self):
        is_admin = self.env.user.id == SUPERUSER_ID or \
                   self.env.user.has_group('base.group_erp_manager') or \
                   self.env.user.has_group('base.group_system')
        for rec in self:
            rec.is_admin=is_admin

    def _can_be_confirmed(self):
        self.ensure_one()
        return self.state in {'draft', 'sent', 'to_approve'}

    def action_cancel(self):
        res = super(SaleOrder, self).action_cancel()
        self.sale_approval_cycle_ids = False
        return res

    def action_draft(self):
        res = super(SaleOrder, self).action_draft()
        self.show_request_approve_button = False
        return res

    @api.depends('sale_approval_cycle_ids',
                 'sale_approval_cycle_ids.is_approved')
    def check_show_approve_button(self):
        self.show_approve_button = False
        current_approve = self.sale_approval_cycle_ids.filtered(
            lambda x: x.is_approved).mapped('approval_seq')

        last_approval = max(current_approve) if current_approve else 0
        check_last_approval_is_approved = self.sale_approval_cycle_ids.filtered(
            lambda x: x.approval_seq == int(last_approval))
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
        out_budget = self.budget_collect_ids.filtered(
            lambda x: x.difference_amount > 0)
        if out_budget:
            self.out_budget = True

    @api.onchange('order_line')
    def get_budgets_in_out_budget_tab(self):
        self.budget_collect_ids = False
        budgets = self.order_line.mapped('budget_id')
        budget_lines = []
        budgets = set(budgets)
        if budgets:
            budget_collects = self.budget_collect_ids.mapped('budget_id')
            for bud in budgets:
                if bud not in budget_collects:
                    budget_lines.append((0, 0, {
                        'budget_id': bud.id
                    }))
            self.write({'budget_collect_ids': budget_lines})

    def send_user_notification(self, user):
        for use in user:
            reseiver = use.partner_id
            if reseiver:
                email_template_id = self.env.ref(
                    'analytic_account_types.email_template_send_mail_approval_sales')
                ctx = self._context.copy()
                ctx.update({'name': use.name})
                if email_template_id:
                    email_from_alias = self.env[
                        'ir.config_parameter'].sudo().get_param(
                        'mail.default.from')
                    if email_from_alias:
                        email_from = f"Odoo ERP <{email_from_alias}>"
                    else:
                        email_from = f"Odoo ERP <{self.env.user.company_id.email}>"
                    email_template_id.with_context(ctx).send_mail(self.id,
                                                                  force_send=True,
                                                                  email_values={
                                                                      'email_from': email_from,
                                                                      'email_to': use.email,
                                                                      'model': None,
                                                                      'res_id': None})

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

            self.write({'sale_approval_cycle_ids': out_budget_list})
        if not self.out_budget and not self.sale_approval_cycle_ids:
            in_budget_list = []
            in_budget = self.env['budget.in.out.check.sales'].search(
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
            self.write({'sale_approval_cycle_ids': in_budget_list})
        self.show_request_approve_button = True
        if self.sale_approval_cycle_ids:
            min_seq_approval = min(
                self.sale_approval_cycle_ids.mapped('approval_seq'))
            notification_to_user = self.sale_approval_cycle_ids.filtered(
                lambda x: x.approval_seq == int(min_seq_approval))
            user = notification_to_user.user_approve_ids
            self.send_user_notification(user)
            self.state = 'to_approve'
        else:
            self.show_button_confirm = True

    def button_approve_sales_cycle(self):
        for so in self:
            if not so.sale_approval_cycle_ids:
                so.button_request_purchase_cycle()
            if so.sale_approval_cycle_ids:
                min_seq_approval = min(
                    so.sale_approval_cycle_ids.filtered(
                        lambda x: x.is_approved is not True).mapped(
                        'approval_seq'))
                last_approval = so.sale_approval_cycle_ids.filtered(
                    lambda x: x.approval_seq == int(min_seq_approval))
                if so.env.user not in last_approval.user_approve_ids:
                    raise UserError(
                        'You cannot approve this record' + ' ' + str(
                            so.name))
                last_approval.is_approved = True
                remaining_approvals = so.sale_approval_cycle_ids.filtered(
                        lambda x: x.is_approved is not True).mapped(
                        'approval_seq')
                if len(remaining_approvals) > 0:
                    min_seq_approval_next = min(remaining_approvals)
                    last_approval_to_approve = so.sale_approval_cycle_ids.filtered(
                        lambda x: x.approval_seq == int(min_seq_approval_next))
                    so.send_user_notification(last_approval_to_approve.user_approve_ids)
                if not so.sale_approval_cycle_ids.filtered(
                        lambda x: x.is_approved is False):
                    so.action_confirm()
                message = 'Level ' + str(
                    last_approval.approval_seq) + ' Approved by :' + str(
                    so.env.user.name)
                so.message_post(body=message)


class SalesOrderLine(models.Model):
    _inherit = 'sale.order.line'

    cost_center_id = fields.Many2one(comodel_name="account.analytic.account",
                                     string="Cost Center",
                                     required=False, domain=[
            ('analytic_account_type', '=', 'cost_center')])
    project_site_id = fields.Many2one(comodel_name="account.analytic.account",
                                      string="Project/Site",
                                      domain=[('analytic_account_type', '=',
                                               'project_site')],
                                      required=False, )
    budget_id = fields.Many2one(comodel_name="crossovered.budget",
                                string="Budget", required=False, )
    budget_line_id = fields.Many2one(comodel_name="crossovered.budget.lines",
                                     string="Budget Line", required=False, )

    remaining_amount = fields.Float(string="Remaining Amount", required=False,
                                    compute='get_budget_remaining_amount')
    local_subtotal = fields.Float(compute='compute_local_subtotal', store=True)
    location_id = fields.Many2one(comodel_name="account.analytic.account",
                                  string="Location",
                                  domain=[('analytic_account_type', '=',
                                           'location')], required=False, )
    type_id = fields.Many2one(comodel_name="account.analytic.account",
                              string="Type",
                              domain=[('analytic_account_type', '=',
                                       'type')], required=False, )
    site_status = fields.Selection(
        [('on_air', 'ON AIR'), ('off_air', 'OFF AIR'), ],
        string='Site Status')
    t_budget = fields.Selection(
        [('capex', 'CAPEX'), ('opex', 'OPEX'), ],
        string='T.Budget')

    @api.depends('price_subtotal')
    def compute_local_subtotal(self):
        for rec in self:
            if not rec.order_id.date_order:
                raise UserError(_('Order date is required'))
            else:
                rec.local_subtotal = rec.order_id.currency_id._convert(
                    rec.price_subtotal,
                    rec.order_id.company_id.currency_id,
                    rec.order_id.company_id,
                    rec.order_id.date_order or rec.order_id.create_date.date())

    @api.onchange('budget_id')
    def onchange_budget_id(self):
        return {'domain': {'budget_line_id': [
            ('crossovered_budget_id', '=', self.budget_id.id)]}}

    @api.depends('budget_id')
    def get_budget_remaining_amount(self):
        for rec in self:
            order_lines_without_inv = sum(
                self.env['sale.order.line'].search(
                    [('order_id.state', '=', 'sale')]).filtered(
                    lambda
                        x: not x.order_id.invoice_ids and x.budget_id == self.budget_id).mapped(
                    'price_subtotal'))
            sales_with_inv = self.env['sale.order'].search(
                [('state', '=', 'sale')]).filtered(lambda x: x.invoice_ids)
            invoices_budget = 0.0
            for order in sales_with_inv:
                for inv in order.invoice_ids:
                    if inv.state == 'draft':
                        for line in inv.invoice_line_ids.filtered(
                                lambda x: x.budget_id == self.budget_id):
                            invoices_budget += line.price_subtotal

            rec.remaining_amount = 0.0
            if rec.budget_line_id:
                rec.remaining_amount = rec.budget_line_id.remaining_amount - order_lines_without_inv - invoices_budget

    def _prepare_invoice_line(self, **optional_values):
        res = super(SalesOrderLine, self)._prepare_invoice_line(
            **optional_values)
        res.update({
            'budget_id': self.budget_id.id,
            'analytic_account_id': self.cost_center_id.id,
            'project_site_id': self.project_site_id.id})
        return res
