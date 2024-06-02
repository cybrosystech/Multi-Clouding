from odoo import models, fields,_,Command
from odoo.exceptions import UserError


class AccountMoveLeaseSecurity(models.Model):
    _inherit = 'account.move'

    lease_security_advance_id = fields.Many2one('leasee.security.advance')

    def _generate_deferred_entries(self):
        """
        Generates the deferred entries for the invoice.
        """
        self.ensure_one()
        if self.is_entry():
            raise UserError(_("You cannot generate deferred entries for a miscellaneous journal entry."))
        assert not self.deferred_move_ids, "The deferred entries have already been generated for this document."
        is_deferred_expense = self.is_purchase_document()
        deferred_account = self.company_id.deferred_expense_account_id if is_deferred_expense else self.company_id.deferred_revenue_account_id
        deferred_journal = self.company_id.deferred_journal_id
        if not deferred_journal:
            raise UserError(_("Please set the deferred journal in the accounting settings."))
        if not deferred_account:
            raise UserError(_("Please set the deferred accounts in the accounting settings."))

        for line in self.line_ids.filtered(lambda l: l.deferred_start_date and l.deferred_end_date):
            periods = line._get_deferred_periods()
            if not periods:
                continue

            ref = _("Deferral of %s", line.move_id.name or '')
            # Defer the current invoice
            move_fully_deferred = self.create({
                'move_type': 'entry',
                'deferred_original_move_ids': [Command.set(line.move_id.ids)],
                'journal_id': deferred_journal.id,
                'company_id': self.company_id.id,
                'partner_id': line.partner_id.id,
                'date': line.move_id.date,
                'auto_post': 'at_date',
                'ref': ref,
            })
            # We write the lines after creation, to make sure the `deferred_original_move_ids` is set.
            # This way we can avoid adding taxes for deferred moves.
            move_fully_deferred.write({
                'line_ids': [
                    Command.create(
                        self.env['account.move.line']._get_deferred_lines_values(account.id, coeff * line.balance, ref, line.analytic_distribution, line)
                    ) for (account, coeff) in [(line.account_id, -1), (deferred_account, 1)]
                ],
            })
            line.move_id.deferred_move_ids |= move_fully_deferred
            move_fully_deferred._post(soft=True)

            # Create the deferred entries for the periods [deferred_start_date, deferred_end_date]
            remaining_balance = line.balance
            for period_index, period in enumerate(periods):
                if period[1] >= self.invoice_date and period[1]<= self.date:
                    deferral_move = self.create({
                        'move_type': 'entry',
                        'deferred_original_move_ids': [Command.set(line.move_id.ids)],
                        'journal_id': deferred_journal.id,
                        'partner_id': line.partner_id.id,
                        'date': self.date,
                        'auto_post': 'at_date',
                        'ref': ref,
                    })
                else:
                    deferral_move = self.create({
                        'move_type': 'entry',
                        'deferred_original_move_ids': [
                            Command.set(line.move_id.ids)],
                        'journal_id': deferred_journal.id,
                        'partner_id': line.partner_id.id,
                        'date': period[1],
                        'auto_post': 'at_date',
                        'ref': ref,
                    })
                # For the last deferral move the balance is forced to remaining balance to avoid rounding errors
                force_balance = remaining_balance if period_index == len(periods) - 1 else None
                # Same as before, to avoid adding taxes for deferred moves.
                deferral_move.write({
                    'line_ids': self._get_deferred_lines(line, deferred_account, period, ref, force_balance=force_balance),
                })
                remaining_balance -= deferral_move.line_ids[0].balance
                line.move_id.deferred_move_ids |= deferral_move
                deferral_move._post(soft=True)


class AccountMoveLineConstraints(models.Model):
    _inherit = "account.move.line"

    def init(self):
        super().init()
        self.env.cr.execute('''
        SELECT
        CONSTRAINT_NAME, CONSTRAINT_TYPE
        FROM
        INFORMATION_SCHEMA.TABLE_CONSTRAINTS
        WHERE
        TABLE_NAME = 'account_move_line' and CONSTRAINT_NAME = 'account_move_line_check_amount_currency_balance_sign';
        ''')
        constraint = self.env.cr.dictfetchall()
        if constraint:
            self.env.cr.execute("""
                        ALTER TABLE account_move_line DROP CONSTRAINT account_move_line_check_amount_currency_balance_sign;
                    """)
