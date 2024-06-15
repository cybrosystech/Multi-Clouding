from email.policy import default

from markupsafe import escape
from odoo import models, _, fields
from odoo.exceptions import UserError


class AccountMoveReversalInherit(models.TransientModel):
    _inherit = 'account.move.reversal'

    def reverse_moves(self, is_modify=False):
        self.ensure_one()
        moves = self.move_ids

        # Create default values.
        default_values_list = []
        for move in moves:
            default_values_list.append(self._prepare_default_reversal(move))

        batches = [
            [self.env['account.move'], [], True],   # Moves to be cancelled by the reverses.
            [self.env['account.move'], [], False],  # Others.
        ]
        for move, default_vals in zip(moves, default_values_list):
            is_auto_post = default_vals.get('auto_post') != 'no'
            is_cancel_needed = not is_auto_post and is_modify
            batch_index = 0 if is_cancel_needed else 1
            batches[batch_index][0] |= move
            batches[batch_index][1].append(default_vals)

        # Handle reverse method.
        moves_to_redirect = self.env['account.move']
        for moves, default_values_list, is_cancel_needed in batches:
            new_moves = moves._reverse_moves(default_values_list, cancel=is_cancel_needed)
            moves._message_log_batch(
                bodies=dict((move.id, escape(_('This entry has been %s')) % reverse._get_html_link(title=_("reversed"))) for move, reverse in zip(moves, new_moves))
            )
            if moves and new_moves:
                # new_moves.button_draft()
                message = 'Number: ' + moves.name + \
                          '\n Created the reverse entry\n' + \
                          ' Reverse Entry/: ' + new_moves.name + \
                          '\nStatus: ' + new_moves.state
                moves.reverse_boolean = True
                moves.message_post(body=message)

            if is_modify:
                moves_vals_list = []
                for move in moves.with_context(include_business_fields=True):
                    moves_vals_list.append(move.copy_data({'date': self.date})[0])
                new_moves = self.env['account.move'].create(moves_vals_list)

            moves_to_redirect |= new_moves

        self.new_move_ids = moves_to_redirect

        # Create action.
        action = {
            'name': _('Reverse Moves'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
        }
        if len(moves_to_redirect) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': moves_to_redirect.id,
                'context': {'default_move_type':  moves_to_redirect.move_type},
            })
        else:
            action.update({
                'view_mode': 'tree,form',
                'domain': [('id', 'in', moves_to_redirect.ids)],
            })
            if len(set(moves_to_redirect.mapped('move_type'))) == 1:
                action['context'] = {'default_move_type':  moves_to_redirect.mapped('move_type').pop()}
        return action

class AccountMoveInherit(models.Model):
    _inherit = "account.move"

    reverse_boolean = fields.Boolean(default=False, string='Reverse Entry',copy=False)
    request_approve_bool = fields.Boolean(default=False,copy=False)
    leasee_contract_id = fields.Many2one(comodel_name="leasee.contract",
                                         index=True)

    def button_draft(self):
        res = super().button_draft()
        if any(move.state not in ('cancel', 'posted', 'to_approve') for move in self):
            raise UserError(_("Only posted/cancelled journal entries can be reset to draft."))

        exchange_move_ids = set()
        if self:
            self.env['account.full.reconcile'].flush_model(['exchange_move_id'])
            self.env['account.partial.reconcile'].flush_model(['exchange_move_id'])
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
                raise UserError(_('You cannot reset to draft an exchange difference journal entry.'))
            if move.tax_cash_basis_rec_id or move.tax_cash_basis_origin_move_id:
                # If the reconciliation was undone, move.tax_cash_basis_rec_id will be empty;
                # but we still don't want to allow setting the caba entry to draft
                # (it'll have been reversed automatically, so no manual intervention is required),
                # so we also check tax_cash_basis_origin_move_id, which stays unchanged
                # (we need both, as tax_cash_basis_origin_move_id did not exist in older versions).
                raise UserError(_('You cannot reset to draft a tax cash basis journal entry.'))
            if move.restrict_mode_hash_table and move.state == 'posted':
                raise UserError(_('You cannot modify a posted entry of this journal because it is in strict mode.'))
            # We remove all the analytics entries for this journal
            move.mapped('line_ids.analytic_line_ids').unlink()

        self.mapped('line_ids').remove_move_reconcile()
        self.write({'state': 'draft', 'is_move_sent': False})
        return res

    def request_approval_button(self):
        self.get_budgets_in_out_budget_tab()
        if self.out_budget and not self.purchase_approval_cycle_ids:
            out_budget_list = []
            out_budget = self.env['budget.in.out.check.invoice'].search(
                [('type', '=', 'out_budget'),
                 ('company_id', '=', self.env.company.id)], limit=1)
            max_value = max(self.budget_collect_ids.mapped('demand_amount'))
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
                max_value = sum(
                    self.line_ids.mapped('debit'))  # Old Field is debit
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

    def button_draft(self):
        res = super(AccountMoveInherit, self).button_draft()
        self.request_approve_bool = False
        return res
