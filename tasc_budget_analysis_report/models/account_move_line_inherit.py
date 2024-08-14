from odoo import models, fields, _
from odoo.addons.approve_status.model.account_move_inherit import \
    AccountMoveInherit
from odoo.addons.analytic_account_types.models.account_move_line import AccountMove

from odoo.exceptions import UserError


class AccountMoveBudgetConf(models.Model):
    _inherit = 'account.move'

    budget_collect_copy_ids = fields.One2many(
        comodel_name="budget.collect.copy",
        inverse_name="move_id", string="",
        required=False, )
    leasee_contract_id = fields.Many2one(comodel_name="leasee.contract",
                                         index=True)

    def button_draft(self):
        if any(move.state not in ('cancel', 'posted','to_approve') for move in self):
            raise UserError(
                _("Only posted/cancelled journal entries can be reset to draft."))

        exchange_move_ids = set()
        if self:
            self.env['account.full.reconcile'].flush_model(['exchange_move_id'])
            self.env['account.partial.reconcile'].flush_model(
                ['exchange_move_id'])
            self._cr.execute(
                """
                    SELECT DISTINCT sub.exchange_move_id
                    FROM (
                        SELECT exchange_move_id
                        FROM account_full_reconcile
                        WHERE exchange_move_id IN %s

                        UNION ALL

                        SELECT exchange_move_id
                        FROM account_partial_reconcile
                        WHERE exchange_move_id IN %s
                    ) AS sub
                """,
                [tuple(self.ids), tuple(self.ids)],
            )
            exchange_move_ids = set([row[0] for row in self._cr.fetchall()])

        for move in self:
            if move.id in exchange_move_ids:
                raise UserError(
                    _('You cannot reset to draft an exchange difference journal entry.'))
            if move.tax_cash_basis_rec_id or move.tax_cash_basis_origin_move_id:
                # If the reconciliation was undone, move.tax_cash_basis_rec_id will be empty;
                # but we still don't want to allow setting the caba entry to draft
                # (it'll have been reversed automatically, so no manual intervention is required),
                # so we also check tax_cash_basis_origin_move_id, which stays unchanged
                # (we need both, as tax_cash_basis_origin_move_id did not exist in older versions).
                raise UserError(
                    _('You cannot reset to draft a tax cash basis journal entry.'))
            if move.restrict_mode_hash_table and move.state == 'posted':
                raise UserError(
                    _('You cannot modify a posted entry of this journal because it is in strict mode.'))
            # We remove all the analytics entries for this journal
            move.mapped('line_ids.analytic_line_ids').unlink()

        self.mapped('line_ids').remove_move_reconcile()
        self.write({'state': 'draft', 'is_move_sent': False})
        self.request_approve_bool = False
        self.show_approve_button = False

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
    self.budget_collect_copy_ids = [(5, 0, 0)]
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
        if self.move_type == 'entry':
            max_value = sum(self.line_ids.mapped('debit'))  # Old Field is debit
        else:
            max_value = sum(self.invoice_line_ids.mapped('local_subtotal'))
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


