import calendar

from odoo import models, fields, _, Command, api
from odoo.exceptions import UserError, ValidationError


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    deferred_account_id = fields.Many2one('account.account',
                                          string="Deferred Account",
                                          domain="[('account_type','in',['asset_prepayments','asset_current','liability_current'])]",
                                          copy=False)

    @api.model
    def _get_deferred_lines_values(self, account_id, balance, ref, analytic_distribution, line):
        deferred_lines_values = super()._get_deferred_lines_values(account_id, balance, ref, analytic_distribution)
        return {
            **deferred_lines_values,
            'project_site_id': int(line['project_site_id'] or 0) or None,
            'analytic_account_id': int(line['analytic_account_id'] or 0) or None,
        }


class AccountMove(models.Model):
    _inherit = 'account.move'

    def request_approval_button(self):
        if any(not c.deferred_account_id and (
                c.deferred_start_date != False or c.deferred_end_date != False)
               for c in self.invoice_line_ids):
            raise ValidationError(
                _('Please set deferred account on invoice lines.'))
        else:
            res = super().request_approval_button()

    def button_request_purchase_cycle(self):
        for rec in self:
            if any(not c.deferred_account_id and (
                    c.deferred_start_date != False or c.deferred_end_date != False)
                   for c in rec.invoice_line_ids):
                raise ValidationError(
                    _('Please set deferred account on invoice lines.'))
            else:
                res = super(AccountMove, rec).button_request_purchase_cycle()

    def is_month_end(self,date):
        # Get the last day of the given month
        _, last_day = calendar.monthrange(date.year, date.month)
        return date.day == last_day

    def _generate_deferred_entries(self):
        """
        Generates the deferred entries for the invoice.
        """
        self.ensure_one()
        if self.is_entry():
            raise UserError(
                _("You cannot generate deferred entries for a miscellaneous journal entry."))
        assert not self.deferred_move_ids, "The deferred entries have already been generated for this document."
        is_deferred_expense = self.is_purchase_document()
        deferred_journal = self.company_id.deferred_journal_id
        if not deferred_journal:
            raise UserError(
                _("Please set the deferred journal in the accounting settings."))

        for line in self.line_ids.filtered(
                lambda l: l.deferred_start_date and l.deferred_end_date and not l.tax_line_id):
            if is_deferred_expense:
                if not line.deferred_account_id and not line.tax_line_id:
                    raise UserError(
                        _("Deferred account cannot be empty if deferred start "
                          "date and deferred end date is set."))
                else:
                    deferred_account = line.deferred_account_id if line.deferred_account_id else False
            else:
                if not line.deferred_account_id and not line.tax_line_id:
                    raise UserError(
                        _("Deferred account cannot be empty if deferred start "
                          "date and deferred end date is set."))
                else:
                    deferred_account = line.deferred_account_id if line.deferred_account_id else False
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
                        self.env[
                            'account.move.line']._get_deferred_lines_values(
                            account.id, coeff * line.balance, ref,
                            line.analytic_distribution, line)
                    ) for (account, coeff) in
                    [(line.account_id, -1), (deferred_account, 1)]
                ],
            })
            line.move_id.deferred_move_ids |= move_fully_deferred
            move_fully_deferred._post(soft=True)

            # Create the deferred entries for the periods [deferred_start_date, deferred_end_date]
            remaining_balance = line.balance
            for period_index, period in enumerate(periods):
                if period[1] == line.deferred_start_date and self.is_month_end(period[1]):
                    continue
                else:
                    if period[1] >= self.invoice_date and period[1] <= self.date:
                        deferral_move = self.create({
                            'move_type': 'entry',
                            'deferred_original_move_ids': [
                                Command.set(line.move_id.ids)],
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
                    force_balance = remaining_balance if period_index == len(
                        periods) - 1 else None
                    # Same as before, to avoid adding taxes for deferred moves.
                    deferral_move.write({
                        'line_ids': self._get_deferred_lines(line, deferred_account,
                                                             period, ref,
                                                             force_balance=force_balance),
                    })
                    remaining_balance -= deferral_move.line_ids[0].balance
                    line.move_id.deferred_move_ids |= deferral_move
                    deferral_move._post(soft=True)
