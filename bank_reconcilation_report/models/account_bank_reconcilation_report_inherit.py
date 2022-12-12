from odoo import models, fields, api, _
from odoo.tools.misc import format_date


class AccountBankReconciliationReportInherit(models.AbstractModel):
    _inherit = 'account.bank.reconciliation.report'

    @api.model
    def _get_lines(self, options, line_id=None):
        print_mode = self._context.get('print_mode')
        journal_id = self._context.get('active_id') or options.get('active_id')
        journal = self.env['account.journal'].browse(journal_id)

        if not journal:
            return []

        # Make sure to keep the 'active_id' inside the options to don't depend of the context when printing the report.
        options['active_id'] = journal_id

        company_currency = journal.company_id.currency_id
        journal_currency = journal.currency_id if journal.currency_id and journal.currency_id != company_currency else False
        report_currency = journal_currency or company_currency

        last_statement_domain = [('date', '<=', options['date']['date_to'])]
        if not options['all_entries']:
            last_statement_domain.append(('state', 'in', ['posted', 'confirm']))
        last_statement = journal._get_last_bank_statement(
            domain=last_statement_domain)

        # === Warnings ====

        # Unconsistent statements.
        options[
            'unconsistent_statement_ids'] = self._get_unconsistent_statements(
            options, journal).ids

        # Strange miscellaneous journal items affecting the bank accounts.
        domain = self._get_bank_miscellaneous_move_lines_domain(options,
                                                                journal)
        if domain:
            options['has_bank_miscellaneous_move_lines'] = bool(
                self.env['account.move.line'].search_count(domain))
        else:
            options['has_bank_miscellaneous_move_lines'] = False
        options['account_names'] = journal.default_account_id.display_name

        # ==== Build sub-sections about journal items ====

        plus_st_lines, less_st_lines = self._get_statement_report_lines(options,
                                                                        journal)
        plus_pay_lines, less_pay_lines = self._get_payment_report_lines(options,
                                                                        journal)

        # ==== Build section block about statement lines ====

        domain = self._get_options_domain(options)
        balance_gl = journal._get_journal_bank_account_balance(domain=domain)[0]

        # Compute the 'Reference' cell.
        if last_statement and not print_mode:
            reference_cell = {
                'last_statement_name': last_statement.display_name,
                'last_statement_id': last_statement.id,
                'template': 'account_reports.bank_reconciliation_report_cell_template_link_last_statement',
            }
        else:
            reference_cell = {'name': ''}

        # Compute the 'Amount' cell.
        balance_cell = {
            'name': self.format_value(balance_gl, report_currency),
            'no_format': balance_gl,
        }
        if last_statement:
            report_date = fields.Date.from_string(options['date']['date_to'])
            lines_before_date_to = last_statement.line_ids.filtered(
                lambda line: line.date <= report_date)
            balance_end = last_statement.balance_start + sum(
                lines_before_date_to.mapped('amount'))
            difference = balance_gl - balance_end

            if not report_currency.is_zero(difference):
                balance_cell.update({
                    'template': 'account_reports.bank_reconciliation_report_cell_template_unexplained_difference',
                    'style': 'color:orange;',
                    'title': _(
                        "The current balance in the General Ledger %s doesn't match the balance of your last "
                        "bank statement %s leading to an unexplained difference of %s.") % (
                                 balance_cell['name'],
                                 self.format_value(balance_end,
                                                   report_currency),
                                 self.format_value(difference, report_currency),
                             ),
                })

        balance_gl_report_line = {
            'id': 'balance_gl_line',
            'name': _("Balance of %s", options['account_names']),
            'title_hover': _("The Book balance in Odoo dated today"),
            'columns': self._apply_groups([
                {'name': format_date(self.env, options['date']['date_to']),
                 'class': 'date'},
                reference_cell,
                {'name': ''},
                {'name': ''},
                balance_cell,
            ]),
            'class': 'o_account_reports_totals_below_sections' if self.env.company.totals_below_sections else '',
            'level': 0,
            'unfolded': True,
            'unfoldable': False,
        }

        section_st_report_lines = [
                                      balance_gl_report_line] + plus_st_lines + less_st_lines

        if self.env.company.totals_below_sections:
            section_st_report_lines.append({
                'id': '%s_total' % balance_gl_report_line,
                'name': _("Total %s", balance_gl_report_line['name']),
                'columns': balance_gl_report_line['columns'],
                'class': 'total',
                'level': balance_gl_report_line['level'] + 1,
            })

        # ==== Build section block about payments ====

        section_pay_report_lines = []

        if plus_pay_lines or less_pay_lines:

            # Compute total to display for this section.
            total = 0.0
            if plus_pay_lines:
                total += plus_pay_lines[0]['columns'][-1]['no_format']
            if less_pay_lines:
                total += less_pay_lines[0]['columns'][-1]['no_format']

            outstanding_payments_report_line = {
                'id': 'outstanding_payments',
                'name': _("Outstanding Payments/Receipts"),
                'title_hover': _(
                    "Transactions that were entered into Odoo, but not yet reconciled (Payments triggered by invoices/bills or manually)"),
                'columns': self._apply_groups([
                    {'name': ''},
                    {'name': ''},
                    {'name': ''},
                    {'name': ''},
                    {
                        'name': self.format_value(total, report_currency),
                        'no_format': total,
                    },
                ]),
                'class': 'o_account_reports_totals_below_sections' if self.env.company.totals_below_sections else '',
                'level': 0,
                'unfolded': True,
                'unfoldable': False,
            }
            section_pay_report_lines += [
                                            outstanding_payments_report_line] + plus_pay_lines + less_pay_lines

            if self.env.company.totals_below_sections:
                section_pay_report_lines.append({
                    'id': '%s_total' % outstanding_payments_report_line['id'],
                    'name': _("Total %s",
                              outstanding_payments_report_line['name']),
                    'columns': outstanding_payments_report_line['columns'],
                    'class': 'total',
                    'level': outstanding_payments_report_line['level'] + 1,
                })

        # ==== Build trailing section block ====
        clearing_account = self.env['account.move.line'].search(
            [('account_id', '=', journal.suspense_account_id.id),
             ('date', '<=', options['date']['date_to']),
             ('move_id.name', 'ilike', journal.code),
             ('parent_state', '!=', 'cancel')])
        clearing_debit = sum(clearing_account.mapped(lambda x: x.debit))
        clearing_credit = sum(clearing_account.mapped(lambda x: x.credit))
        total_clearance = clearing_debit - clearing_credit
        balance_of_book = balance_gl + abs(total_clearance)
        gl_account = {
            'id': 'current_2',
            'name': options['account_names'],
            'columns': [{'name': ''}, {'name': ''},
                        balance_cell]
        }
        clearing_line = {
            'id': 'current_1',
            'name': 'Bank Clearing Account',
            'columns': [{'name': ''}, {'name': ''},
                        {
                            'name': self.format_value(
                                total_clearance,
                                report_currency),
                            'no_format': total_clearance,
                        }]
        }
        difference_amnt = {
            'id': 'current_3',
            'name': 'Difference',
            'columns': [{'name': ''}, {'name': ''},
                        {
                            'name': self.format_value(
                                (balance_gl - balance_of_book),
                                report_currency),
                            'no_format': balance_gl - balance_of_book,
                        }],
            'level': 0,
            'unfolded': True,
            'unfoldable': False,
        }
        balance_of_book_dict = {
            'id': 'balance_gl_line1',
            'name': _("Balance as per our book"),
            'columns': [{'name': ''}, {'name': ''},
                        {
                            'name': self.format_value(
                                balance_of_book,
                                report_currency),
                            'no_format': balance_of_book,
                        }],
            'level': 0,
            'unfolded': True,
            'unfoldable': False,
        }
        section_st_report_lines.insert(1, balance_of_book_dict)
        section_st_report_lines.insert(2, gl_account)
        section_st_report_lines.insert(3, clearing_line)
        section_st_report_lines.insert(4, difference_amnt)
        return section_st_report_lines + section_pay_report_lines
