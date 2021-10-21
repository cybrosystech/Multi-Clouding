# -*- coding: utf-8 -*-

import math
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_round
from odoo.tools.misc import formatLang
from dateutil.relativedelta import relativedelta


class AccountMove(models.Model):
    _inherit = 'account.move'
    # /////////// Start of Approval Cycle According To In Budget or Out Budget in Po Configuration //////////////

    budget_collect_ids = fields.One2many(comodel_name="budget.collect", inverse_name="move_id", string="",
                                         required=False, )
    purchase_approval_cycle_ids = fields.One2many(comodel_name="purchase.approval.cycle", inverse_name="move_id",
                                                  string="", required=False, )
    out_budget = fields.Boolean(string="Out Budget", compute="check_out_budget")
    show_approve_button = fields.Boolean(string="", compute='check_show_approve_button')
    show_request_approve_button = fields.Boolean(string="",copy=False )
    is_from_purchase = fields.Boolean(string="",compute='check_if_from_purchase'  )
    is_from_sales = fields.Boolean(string="",compute='check_if_from_sales'  )
    show_confirm_button = fields.Boolean(string="",compute='check_show_confirm_and_post_buttons' )
    show_post_button = fields.Boolean(string="",compute='check_show_confirm_and_post_buttons' )
    mail_link = fields.Text(string="\\4111", required=False, )
    state = fields.Selection(selection_add=[('to_approve', 'To Approve'),('posted',), ], ondelete={'to_approve': 'set default','draft': 'set default',})
    new_sequence = fields.Char(string="New Seq", required=False, )

    def button_cancel(self):
        res = super(AccountMove, self).button_cancel()
        self.purchase_approval_cycle_ids = False
        return res

    def button_draft(self):
        res = super(AccountMove, self).button_draft()
        self.purchase_approval_cycle_ids = False
        self.show_request_approve_button = False
        return res

    @api.model_create_multi
    def create(self, vals_list):
        res = super(AccountMove, self).create(vals_list)
        for rec in res:
            if rec.move_type == 'in_invoice':
                rec.new_sequence = self.env['ir.sequence'].next_by_code('vendor.bill.temporary.seq')
            if rec.move_type == 'in_refund':
                rec.new_sequence = self.env['ir.sequence'].next_by_code('debit.note.temporary.seq')
            if rec.move_type == 'out_invoice':
                rec.new_sequence = self.env['ir.sequence'].next_by_code('customer.invoice.temporary.seq')
            if rec.move_type == 'out_refund':
                rec.new_sequence = self.env['ir.sequence'].next_by_code('credit.note.temporary.seq')
            if rec.move_type == 'entry':
                rec.new_sequence = self.env['ir.sequence'].next_by_code('entry.temporary.seq')
        return res





    @api.depends()
    def check_show_confirm_and_post_buttons(self):
        self.show_post_button = False
        self.show_confirm_button = False
        if self.state not in ['draft','to_approve'] or self.auto_post or self.move_type != 'entry':
            if self.is_from_purchase or self.is_from_sales:
                self.show_post_button = True
            else:
                self.show_post_button = False
        elif self.state not in ['draft','to_approve'] or self.auto_post == True or self.move_type == 'entry':
            if self.is_from_purchase or self.is_from_sales:
                self.show_confirm_button = True
            else:
                self.show_confirm_button = False

    @api.depends()
    def check_if_from_purchase(self):
        self.is_from_purchase = False
        purchased = self.invoice_line_ids.filtered(lambda x:x.purchase_line_id)
        if purchased:
            self.is_from_purchase = True

    @api.depends()
    def check_if_from_sales(self):
        self.is_from_sales = False
        sales = self.invoice_line_ids.filtered(lambda x: x.sale_line_ids)
        if sales:
            self.is_from_sales = True

    @api.depends()
    def check_show_approve_button(self):
        self.show_approve_button = False
        current_approve = self.purchase_approval_cycle_ids.filtered(lambda x: x.is_approved).mapped('approval_seq')

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
        if not self.is_from_purchase and not self.is_from_sales:
            out_budget = self.budget_collect_ids.filtered(lambda x: x.difference_amount > 0)
            if out_budget:
                self.out_budget = True

    @api.onchange('invoice_line_ids')
    def get_budgets_in_out_budget_tab(self):
        if not self.is_from_purchase and not self.is_from_sales:
            budgets = self.invoice_line_ids.mapped('budget_id')
            self.budget_collect_ids = False
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
        for us in user:
            reseiver = us.partner_id
            if reseiver:
                for move in self:
                    self.message_post(
                        subject='Invoice Approval Needed',
                        body=str('This Invoice ' + str(
                            move.name if move.name != '/' else move.new_sequence) + ' Need Your Approval ') + ' click here to open: <a target=_BLANK href="/web?#id=' + str(
                            move.id) + '&view_type=form&model=account.move&action=" style="font-weight: bold">' + str(
                            move.name if move.name != '/' else move.new_sequence) + '</a>',
                        partner_ids=[reseiver.id]
                    )
                    # thread_pool = self.sudo().env['mail.thread']
                    # thread_pool.message_notify(
                    #     partner_ids=[reseiver.id],
                    #     subject=str('Invoice Approval Needed'),
                    #     body=str('This Sale Order ' + str(
                    #         move.name) + ' Need Your Approval ') + ' click here to open: <a target=_BLANK href="/web?#id=' + str(
                    #         move.id) + '&view_type=form&model=account.move&action=" style="font-weight: bold">' + str(
                    #         move.name) + '</a>',
                    #     email_from=self.env.user.company_id.catchall_formatted or self.env.user.company_id.email_formatted, )

                    email_template_id = self.env.ref('analytic_account_types.email_template_send_mail_approval_account')
                    ctx = self._context.copy()
                    ctx.update({'name': us.name})
                    if email_template_id:
                        email_template_id.with_context(ctx).send_mail(self.id, email_values={'email_to': us.email,})

    def request_approval_button(self):
        if self.out_budget and not self.purchase_approval_cycle_ids:
            out_budget_list = []
            out_budget = self.env['budget.in.out.check.invoice'].search([('type', '=', 'out_budget')], limit=1)
            max_value = max(self.budget_collect_ids.mapped('difference_amount'))
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
            self.write({'purchase_approval_cycle_ids': out_budget_list})
        if not self.out_budget and not self.purchase_approval_cycle_ids:
            in_budget_list = []
            in_budget = self.env['budget.in.out.check.invoice'].search([('type', '=', 'in_budget')], limit=1)
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
            self.write({'purchase_approval_cycle_ids': in_budget_list})
        self.show_request_approve_button = True
        if self.purchase_approval_cycle_ids:
            min_seq_approval = min(self.purchase_approval_cycle_ids.mapped('approval_seq'))
            notification_to_user = self.purchase_approval_cycle_ids.filtered(
                lambda x: x.approval_seq == int(min_seq_approval))
            user = notification_to_user.user_approve_ids
            self.state = 'to_approve'
            self.send_user_notification(user)

    def button_approve_purchase_cycle(self):
        max_seq_approval = max(self.purchase_approval_cycle_ids.mapped('approval_seq'))
        last_approval = self.purchase_approval_cycle_ids.filtered(lambda x: x.approval_seq == int(max_seq_approval))
        last_approval_user = last_approval
        for line in self.purchase_approval_cycle_ids:
            if not line.is_approved:
                line.is_approved = True
                notification_to_user = self.purchase_approval_cycle_ids.filtered(
                    lambda x: x.approval_seq == int(line.approval_seq + 1))
                if notification_to_user:
                    user = notification_to_user.user_approve_ids
                    self.send_user_notification(user)
                if line == last_approval_user:
                    self.action_post()
                break

    # /////////// End of Approval Cycle According To In Budget or Out Budget in Po Configuration //////////////


    def _auto_create_asset(self):
        create_list = []
        invoice_list = []
        auto_validate = []
        for move in self:
            if not move.is_invoice():
                continue

            for move_line in move.line_ids.filtered(lambda line: not (move.move_type in (
            'out_invoice', 'out_refund') and line.account_id.user_type_id.internal_group == 'asset')):
                if (
                        move_line.account_id
                        and (move_line.account_id.can_create_asset)
                        and move_line.account_id.create_asset != "no"
                        and not move.reversed_entry_id
                        and not (move_line.currency_id or move.currency_id).is_zero(move_line.price_total)
                        and not move_line.asset_ids
                ):
                    if not move_line.name:
                        raise UserError(
                            _('Journal Items of {account} should have a label in order to generate an asset').format(
                                account=move_line.account_id.display_name))
                    amount_total = amount_left = move_line.debit + move_line.credit
                    unit_uom = self.env.ref('uom.product_uom_unit')
                    if move_line.account_id.multiple_assets_per_line and ((
                                                                                  move_line.product_uom_id and move_line.product_uom_id.category_id.id == unit_uom.category_id.id) or not move_line.product_uom_id):
                        units_quantity = move_line.product_uom_id._compute_quantity(move_line.quantity, unit_uom, False)
                    else:
                        units_quantity = 1
                    while units_quantity > 0:
                        if units_quantity > 1:
                            original_value = float_round(amount_left / units_quantity,
                                                         precision_rounding=move_line.company_currency_id.rounding)
                            amount_left = float_round(amount_left - original_value,
                                                      precision_rounding=move_line.company_currency_id.rounding)
                        else:
                            original_value = amount_left
                        vals = {
                            'name': move_line.name,
                            'company_id': move_line.company_id.id,
                            'currency_id': move_line.company_currency_id.id,
                            'account_analytic_id': move_line.analytic_account_id.id,
                            'project_site_id': move_line.project_site_id.id,
                            'type_id': move_line.type_id.id,
                            'location_id': move_line.location_id.id,
                            'analytic_tag_ids': [(6, False, move_line.analytic_tag_ids.ids)],
                            'original_move_line_ids': [(6, False, move_line.ids)],
                            'state': 'draft',
                            'original_value': original_value,
                        }
                        model_id = move_line.account_id.asset_model
                        if model_id:
                            vals.update({
                                'model_id': model_id.id,
                            })
                        auto_validate.append(move_line.account_id.create_asset == 'validate')
                        invoice_list.append(move)
                        create_list.append(vals)
                        units_quantity -= 1

        assets = self.env['account.asset'].create(create_list)
        for asset, vals, invoice, validate in zip(assets, create_list, invoice_list, auto_validate):
            if 'model_id' in vals:
                asset._onchange_model_id()
                if validate:
                    asset.validate()
            if invoice:
                asset_name = {
                    'purchase': _('Asset'),
                    'sale': _('Deferred revenue'),
                    'expense': _('Deferred expense'),
                }[asset.asset_type]
                msg = _('%s created from invoice') % (asset_name)
                msg += ': <a href=# data-oe-model=account.move data-oe-id=%d>%s</a>' % (invoice.id, invoice.name)
                asset.message_post(body=msg)
        return assets

    @api.model
    def _prepare_move_for_asset_depreciation(self, vals):
        missing_fields = set(['asset_id', 'move_ref', 'amount', 'asset_remaining_value', 'asset_depreciated_value']) - set(vals)
        if missing_fields:
            raise UserError(_('Some fields are missing {}').format(', '.join(missing_fields)))
        asset = vals['asset_id']
        account_analytic_id = asset.account_analytic_id
        project_site_id = asset.project_site_id
        type_id = asset.type_id
        location_id = asset.location_id
        analytic_tag_ids = asset.analytic_tag_ids
        depreciation_date = vals.get('date', fields.Date.context_today(self))
        company_currency = asset.company_id.currency_id
        current_currency = asset.currency_id
        prec = company_currency.decimal_places
        amount = current_currency._convert(vals['amount'], company_currency, asset.company_id, depreciation_date)
        # Keep the partner on the original invoice if there is only one
        partner = asset.original_move_line_ids.mapped('partner_id')
        partner = partner[:1] if len(partner) <= 1 else self.env['res.partner']
        move_line_1 = {
            'name': asset.name,
            'partner_id': partner.id,
            'account_id': asset.account_depreciation_id.id,
            'debit': 0.0 if float_compare(amount, 0.0, precision_digits=prec) > 0 else -amount,
            'credit': amount if float_compare(amount, 0.0, precision_digits=prec) > 0 else 0.0,
            'analytic_account_id': account_analytic_id.id if asset.asset_type == 'sale' else False,
            'project_site_id': project_site_id.id if asset.asset_type == 'sale' else False,
            'type_id': type_id.id if asset.asset_type == 'sale' else False,
            'location_id': location_id.id if asset.asset_type == 'sale' else False,
            'analytic_tag_ids': [(6, 0, analytic_tag_ids.ids)] if asset.asset_type == 'sale' else False,
            'currency_id': current_currency.id,
            'amount_currency': -vals['amount'],
        }
        move_line_2 = {
            'name': asset.name,
            'partner_id': partner.id,
            'account_id': asset.account_depreciation_expense_id.id,
            'credit': 0.0 if float_compare(amount, 0.0, precision_digits=prec) > 0 else -amount,
            'debit': amount if float_compare(amount, 0.0, precision_digits=prec) > 0 else 0.0,
            'analytic_account_id': account_analytic_id.id if asset.asset_type in ('purchase', 'expense') else False,
            'project_site_id': project_site_id.id if asset.asset_type in ('purchase', 'expense') else False,
            'type_id': type_id.id if asset.asset_type in ('purchase', 'expense') else False,
            'location_id': location_id.id if asset.asset_type in ('purchase', 'expense') else False,
            'analytic_tag_ids': [(6, 0, analytic_tag_ids.ids)] if asset.asset_type in (
            'purchase', 'expense') else False,
            'currency_id': current_currency.id,
            'amount_currency': vals['amount'],
        }
        move_vals = {
            'ref': vals['move_ref'],
            'partner_id': partner.id,
            'date': depreciation_date,
            'journal_id': asset.journal_id.id,
            'line_ids': [(0, 0, move_line_1), (0, 0, move_line_2)],
            'asset_id': asset.id,
            'asset_remaining_value': vals['asset_remaining_value'],
            'asset_depreciated_value': vals['asset_depreciated_value'],
            'amount_total': amount,
            'name': '/',
            'asset_value_change': vals.get('asset_value_change', False),
            'move_type': 'entry',
            'currency_id': current_currency.id,
        }
        return move_vals


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    project_site_id = fields.Many2one(comodel_name="account.analytic.account", string="Project/Site",domain=[('analytic_account_type','=','project_site')], required=False, )
    type_id = fields.Many2one(comodel_name="account.analytic.account", string="Type",domain=[('analytic_account_type','=','type')], required=False, )
    location_id = fields.Many2one(comodel_name="account.analytic.account", string="Location",domain=[('analytic_account_type','=','location')], required=False, )
    analytic_account_id = fields.Many2one(string='Cost Center')
    budget_id = fields.Many2one(comodel_name="crossovered.budget", string="Budget", required=False, )
    budget_line_id = fields.Many2one(comodel_name="crossovered.budget.lines", string="Budget Line", required=False, )

    remaining_amount = fields.Float(string="Remaining Amount", required=False,compute='get_budget_remaining_amount' )

    @api.depends('budget_id','purchase_line_id')
    def get_budget_remaining_amount(self):
        for rec in self:
            rec.remaining_amount = 0.0
            if rec.purchase_line_id:
                rec.remaining_amount = rec.purchase_line_id.remaining_amount
            elif rec.sale_line_ids:
                rec.remaining_amount = rec.sale_line_ids[0].remaining_amount
            else:
                # order_lines_without_inv = sum(
                #     self.env['account.move.line'].search([('move_id.state', '=', 'draft')]).filtred(
                #         lambda x: not x.order_id.invoice_ids and x.budet_id == self.budget_id).mapped('price_subtotal'))
                # purchases_with_inv = self.env['purchase.order'].search([('state', '=', 'purchase')]).filtred(
                #     lambda x: x.invoice_ids)
                # invoices_budget = 0.0
                # for order in purchases_with_inv:
                #     for inv in order.invoice_ids:
                #         if inv.state == 'draft':
                #             for line in inv.invoice_line_ids.filtred(lambda x: x.budget_id == self.budget_id):
                #                 invoices_budget += line.price_subtotal
                # budget_lines = rec.budget_id.crossovered_budget_line.filtered(lambda x:rec.move_id.invoice_date >= x.date_from and rec.move_id.invoice_date <= x.date_to and x.analytic_account_id == rec.analytic_account_id and x.project_site_id == rec.project_site_id and x.type_id == rec.type_id and x.location_id == rec.location_id )
                rec.remaining_amount = rec.budget_line_id.remaining_amount


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
            'context': {'default_move_line': self.id},
            'target': 'new',
        }