def button_request_purchase_cycle(self):
    for record in self:
        record.configure_budget_line()
        lines = record.line_ids.filtered(
            lambda
                x: x.remaining_amount < x.debit or x.remaining_amount < x.credit)
        record.budget_collect_copy_ids = [(5, 0, 0)]
        for line in lines:
            if line.budget_id:
                self.env['budget.collect.copy'].create({
                    'budget_id': line.budget_id.id,
                    'budget_line_id': line.budget_line_id.id,
                    'remaining_amount_copy': line.remaining_amount,
                    'demand_amount_copy': line.debit,
                    'difference_amount_copy': line.remaining_amount - line.debit,
                    'move_id': record.id
                })
        record.get_budgets_in_out_budget_tab()
        if record.out_budget and not record.purchase_approval_cycle_ids:
            out_budget_list = []
            out_budget = self.env['budget.in.out.check.invoice'].search(
                [('type', '=', 'out_budget'),
                 ('company_id', '=', self.env.company.id)], limit=1)
            if record.move_type == 'entry':
                max_value = sum(
                    record.line_ids.mapped('debit'))  # Old Field is debit
            else:
                max_value = sum(record.invoice_line_ids.mapped('local_subtotal'))
            for rec in out_budget.budget_line_ids:
                if max_value >= rec.from_amount:
                    out_budget_list.append((0, 0, {
                        'approval_seq': rec.approval_seq,
                        'user_approve_ids': rec.user_ids.ids,
                    }))
            record.write({'purchase_approval_cycle_ids': out_budget_list})
            record.request_approve_bool = True
        if not record.out_budget and not record.purchase_approval_cycle_ids:
            in_budget_list = []
            in_budget = self.env['budget.in.out.check.invoice'].search(
                [('type', '=', 'in_budget'),
                 ('company_id', '=', self.env.company.id)], limit=1)
            if record.move_type == 'entry':
                max_value = sum(
                    record.line_ids.mapped('debit'))  # Old Field is debit
            else:
                max_value = sum(record.invoice_line_ids.mapped('local_subtotal'))
            for rec in in_budget.budget_line_ids:
                if max_value >= rec.from_amount:
                    in_budget_list.append((0, 0, {
                        'approval_seq': rec.approval_seq,
                        'user_approve_ids': rec.user_ids.ids,
                    }))

            record.write({'purchase_approval_cycle_ids': in_budget_list})
            record.request_approve_bool = True
        record.show_request_approve_button = True
        if record.purchase_approval_cycle_ids:
            min_seq_approval = min(
                record.purchase_approval_cycle_ids.mapped('approval_seq'))
            notification_to_user = record.purchase_approval_cycle_ids.filtered(
                lambda x: x.approval_seq == int(min_seq_approval))
            user = notification_to_user.user_approve_ids
            record.state = 'to_approve'
            record.send_user_notification(user)
            record.request_approve_bool = True


        # journals = self.env['account.move'].search([('id', '=', rec.id)])
        # journals.get_budgets_in_out_budget_tab()
        # if journals.out_budget and not journals.purchase_approval_cycle_ids:
        #     out_budget_list = []
        #     out_budget = journals.env['budget.in.out.check.invoice'].search(
        #         [('type', '=', 'out_budget'),
        #          ('company_id', '=', journals.env.company.id)], limit=1)
        #     max_value = max(
        #         journals.budget_collect_ids.mapped('demand_amount'))
        #     for rec in out_budget.budget_line_ids:
        #         if max_value >= rec.from_amount:
        #             out_budget_list.append((0, 0, {
        #                 'approval_seq': rec.approval_seq,
        #                 'user_approve_ids': rec.user_ids.ids,
        #             }))
        #
        #     journals.write({'purchase_approval_cycle_ids': out_budget_list})
        # if not journals.out_budget and not journals.purchase_approval_cycle_ids:
        #     in_budget_list = []
        #     in_budget = journals.env['budget.in.out.check.invoice'].search(
        #         [('type', '=', 'in_budget'),
        #          ('company_id', '=', journals.env.company.id)], limit=1)
        #     if journals.move_type == 'endef request_approval_buttontry':
        #         max_value = max(journals.line_ids.mapped(
        #             'local_subtotal'))  # Old Field is debit
        #     else:
        #         max_value = sum(
        #             journals.invoice_line_ids.mapped('local_subtotal'))
        #     for rec in in_budget.budget_line_ids:
        #         if max_value >= rec.from_amount:
        #             in_budget_list.append((0, 0, {
        #                 'approval_seq': rec.approval_seq,
        #                 'user_approve_ids': rec.user_ids.ids,
        #             }))
        #
        #     journals.write({'purchase_approval_cycle_ids': in_budget_list})
        # journals.show_request_approve_button = True
        # if journals.purchase_approval_cycle_ids:
        #     min_seq_approval = min(
        #         journals.purchase_approval_cycle_ids.mapped('approval_seq'))
        #     notification_to_user = journals.purchase_approval_cycle_ids.filtered(
        #         lambda x: x.approval_seq == int(min_seq_approval))
        #     user = notification_to_user.user_approve_ids
        #     journals.state = 'to_approve'
        #     journals.send_user_notification(user)


AccountMoveInherit.request_approval_button = request_approval_button
AccountMove.button_request_purchase_cycle = button_request_purchase_cycle
