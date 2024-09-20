# -*- coding: utf-8 -*-

from odoo import models, fields, api, _,SUPERUSER_ID
from odoo.exceptions import ValidationError, UserError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    budget_collect_ids = fields.One2many(comodel_name="budget.collect",
                                         inverse_name="purchase_id", string="",
                                         required=False, )
    purchase_approval_cycle_ids = fields.One2many(
        comodel_name="purchase.approval.cycle", inverse_name="purchase_id",
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
    is_admin = fields.Boolean(string="Is Admin", compute='compute_is_admin',default=lambda self: self.get_is_admin())

    def get_is_admin(self):
        if self.env.user.has_group(
                'base.group_erp_manager') or self.env.user.has_group(
            'base.group_system'):
            is_admin = True
        else:
            is_admin = False
        return is_admin

    def compute_is_admin(self):
        for rec in self:
            if self.env.user.id == SUPERUSER_ID or self.env.user.has_group(
                    'base.group_erp_manager') or self.env.user.has_group(
                    'base.group_system'):
                rec.is_admin = True
            else:
                rec.is_admin = False

    def button_cancel(self):
        res = super(PurchaseOrder, self).button_cancel()
        self.purchase_approval_cycle_ids = False
        return res

    def button_draft(self):
        res = super(PurchaseOrder, self).button_draft()
        self.show_request_approve_button = False
        return res

    @api.depends('purchase_approval_cycle_ids',
                 'purchase_approval_cycle_ids.is_approved')
    def check_show_approve_button(self):
        self.show_approve_button = False
        current_approve = self.purchase_approval_cycle_ids.filtered(
            lambda x: x.is_approved).mapped('approval_seq')

        last_approval = max(current_approve) if current_approve else 0
        check_last_approval_is_approved = self.purchase_approval_cycle_ids.filtered(
            lambda x: x.approval_seq == int(last_approval))
        for rec in self.purchase_approval_cycle_ids:
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
        self.budget_collect_ids = [(5, 0, 0)]
        budgets = self.order_line.mapped('budget_id')
        budget_lines = []
        budgets = set(budgets)
        for bud in budgets:
            if bud not in self.budget_collect_ids.mapped('budget_id'):
                budget_lines.append((0, 0, {
                    'budget_id': bud.id
                }))
        self.write({'budget_collect_ids': budget_lines})

    def send_user_notification(self, user):
        for us in user:
            reseiver = us.partner_id
            if reseiver:
                for purchase in self:
                    email_template_id = self.env.ref(
                        'analytic_account_types.email_template_send_mail_approval_purchase')
                    ctx = self._context.copy()
                    ctx.update({'name': us.name})
                    # email_from = self.env["ir.config_parameter"].get_param(
                    #     "mail.default.from", "migrate+default_from")
                    if email_template_id:
                        email_template_id.with_context(ctx).send_mail(self.id,
                                                                      force_send=True,
                                                                      email_values={
                                                                          'email_to': us.email,
                                                                          'model': None,
                                                                          'res_id': None})

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
        self.show_request_approve_button = True
        if self.purchase_approval_cycle_ids:
            min_seq_approval = min(
                self.purchase_approval_cycle_ids.mapped('approval_seq'))
            notification_to_user = self.purchase_approval_cycle_ids.filtered(
                lambda x: x.approval_seq == int(min_seq_approval))
            user = notification_to_user.user_approve_ids
            self.send_user_notification(user)
            self.state = 'to_approve'
        else:
            self.show_button_confirm = True

    def button_approve_purchase_cycle(self):
        max_seq_approval = max(
            self.purchase_approval_cycle_ids.mapped('approval_seq'))
        approval_levels = len(self.purchase_approval_cycle_ids.ids)
        last_approval = self.purchase_approval_cycle_ids.filtered(
            lambda x: x.approval_seq == int(max_seq_approval))
        last_approval_id = last_approval
        for line in self.purchase_approval_cycle_ids:
            if not line.is_approved:
                line.is_approved = True
                notification_to_user = self.purchase_approval_cycle_ids.filtered(
                    lambda x: x.approval_seq == int(line.approval_seq + 1))
                if notification_to_user:
                    user = notification_to_user.user_approve_ids
                    self.send_user_notification(user)
                if line == last_approval_id:
                    self.button_confirm()
                break

    def button_confirm(self):
        for order in self:
            if order.state not in ['draft', 'sent', 'to_approve']:
                continue
            order._add_supplier_to_product()
            # Deal with double validation process
            if order.company_id.po_double_validation == 'one_step' \
                    or (order.company_id.po_double_validation == 'two_step' \
                        and order.amount_total < self.env.company.currency_id._convert(
                        order.company_id.po_double_validation_amount,
                        order.currency_id, order.company_id,
                        order.date_order or fields.Date.today())) \
                    or order.user_has_groups('purchase.group_purchase_manager'):
                order.button_approve()
            else:
                order.write({'state': 'to approve'})
            if order.partner_id not in order.message_partner_ids:
                order.message_subscribe([order.partner_id.id])
        return True


class PurchaseApprovalCycle(models.Model):
    _name = 'purchase.approval.cycle'

    move_id = fields.Many2one(comodel_name="account.move", string="",
                              required=False, )
    purchase_id = fields.Many2one(comodel_name="purchase.order", string="",
                                  required=False, )
    sale_id = fields.Many2one(comodel_name="sale.order", string="",
                              required=False, )
    approval_seq = fields.Integer(string="Approval Sequence", required=False, )
    user_approve_ids = fields.Many2many(comodel_name="res.users",
                                        string="User Approval",
                                        required=False, )
    is_approved = fields.Boolean(string="Approved", )


class BudgetCollect(models.Model):
    _name = 'budget.collect'

    purchase_id = fields.Many2one(comodel_name="purchase.order", string="",
                                  required=False, )
    sale_id = fields.Many2one(comodel_name="sale.order", string="",
                              required=False, )
    move_id = fields.Many2one(comodel_name="account.move", string="",
                              required=False, )
    budget_id = fields.Many2one(comodel_name="crossovered.budget",
                                string="Budget", required=False, )
    remaining_amount = fields.Float(string="Remaining Amount", required=False,
                                    compute='get_fields_related_to_po_line')
    demand_amount = fields.Float(string="Demand Amount", required=False,
                                 compute='get_fields_related_to_po_line')
    difference_amount = fields.Float(string="Difference Amount", required=False,
                                     compute='get_fields_related_to_po_line')

    @api.depends('budget_id')
    def get_fields_related_to_po_line(self):
        for rec in self:
            rec.remaining_amount = 0.0
            rec.demand_amount = 0.0
            rec.difference_amount = 0.0
            if rec.purchase_id:
                budget_lines = rec.purchase_id.order_line.filtered(
                    lambda x: x.budget_id == rec.budget_id)
                if budget_lines:
                    rec.remaining_amount = budget_lines[0].remaining_amount
                    rec.demand_amount = sum(
                        budget_lines.mapped('local_subtotal'))
                    if rec.demand_amount > rec.remaining_amount:
                        rec.difference_amount = rec.demand_amount - rec.remaining_amount
            if rec.move_id:
                budget_lines = rec.move_id.invoice_line_ids.filtered(
                    lambda x: x.budget_id == rec.budget_id)
                if budget_lines:
                    rec.remaining_amount = budget_lines[0].remaining_amount
                    rec.demand_amount = sum(
                        budget_lines.mapped('local_subtotal'))
                    if rec.demand_amount > rec.remaining_amount:
                        rec.difference_amount = rec.demand_amount - rec.remaining_amount
            if rec.sale_id:
                budget_lines = rec.sale_id.order_line.filtered(
                    lambda x: x.budget_id == rec.budget_id)
                if budget_lines:
                    rec.remaining_amount = budget_lines[0].remaining_amount
                    rec.demand_amount = sum(
                        budget_lines.mapped('local_subtotal'))
                    if rec.demand_amount > rec.remaining_amount:
                        rec.difference_amount = rec.demand_amount - rec.remaining_amount


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    cost_center_id = fields.Many2one(comodel_name="account.analytic.account",
                                     string="Cost center", domain=[
            ('analytic_account_type', '=', 'cost_center')], required=False, )
    project_site_id = fields.Many2one(comodel_name="account.analytic.account",
                                      string="Project/Site", domain=[
            ('analytic_account_type', '=', 'project_site')], required=False, )
    type_id = fields.Many2one(comodel_name="account.analytic.account",
                              string="Type",
                              domain=[('analytic_account_type', '=', 'type')],
                              required=False, )
    location_id = fields.Many2one(comodel_name="account.analytic.account",
                                  string="Location", domain=[
            ('analytic_account_type', '=', 'location')], required=False, )
    budget_id = fields.Many2one(comodel_name="crossovered.budget",
                                string="Budget", required=False, )
    budget_line_id = fields.Many2one(comodel_name="crossovered.budget.lines",
                                     string="Budget Line", required=False, )
    remaining_amount = fields.Float(string="Remaining Amount", required=False,
                                    compute='get_budget_remaining_amount')
    local_subtotal = fields.Float(compute='compute_local_subtotal', store=True)


    @api.onchange('budget_id')
    def onchange_budget_id(self):
        return {'domain': {'budget_line_id': [
            ('crossovered_budget_id', '=', self.budget_id.id)]}}

    @api.depends('price_subtotal')
    def compute_local_subtotal(self):
        for rec in self:
            if not rec.order_id.date_order:
                raise UserError(_('Order date is required'))
            else:
                rec.local_subtotal = rec.order_id.currency_id._convert(
                    rec.price_subtotal, rec.order_id.company_id.currency_id,
                    rec.order_id.company_id,
                    rec.order_id.date_order or rec.order_id.create_date.date())

    @api.depends('budget_id')
    def get_budget_remaining_amount(self):
        for rec in self:
            order_lines_without_inv = sum(
                self.env['purchase.order.line'].search(
                    [('order_id.state', '=', 'purchase')]).filtered(
                    lambda
                        x: not x.order_id.invoice_ids and x.budget_id == self.budget_id).mapped(
                    'local_subtotal'))
            purchases_with_inv = self.env['purchase.order'].search(
                [('state', '=', 'purchase')]).filtered(lambda x: x.invoice_ids)
            invoices_budget = 0.0
            for order in purchases_with_inv:
                for inv in order.invoice_ids:
                    if inv.state == 'draft':
                        for line in inv.invoice_line_ids.filtered(
                                lambda x: x.budget_id == self.budget_id):
                            invoices_budget += line.price_subtotal
            rec.remaining_amount = 0.0
            if rec.budget_line_id:
                rec.remaining_amount = rec.budget_line_id.remaining_amount - order_lines_without_inv - invoices_budget

    def _prepare_account_move_line(self, move=False):
        res = super(PurchaseOrderLine, self)._prepare_account_move_line()
        res.update({'budget_id': self.budget_id.id, })
        return res
