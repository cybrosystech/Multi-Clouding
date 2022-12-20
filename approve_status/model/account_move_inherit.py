from email.policy import default

from odoo import models, _, fields


class AccountMoveReversalInherit(models.TransientModel):
    _inherit = 'account.move.reversal'

    def reverse_moves(self):
        self.ensure_one()
        moves = self.move_ids

        # Create default values.
        default_values_list = []
        for move in moves:
            default_values_list.append(self._prepare_default_reversal(move))

        batches = [
            [self.env['account.move'], [], True],
            # Moves to be cancelled by the reverses.
            [self.env['account.move'], [], False],  # Others.
        ]
        for move, default_vals in zip(moves, default_values_list):
            is_auto_post = bool(default_vals.get('auto_post'))
            is_cancel_needed = not is_auto_post and self.refund_method in (
                'cancel', 'modify')
            batch_index = 0 if is_cancel_needed else 1
            batches[batch_index][0] |= move
            batches[batch_index][1].append(default_vals)

        # Handle reverse method.
        moves_to_redirect = self.env['account.move']
        for moves, default_values_list, is_cancel_needed in batches:
            new_moves = moves._reverse_moves(default_values_list,
                                             cancel=is_cancel_needed)
            if moves and new_moves:
                new_moves.button_draft()
                message = 'Number/: ' + moves.name + \
                          '<br/>Created the reverse entry<br/>' + \
                          'Reverse Entry/: ' + new_moves.name + \
                          '<br/>Status: ' + new_moves.state
                moves.reverse_boolean = True
                moves.message_post(body=message)

            if self.refund_method == 'modify':
                moves_vals_list = []
                for move in moves.with_context(include_business_fields=True):
                    moves_vals_list.append(move.copy_data({
                        'date': self.date if self.date_mode == 'custom' else move.date})[
                                               0])
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
                'context': {'default_move_type': moves_to_redirect.move_type},
            })
        else:
            action.update({
                'view_mode': 'tree,form',
                'domain': [('id', 'in', moves_to_redirect.ids)],
            })
            if len(set(moves_to_redirect.mapped('move_type'))) == 1:
                action['context'] = {
                    'default_move_type': moves_to_redirect.mapped(
                        'move_type').pop()}
        return action


class AccountMoveInherit(models.Model):
    _inherit = "account.move"

    reverse_boolean = fields.Boolean(default=False, string='Reverse Entry')
    request_approve_bool = fields.Boolean(default=False)

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

    def button_draft(self):
        res = super(AccountMoveInherit, self).button_draft()
        self.request_approve_bool = False
        return res
