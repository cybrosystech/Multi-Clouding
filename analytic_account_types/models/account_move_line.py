# -*- coding: utf-8 -*-

from odoo import api, fields, models, _, SUPERUSER_ID, tools
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, float_round
from textwrap import shorten
from odoo.tools import (format_date)
from markupsafe import escape
from collections import defaultdict


class AccountMove(models.Model):
    _inherit = 'account.move'
    # /////////// Start of Approval Cycle According To In Budget or Out Budget in Po Configuration //////////////

    budget_collect_ids = fields.One2many(comodel_name="budget.collect",
                                         inverse_name="move_id", string="",
                                         required=False, )
    purchase_approval_cycle_ids = fields.One2many(
        comodel_name="purchase.approval.cycle", inverse_name="move_id",
        string="", required=False, )
    out_budget = fields.Boolean(string="Out Budget", compute="check_out_budget",
                                copy=False)
    show_approve_button = fields.Boolean(string="",
                                         compute='check_show_approve_button',
                                         copy=False)
    show_request_approve_button = fields.Boolean(string="", copy=False)
    is_from_purchase = fields.Boolean(string="",
                                      compute='check_if_from_purchase',
                                      copy=False)
    is_from_sales = fields.Boolean(string="", compute='check_if_from_sales',
                                   copy=False)
    show_confirm_button = fields.Boolean(string="",
                                         compute='check_show_confirm_and_post_buttons',
                                         copy=False)
    show_post_button = fields.Boolean(string="",
                                      compute='check_show_confirm_and_post_buttons',
                                      copy=False)
    state = fields.Selection(
        selection_add=[('to_approve', 'To Approve'), ('posted',), ],
        ondelete={'to_approve': 'set default', 'draft': 'set default', })
    is_admin = fields.Boolean(string="Is Admin", compute='_compute_is_admin')

    @api.depends_context('uid')
    def _compute_is_admin(self):
        env = self.env
        is_admin = env.su or env.user.has_group('base.group_erp_manager') or env.user.has_group('base.group_system')
        for record in self:
            record.is_admin = is_admin

    @api.depends('line_ids.balance')
    def _compute_depreciation_value(self):
        for move in self:
            asset = move.asset_id or move.reversed_entry_id.asset_id  # reversed moves are created before being assigned to the asset
            if asset:
                account_internal_group = 'expense'
                if asset.currency_id.id != asset.company_id.currency_id.id:
                    asset_depreciation = sum(
                        move.line_ids.filtered(lambda
                                                   l: l.account_id.internal_group == account_internal_group or l.account_id == asset.account_depreciation_expense_id).mapped(
                            'amount_currency')
                    )
                    # Special case of closing entry - only disposed assets of type 'purchase' should match this condition

                    if any(
                            line.account_id == asset.account_asset_id
                            and float_compare(-line.amount_currency, asset.original_value,
                                              precision_rounding=asset.currency_id.rounding) == 0
                            for line in move.line_ids
                    ) and len(move.line_ids) > 2:
                        asset_depreciation = (
                                asset.original_value
                                - asset.salvage_value
                                - move.line_ids[
                                    1].amount_currency
                                * (-1 if asset.original_value < 0 else 1)
                        )
                else:
                    asset_depreciation = sum(
                        move.line_ids.filtered(lambda
                                                   l: l.account_id.internal_group == account_internal_group or l.account_id == asset.account_depreciation_expense_id).mapped(
                            'balance')
                    )
                    # Special case of closing entry - only disposed assets of type 'purchase' should match this condition
                    if any(
                            line.account_id == asset.account_asset_id
                            and float_compare(-line.balance, asset.original_value,
                                              precision_rounding=asset.currency_id.rounding) == 0
                            for line in move.line_ids
                    ):
                        asset_depreciation = (
                                asset.original_value
                                - asset.salvage_value
                                - (
                                    move.line_ids[
                                        1].debit if asset.original_value > 0 else
                                    move.line_ids[1].credit
                                ) * (-1 if asset.original_value < 0 else 1)
                        )
            else:
                asset_depreciation = 0
            move.depreciation_value = asset_depreciation

    def button_cancel(self):
        res = super(AccountMove, self).button_cancel()
        self.purchase_approval_cycle_ids = False
        return res

    def button_draft(self):
        res = super(AccountMove, self).button_draft()
        self.purchase_approval_cycle_ids = False
        self.show_request_approve_button = False
        return res

    # Override native method to set invoice display name in 'to_approve'status.
    def _get_move_display_name(self, show_ref=False):
        ''' Helper to get the display name of an invoice depending of its type.
        :param show_ref:    A flag indicating of the display name must include or not the journal entry reference.
        :return:            A string representing the invoice.
        '''
        self.ensure_one()
        name = ''
        if self.state in ('draft', 'to_approve'):
            name += {
                'out_invoice': _('Draft Invoice'),
                'out_refund': _('Draft Credit Note'),
                'in_invoice': _('Draft Bill'),
                'in_refund': _('Draft Vendor Credit Note'),
                'out_receipt': _('Draft Sales Receipt'),
                'in_receipt': _('Draft Purchase Receipt'),
                'entry': _('Draft Entry'),
            }[self.move_type]
            name += ' '
        if not self.name or self.name == '/':
            name += '(* %s)' % str(self.id)
        else:
            name += self.name
            if self.env.context.get('input_full_display_name'):
                if self.partner_id:
                    name += f', {self.partner_id.name}'
                if self.date:
                    name += f', {format_date(self.env, self.date)}'
        return name + (
            f" ({shorten(self.ref, width=50)})" if show_ref and self.ref else '')

    @api.depends('state', 'auto_post', 'move_type', 'is_from_purchase', 'is_from_sales', 'purchase_approval_cycle_ids')
    def check_show_confirm_and_post_buttons(self):
        for rec in self:
            # Default values
            rec.show_post_button = False
            rec.show_confirm_button = False

            # Common conditions
            is_draft_or_approve = rec.state in ['draft', 'to_approve']
            is_entry_type = rec.move_type == 'entry'
            has_purchase_or_sales = rec.is_from_purchase or rec.is_from_sales
            has_no_approval_cycle = not rec.purchase_approval_cycle_ids

            if not is_draft_or_approve or rec.auto_post or not is_entry_type:
                rec.show_post_button = has_purchase_or_sales or has_no_approval_cycle
            else:
                rec.show_confirm_button = has_purchase_or_sales

    @api.depends('invoice_line_ids.purchase_line_id')
    def check_if_from_purchase(self):
        invoice_lines = self.env['account.move.line'].search_read(
            [('move_id', 'in', self.ids), ('purchase_line_id', '!=', False)],
            ['move_id']
        )
        # Use a set for fast lookup
        move_ids_with_purchase = {line['move_id'][0] for line in invoice_lines}

        for rec in self:
            rec.is_from_purchase = rec.id in move_ids_with_purchase

    @api.depends('invoice_line_ids.sale_line_ids')
    def check_if_from_sales(self):
        invoice_lines = self.env['account.move.line'].search_read(
            [('move_id', 'in', self.ids), ('sale_line_ids', '!=', False)],
            ['move_id']
        )
        # Use a set for fast lookup
        move_ids_with_sales = {line['move_id'][0] for line in invoice_lines}

        for rec in self:
            rec.is_from_sales = rec.id in move_ids_with_sales

    @api.depends('purchase_approval_cycle_ids', 'state',
                 'purchase_approval_cycle_ids.is_approved',
                 'purchase_approval_cycle_ids.user_approve_ids')
    def check_show_approve_button(self):
        for r in self:
            r.show_approve_button = False

            # Get all approved approval sequences
            approved_cycles = r.purchase_approval_cycle_ids.filtered(lambda x: x.is_approved)
            last_approval = max(approved_cycles.mapped('approval_seq'), default=0)

            # Get the last approval cycle object
            last_approval_cycle = r.purchase_approval_cycle_ids.filtered_domain([('approval_seq', '=', last_approval)])

            # Check if current user is in any pending approval cycle
            for rec in r.purchase_approval_cycle_ids:
                if not rec.is_approved and self.env.user.id in rec.user_approve_ids.ids:
                    if not last_approval or last_approval_cycle.is_approved:
                        r.show_approve_button = True
                        break  # Stop checking once a valid case is found

            # Update state only if all approvals are completed
            if r.state != 'posted' and r.purchase_approval_cycle_ids:
                if all(r.purchase_approval_cycle_ids.mapped('is_approved')):
                    r.state = 'posted'

    @api.depends('line_ids.budget_id', 'line_ids.remaining_amount')
    def check_out_budget(self):
        for rec in self:
            rec.out_budget = False
            lines = rec.line_ids.filtered(lambda x: not x.budget_id)
            if lines.filtered(
                    lambda x: x.remaining_amount < x.debit or x.remaining_amount < x.credit):
                rec.out_budget = True

    @api.onchange('invoice_line_ids')
    def get_budgets_in_out_budget_tab(self):
        if not self.is_from_purchase and not self.is_from_sales:
            budgets = self.invoice_line_ids.mapped('budget_id')
            self.budget_collect_ids = [(5, 0, 0)]
            budget_lines = []
            budgets = set(budgets)
            if budgets:
                budget_collects = self.budget_collect_ids.mapped('budget_id')
                for bud in budgets:
                    if bud not in budget_collects:
                        budget_lines.append((0, 0, {
                            'budget_id': bud.id,
                        }))
                self.write({'budget_collect_ids': budget_lines})

    def send_user_notification(self, user):
        for us in user:
            reseiver = us.partner_id
            if reseiver:
                for move in self:
                    email_template_id = self.env.ref(
                        'analytic_account_types.email_template_send_mail_approval_account')
                    ctx = self._context.copy()
                    ctx.update({'name': us.name})
                    if email_template_id:
                        # email_from = self.env["ir.config_parameter"].get_param(
                        #     "mail.default.from", "migrate+default_from")
                        email_template_id.with_context(ctx).send_mail(self.id,
                                                                      force_send=True,
                                                                      email_values={
                                                                          'email_to': us.email,
                                                                          'model': None,
                                                                          'res_id': None})

    def button_request_purchase_cycle(self):
        for rec in self:
            journals = self.env['account.move'].search([('id', '=', rec.id)])
            journals.get_budgets_in_out_budget_tab()
            if journals.out_budget and not journals.purchase_approval_cycle_ids:
                out_budget_list = []
                out_budget = journals.env['budget.in.out.check.invoice'].search(
                    [('type', '=', 'out_budget'),
                     ('company_id', '=', journals.env.company.id)], limit=1)
                max_value = max(
                    journals.budget_collect_ids.mapped('demand_amount'))
                for rec in out_budget.budget_line_ids:
                    if max_value >= rec.from_amount:
                        out_budget_list.append((0, 0, {
                            'approval_seq': rec.approval_seq,
                            'user_approve_ids': rec.user_ids.ids,
                        }))

                journals.write({'purchase_approval_cycle_ids': out_budget_list})
            if not journals.out_budget and not journals.purchase_approval_cycle_ids:
                in_budget_list = []
                in_budget = journals.env['budget.in.out.check.invoice'].search(
                    [('type', '=', 'in_budget'),
                     ('company_id', '=', journals.env.company.id)], limit=1)
                if journals.move_type == 'endef request_approval_buttontry':
                    max_value = max(journals.line_ids.mapped(
                        'local_subtotal'))  # Old Field is debit
                else:
                    max_value = sum(
                        journals.invoice_line_ids.mapped('local_subtotal'))
                for rec in in_budget.budget_line_ids:
                    if max_value >= rec.from_amount:
                        in_budget_list.append((0, 0, {
                            'approval_seq': rec.approval_seq,
                            'user_approve_ids': rec.user_ids.ids,
                        }))

                journals.write({'purchase_approval_cycle_ids': in_budget_list})
            journals.show_request_approve_button = True
            if journals.purchase_approval_cycle_ids:
                min_seq_approval = min(
                    journals.purchase_approval_cycle_ids.mapped('approval_seq'))
                notification_to_user = journals.purchase_approval_cycle_ids.filtered(
                    lambda x: x.approval_seq == int(min_seq_approval))
                user = notification_to_user.user_approve_ids
                journals.state = 'to_approve'
                journals.send_user_notification(user)

    def request_approval_button(self):
        self.get_budgets_in_out_budget_tab()
        if self.out_budget and not self.purchase_approval_cycle_ids:
            out_budget_list = []
            out_budget = self.env['budget.in.out.check.invoice'].search(
                [('type', '=', 'out_budget'),
                 ('company_id', '=', self.env.company.id)], limit=1)
            if self.budget_collect_ids:
                max_value = max(self.budget_collect_ids.mapped('demand_amount'))
                for rec in out_budget.budget_line_ids:
                    if max_value >= rec.from_amount:
                        out_budget_list.append((0, 0, {
                            'approval_seq': rec.approval_seq,
                            'user_approve_ids': rec.user_ids.ids,
                        }))

            self.write({'purchase_approval_cycle_ids': out_budget_list})
        if not self.out_budget and not self.purchase_approval_cycle_ids:
            in_budget_list = []
            in_budget = self.env['budget.in.out.check.invoice'].search(
                [('type', '=', 'in_budget'),
                 ('company_id', '=', self.env.company.id)], limit=1)
            if self.move_type == 'endef request_approval_buttontry':
                max_value = max(self.line_ids.mapped(
                    'local_subtotal'))  # Old Field is debit
            else:
                max_value = sum(self.invoice_line_ids.mapped('local_subtotal'))
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
            self.state = 'to_approve'
            self.send_user_notification(user)

    def button_approve_purchase_cycle(self):
        for journal in self:
            if not journal.purchase_approval_cycle_ids:
                journal.button_request_purchase_cycle()
            if journal.purchase_approval_cycle_ids:
                min_seq_approval = min(
                    journal.purchase_approval_cycle_ids.filtered(
                        lambda x: x.is_approved is not True).mapped(
                        'approval_seq'))
                last_approval = journal.purchase_approval_cycle_ids.filtered(
                    lambda x: x.approval_seq == int(min_seq_approval))
                if journal.env.user not in last_approval.user_approve_ids:
                    raise UserError(
                        'You cannot approve this record' + ' ' + str(
                            journal.name))
                last_approval.is_approved = True
                remaining_approvals = journal.purchase_approval_cycle_ids.filtered(
                    lambda x: x.is_approved is not True).mapped(
                    'approval_seq')
                if len(remaining_approvals) > 0:
                    min_seq_approval_next = min(remaining_approvals)
                    last_approval_to_approve = journal.purchase_approval_cycle_ids.filtered(
                        lambda x: x.approval_seq == int(min_seq_approval_next))
                    journal.send_user_notification(
                        last_approval_to_approve.user_approve_ids)
                if not journal.purchase_approval_cycle_ids.filtered(
                        lambda x: x.is_approved is False):
                    journal.action_post()
                message = 'Level ' + str(
                    last_approval.approval_seq) + ' Approved by :' + str(
                    journal.env.user.name)
                journal.message_post(body=message)

    # /////////// End of Approval Cycle According To In Budget or Out Budget in Po Configuration //////////////

    def _auto_create_asset(self):
        create_list = []
        invoice_list = []
        auto_validate = []
        for move in self:
            if not move.move_type == 'entry':
                if not move.is_invoice():
                    continue

                for move_line in move.line_ids.filtered(
                        lambda line: not (move.move_type in (
                                'out_invoice',
                                'out_refund') and line.account_id.internal_group == 'asset')):
                    if (
                            move_line.account_id
                            and (move_line.account_id.can_create_asset)
                            and move_line.account_id.create_asset != "no"
                            and not move.reversed_entry_id
                            and not (
                            move_line.currency_id or move.currency_id).is_zero(
                        move_line.price_total)
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
                            units_quantity = move_line.product_uom_id._compute_quantity(
                                move_line.quantity, unit_uom, False)
                        else:
                            units_quantity = 1
                        i = 0
                        rec = self.env['stock.valuation.layer'].search(
                            [('account_move_id', '=', move_line.move_id.id)])
                        while units_quantity > 0:
                            if units_quantity > 1:
                                original_value = float_round(
                                    amount_left / units_quantity,
                                    precision_rounding=move_line.company_currency_id.rounding)
                                amount_left = float_round(
                                    amount_left - original_value,
                                    precision_rounding=move_line.company_currency_id.rounding)
                            else:
                                original_value = amount_left

                            if len(rec.stock_move_id.move_line_ids) > 1:
                                sn = rec.stock_move_id.move_line_ids[i].lot_id.name
                            else:
                                sn = rec.stock_move_id.move_line_ids[0].lot_id.name

                            vals = {
                                'name': move_line.name,
                                'company_id': move_line.company_id.id,
                                'currency_id': move_line.company_currency_id.id,
                                'analytic_account_id': move_line.analytic_account_id.id,
                                'business_unit_id': move_line.business_unit_id.id,
                                'project_site_id': move_line.project_site_id.id,
                                'analytic_distribution': move_line.analytic_distribution,
                                'original_move_line_ids': [
                                    (6, False, move_line.ids)],
                                'state': 'draft',
                                'original_value': original_value,
                                'prorata_date': move.date,
                                'accounting_date': move.date,
                                'barcode': move_line.product_id.barcode,
                                'sn': sn,
                            }
                            i+=1
                            model_id = move_line.account_id.asset_model
                            if model_id:
                                vals.update({
                                    'model_id': model_id.id,
                                })
                            auto_validate.append(
                                move_line.account_id.create_asset == 'validate')
                            invoice_list.append(move)
                            create_list.append(vals)
                            units_quantity -= 1
            else:
                # to create asset based on the account configured in move lines and restricted if there already asset ex
                if not move.asset_id:
                    for move_line in move.line_ids.filtered(
                            lambda line: not (move.move_type in (
                                    'out_invoice',
                                    'out_refund') and line.account_id.internal_group == 'asset')):
                        if (
                                move_line.account_id
                                and (move_line.account_id.can_create_asset)
                                and move_line.account_id.create_asset != "no"
                                and not move.reversed_entry_id
                                and not move_line.asset_ids
                        ):
                            if not move_line.name:
                                raise UserError(
                                    _('Journal Items of {account} should have a label in order to generate an asset').format(
                                        account=move_line.account_id.display_name))
                            amount_total = amount_left = move_line.debit + move_line.credit
                            unit_uom = self.env.ref('uom.product_uom_unit')
                            if move_line.account_id.multiple_assets_per_line and (
                                    (
                                            move_line.product_uom_id and move_line.product_uom_id.category_id.id == unit_uom.category_id.id) or not move_line.product_uom_id):
                                units_quantity = move_line.product_uom_id._compute_quantity(
                                    move_line.quantity, unit_uom, False)
                            else:
                                units_quantity = 1
                            i = 0
                            rec = self.env['stock.valuation.layer'].search(
                                [('account_move_id', '=', move_line.move_id.id)])
                            units_quantity = abs(units_quantity)
                            while units_quantity > 0:
                                if units_quantity > 1:
                                    original_value = float_round(
                                        amount_left / units_quantity,
                                        precision_rounding=move_line.company_currency_id.rounding)
                                    amount_left = float_round(
                                        amount_left - original_value,
                                        precision_rounding=move_line.company_currency_id.rounding)
                                else:
                                    original_value = amount_left


                                if len(rec.stock_move_id.move_line_ids) > 1:
                                    sn = rec.stock_move_id.move_line_ids[i].lot_id.name
                                else:
                                    sn = rec.stock_move_id.move_line_ids[0].lot_id.name
                                vals = {
                                    'name': move_line.name,
                                    'company_id': move_line.company_id.id,
                                    'currency_id': move_line.company_currency_id.id,
                                    'analytic_account_id': move_line.analytic_account_id.id,
                                    'project_site_id': move_line.project_site_id.id,
                                    'business_unit_id': move_line.business_unit_id.id,
                                    'analytic_distribution': move_line.analytic_distribution,
                                    'original_move_line_ids': [
                                        (6, False, move_line.ids)],
                                    'state': 'draft',
                                    'original_value': original_value,
                                    'prorata_date': move.date,
                                    'accounting_date': move.date,
                                    'barcode': move_line.product_id.barcode,
                                    'sn': sn,
                                }
                                i += 1
                                model_id = move_line.account_id.asset_model
                                if model_id:
                                    vals.update({
                                        'model_id': model_id.id,
                                    })
                                auto_validate.append(
                                    move_line.account_id.create_asset == 'validate')
                                invoice_list.append(move)
                                create_list.append(vals)
                                units_quantity -= 1

        assets = self.env['account.asset'].create(create_list)
        for asset, vals, invoice, validate in zip(assets, create_list,
                                                  invoice_list, auto_validate):
            if 'model_id' in vals:
                asset.with_context(auto_create_asset=True)._onchange_model_id()
                if validate:
                    asset.validate()
            if invoice:
                asset.message_post(body=escape(
                    _('Asset created from invoice: %s')) % invoice._get_html_link())
                asset._post_non_deductible_tax_value()
        return assets

    @api.model
    def _prepare_move_for_asset_depreciation(self, vals):
        missing_fields = set(
            ['asset_id', 'amount', 'depreciation_beginning_date', 'date',
             'asset_number_days']) - set(vals)
        if missing_fields:
            raise UserError(_('Some fields are missing {}').format(
                ', '.join(missing_fields)))
        asset = vals['asset_id']
        analytic_distribution = asset.analytic_distribution
        project_site_id = asset.project_site_id
        analytic_account_id = asset.analytic_account_id
        depreciation_date = vals.get('date', fields.Date.context_today(self))
        company_currency = asset.company_id.currency_id
        current_currency = asset.currency_id
        prec = company_currency.decimal_places
        amount_currency = vals['amount']
        amount = current_currency._convert(amount_currency, company_currency,
                                           asset.company_id, depreciation_date)
        # Keep the partner on the original invoice if there is only one
        partner = asset.original_move_line_ids.mapped('partner_id')
        partner = partner[:1] if len(partner) <= 1 else self.env['res.partner']
        move_line_1 = {
            'name': asset.name,
            'partner_id': partner.id,
            'account_id': asset.account_depreciation_id.id,
            'debit': 0.0 if float_compare(amount, 0.0,
                                          precision_digits=prec) > 0 else -amount,
            'credit': amount if float_compare(amount, 0.0,
                                              precision_digits=prec) > 0 else 0.0,
            'analytic_distribution': analytic_distribution,
            'project_site_id': project_site_id.id if project_site_id else False,
            'business_unit_id': asset.business_unit_id.id if asset.business_unit_id else False,
            'analytic_account_id': analytic_account_id.id if analytic_account_id.id else False,
            'currency_id': current_currency.id,
            'amount_currency': -amount_currency,
        }
        move_line_2 = {
            'name': asset.name,
            'partner_id': partner.id,
            'account_id': asset.account_depreciation_expense_id.id,
            'credit': 0.0 if float_compare(amount, 0.0,
                                           precision_digits=prec) > 0 else -amount,
            'debit': amount if float_compare(amount, 0.0,
                                             precision_digits=prec) > 0 else 0.0,
            'analytic_distribution': analytic_distribution,
            'business_unit_id': asset.business_unit_id.id if asset.business_unit_id else False,
            'project_site_id': project_site_id.id if project_site_id else False,
            'analytic_account_id': analytic_account_id.id if analytic_account_id.id else False,
            'currency_id': current_currency.id,
            'amount_currency': amount_currency,
        }
        move_vals = {
            'partner_id': partner.id,
            'date': depreciation_date,
            'journal_id': asset.journal_id.id,
            'line_ids': [(0, 0, move_line_1), (0, 0, move_line_2)],
            'asset_id': asset.id,
            'ref': vals["move_ref"] if vals.get('move_ref') else _("%s: Depreciation", asset.name) if not asset.is_accrual else _("%s: Accrual", asset.name),
            'asset_depreciation_beginning_date': vals[
                'depreciation_beginning_date'],
            'asset_number_days': vals['asset_number_days'],
            'name': '/',
            'asset_value_change': vals.get('asset_value_change', False),
            'move_type': 'entry',
            'currency_id': current_currency.id,
        }
        return move_vals


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    analytic_account_id = fields.Many2one(
        comodel_name="account.analytic.account", string='Cost Center', domain=[
            ('analytic_account_type', '=',
             'cost_center')])
    project_site_id = fields.Many2one(comodel_name="account.analytic.account",
                                      string="Project/Site",
                                      domain=[
                                          ('analytic_account_type', '=',
                                           'project_site')],
                                      required=False, store=True)
    business_unit_id = fields.Many2one(comodel_name="account.analytic.account",
                                       string="Business Unit",
                                       domain=[('plan_id.name', '=ilike', 'Business Unit')],
                                       required=False, store=True)
    type_id = fields.Many2one(comodel_name="account.analytic.account",
                              string="Type",
                              domain=[('analytic_account_type', '=', 'type')],
                              required=False, )
    location_id = fields.Many2one(comodel_name="account.analytic.account",
                                  string="Location", domain=[
            ('analytic_account_type', '=', 'location')], required=False, )
    budget_id = fields.Many2one(comodel_name="crossovered.budget",
                                string="Budget", required=False, index=True, copy=False)
    budget_line_id = fields.Many2one(comodel_name="crossovered.budget.lines",
                                     string="Budget Line", required=False,
                                     index=True, copy=False)

    remaining_amount = fields.Float(string="Remaining Amount", required=False,
                                    compute='get_budget_remaining_amount', store=True
                                    )
    local_subtotal = fields.Float(compute='compute_local_subtotal', store=True)
    site_status = fields.Selection(
        [('on_air', 'ON AIR'), ('off_air', 'OFF AIR'), ],
        string='Site Status')
    t_budget = fields.Selection(
        [('capex', 'CAPEX'), ('opex', 'OPEX'), ],
        string='T.Budget')
    t_budget_name = fields.Char(string="T.Budget Name")
    account_id = fields.Many2one(
        comodel_name='account.account',
        string='Account',
        compute='_compute_account_id', store=True, readonly=False, precompute=True,
        inverse='_inverse_account_id',
        index=True,  # covered by account_move_line_account_id_date_idx defined in init()
        auto_join=True,
        ondelete="cascade",
        domain="[('deprecated', '=', False), ('account_type', '!=', 'off_balance')]",
        check_company=True,
        tracking=True,
    )

    @api.onchange('name')
    def _onchange_name_predictive(self):
        if ((
                self.move_id.quick_edit_mode or self.move_id.move_type == 'in_invoice') and self.name and self.display_type == 'product'
                and not self.env.context.get('disable_onchange_name_predictive', False)):
            if not self.product_id:
                predicted_product_id = self._predict_product()
                if predicted_product_id:
                    # We only update the price_unit, tax_ids and name in case they evaluate to False
                    protected_fields = ['price_unit', 'tax_ids', 'name']
                    to_protect = [self._fields[fname] for fname in protected_fields if self[fname]]
                    with self.env.protecting(to_protect, self):
                        self.product_id = predicted_product_id


    @api.onchange('t_budget', 'project_site_id', 'site_status', 'product_id')
    def onchange_t_budget(self):
        journals = self.env['account.journal'].search([
            '|',
            ('name', 'ilike', 'Inventory Valuation'),
            ('name', 'ilike', 'Vendor Bills')
        ])
        if self.product_id:
            if self.journal_id.id in journals.ids:
                if self.purchase_line_id:
                    if self.product_id.detailed_type == 'product':
                        self.account_id = self.product_id.categ_id.property_stock_account_input_categ_id.id
                    elif self.product_id.detailed_type == 'consu' or self.product_id.detailed_type == 'service':
                        if self.t_budget == 'opex':
                            if self.project_site_id and self.project_site_id.is_inventory:
                                self.account_id = self.product_id.inventory_account_id.id
                            else:
                                self.account_id = self.product_id.property_account_expense_id.id
                        elif self.t_budget == 'capex':
                            if self.project_site_id and self.project_site_id.is_inventory:
                                self.account_id = self.product_id.inventory_account_id.id
                            elif self.project_site_id and not self.project_site_id.is_inventory:
                                if self.site_status == 'off_air':
                                    self.account_id = self.product_id.cip_account_id.id
                                elif self.site_status == 'on_air':
                                    self.account_id = self.product_id.asset_account_id.id
                                else:
                                    self.account_id = self.product_id.asset_account_id.id
                            else:
                                if self.site_status == 'off_air':
                                    self.account_id = self.product_id.cip_account_id.id
                                elif self.site_status == 'on_air':
                                    self.account_id = self.product_id.asset_account_id.id
                                else:
                                    self.account_id = self.product_id.asset_account_id.id
                        else:
                            self.account_id = self.product_id.property_account_expense_id.id
                    else:
                        self.account_id = self.product_id.property_account_expense_id.id
                else:
                    if self.product_id.detailed_type in ['product', 'consu']:
                        if self.t_budget == 'opex':
                            if self.project_site_id and self.project_site_id.is_inventory:
                                self.account_id = self.product_id.inventory_account_id.id
                            else:
                                self.account_id = self.product_id.property_account_expense_id.id
                        elif self.t_budget == 'capex':
                            if self.project_site_id and self.project_site_id.is_inventory:
                                self.account_id = self.product_id.inventory_account_id.id
                            elif self.project_site_id and not self.project_site_id.is_inventory:
                                if self.site_status == 'off_air':
                                    self.account_id = self.product_id.cip_account_id.id
                                elif self.site_status == 'on_air':
                                    self.account_id = self.product_id.asset_account_id.id
                                else:
                                    self.account_id = self.product_id.asset_account_id.id
                            else:
                                if self.site_status == 'off_air':
                                    self.account_id = self.product_id.cip_account_id.id
                                elif self.site_status == 'on_air':
                                    self.account_id = self.product_id.asset_account_id.id
                                else:
                                    self.account_id = self.product_id.asset_account_id.id
                        else:
                            self.account_id = self.product_id.property_account_expense_id.id
                    else:
                        self.account_id = self.product_id.property_account_expense_id.id

    @api.onchange('analytic_distribution')
    def _inverse_analytic_distribution(self):
        """ Unlink and recreate analytic_lines when modifying the distribution."""
        lines_to_modify = self.env['account.move.line'].browse([
            line.id for line in self if line.parent_state == "posted"
        ])
        lines_to_modify.analytic_line_ids.unlink()
        lines_to_modify._create_analytic_lines()

    @api.onchange('budget_id')
    def onchange_budget_id(self):
        return {'domain': {'budget_line_id': [
            ('crossovered_budget_id', '=', self.budget_id.id)]}}

    @api.depends('price_subtotal')
    def compute_local_subtotal(self):
        for rec in self:
            if rec.move_id.move_type == 'entry':
                rec.local_subtotal = abs(rec.credit) if rec.credit else abs(
                    rec.debit)
            else:
                if rec.move_id and rec.price_subtotal:
                    rec.local_subtotal = rec.move_id.currency_id._convert(
                        rec.price_subtotal,
                        rec.move_id.company_id.currency_id,
                        rec.move_id.company_id,
                        rec.move_id.invoice_date if rec.move_id.invoice_date else rec.move_id.create_date.date())
                else:
                    rec.local_subtotal = 0

    @api.depends('budget_id', 'purchase_line_id', 'sale_line_ids',
                 'budget_line_id.remaining_amount')
    def get_budget_remaining_amount(self):
        for rec in self:
            rec.remaining_amount = 0.0
            if rec.purchase_line_id:
                rec.remaining_amount = rec.purchase_line_id.remaining_amount
            elif rec.sale_line_ids:
                rec.remaining_amount = rec.sale_line_ids[0].remaining_amount
            else:
                rec.remaining_amount = rec.budget_line_id.remaining_amount

    def _prepare_analytic_distribution_line(self, distribution, account_ids, distribution_on_each_plan):
        """ Prepare the values used to create() an account.analytic.line upon validation of an account.move.line having
            analytic tags with analytic distribution.
        """
        self.ensure_one()
        account_field_values = {}
        decimal_precision = self.env['decimal.precision'].precision_get('Percentage Analytic')
        amount = 0
        stripped = account_ids.lstrip()
        if stripped.startswith(','):
            account_ids = stripped[1:]
        else:
            account_ids = account_ids

        for account in self.env['account.analytic.account'].browse(map(int, account_ids.split(","))).exists():
            distribution_plan = distribution_on_each_plan.get(account.root_plan_id, 0) + distribution
            if float_compare(distribution_plan, 100, precision_digits=decimal_precision) == 0:
                amount = -self.balance * (100 - distribution_on_each_plan.get(account.root_plan_id, 0)) / 100.0
            else:
                amount = -self.balance * distribution / 100.0
            distribution_on_each_plan[account.root_plan_id] = distribution_plan
            account_field_values[account.plan_id._column_name()] = account.id
        default_name = self.name or (self.ref or '/' + ' -- ' + (self.partner_id and self.partner_id.name or '/'))
        return {
            'name': default_name,
            'date': self.date,
            **account_field_values,
            'partner_id': self.partner_id.id,
            'unit_amount': self.quantity,
            'product_id': self.product_id and self.product_id.id or False,
            'product_uom_id': self.product_uom_id and self.product_uom_id.id or False,
            'amount': amount,
            'general_account_id': self.account_id.id,
            'ref': self.ref,
            'move_line_id': self.id,
            'user_id': self.move_id.invoice_user_id.id or self._uid,
            'company_id': self.company_id.id or self.env.company.id,
            'category': 'invoice' if self.move_id.is_sale_document() else 'vendor_bill' if self.move_id.is_purchase_document() else 'other',
        }
