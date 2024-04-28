# # -*- coding: utf-8 -*-
from collections import defaultdict
from markupsafe import Markup
from odoo import models, _, fields
from odoo.exceptions import ValidationError
from odoo.tools import float_compare,plaintext2html
from odoo.tools.safe_eval import safe_eval
from odoo.tools import float_compare, float_is_zero
from odoo.addons.hr_payroll_account.models.hr_payroll_account import HrPayslip

class HrPayslipMpatch(HrPayslip):
    def _prepare_line_values(self, line, account_id, date, debit, credit,amt_currency):
        return {
            'name': line.name,
            'partner_id': line.partner_id.id,
            'account_id': account_id,
            'journal_id': line.slip_id.struct_id.journal_id.id,
            'date': date,
            'debit': debit,
            'credit': credit,
            'analytic_account_id': line.salary_rule_id.analytic_account_id.id or line.slip_id.contract_id.analytic_account_id.id,
            'currency_id': line.slip_id.currency_id.id if line.slip_id.currency_id.id != self.env.company.currency_id.id else self.env.company.currency_id.id ,
            'amount_currency':amt_currency,
        }

    HrPayslip._prepare_line_values = _prepare_line_values

    def _prepare_slip_lines(self, date, line_ids):
        self.ensure_one()
        precision = self.env['decimal.precision'].precision_get('Payroll')
        new_lines = []
        for line in self.line_ids.filtered(lambda line: line.category_id):
            if line.currency_id.id != self.env.company.currency_id.id:
                amt = line.currency_id._convert(line.total,
                                                self.env.company.currency_id,
                                                line.slip_id.company_id,
                                                self.compute_date)
                amount = -amt if self.credit_note else amt
                amt_cur = line.total
            else:
                amount = -line.total if self.credit_note else line.total
                amt_cur = -line.total
            # amount = -line.total if self.credit_note else line.total
            amt_currency = amt_cur
            if line.code == 'NET':  # Check if the line is the 'Net Salary'.

                for tmp_line in self.line_ids.filtered(
                        lambda line: line.category_id):
                    if tmp_line.salary_rule_id.not_computed_in_net:  # Check if the rule must be computed in the 'Net Salary' or not.
                        if line.currency_id.id != self.env.company.currency_id.id:
                            tmp_amt = tmp_line.currency_id._convert(tmp_line.total,
                                                            self.env.company.currency_id,
                                                            tmp_line.slip_id.company_id,
                                                            self.compute_date)
                        else:
                            tmp_amt = tmp_line.total

                        if amount > 0:
                            amount -= abs(tmp_amt)
                            amt_currency -=abs(tmp_line.total)

                        elif amount < 0:
                            amount += abs(tmp_amt)
                            amt_currency+= abs(tmp_line.total)
            if float_is_zero(amount, precision_digits=precision):
                continue
            debit_account_id = line.salary_rule_id.account_debit.id
            credit_account_id = line.salary_rule_id.account_credit.id

            if debit_account_id:  # If the rule has a debit account.
                debit = amount if amount > 0.0 else 0.0
                credit = -amount if amount < 0.0 else 0.0

                debit_line = self._get_existing_lines(
                    line_ids + new_lines, line, debit_account_id, debit, credit)

                if not debit_line:
                    debit_line = self._prepare_line_values(line,
                                                           debit_account_id,
                                                           date, debit, credit,amt_currency)
                    debit_line['tax_ids'] = [(4, tax_id) for tax_id in
                                             line.salary_rule_id.account_debit.tax_ids.ids]
                    new_lines.append(debit_line)
                else:
                    debit_line['debit'] += debit
                    debit_line['credit'] += credit
                    debit_line['amount_currency'] += amt_currency

            if credit_account_id:  # If the rule has a credit account.
                debit = -amount if amount < 0.0 else 0.0
                credit = amount if amount > 0.0 else 0.0
                credit_line = self._get_existing_lines(
                    line_ids + new_lines, line, credit_account_id, debit,
                    credit)

                if not credit_line:
                    credit_line = self._prepare_line_values(line,
                                                            credit_account_id,
                                                            date, debit, credit,amt_currency)
                    credit_line['tax_ids'] = [(4, tax_id) for tax_id in
                                              line.salary_rule_id.account_credit.tax_ids.ids]
                    new_lines.append(credit_line)
                else:
                    credit_line['debit'] += debit
                    credit_line['credit'] += credit
                    credit_line['amount_currency'] += amt_currency

        return new_lines

    HrPayslip._prepare_slip_lines = _prepare_slip_lines
class HrPayslip(models.Model):
    _name = "hr.payslip"
    _inherit = ['hr.payslip', 'portal.mixin']

    def _compute_access_url(self):
        super(HrPayslip, self)._compute_access_url()
        for payslip in self:
            payslip.access_url = '/my/payslip/%s' % (payslip.id)

    def _get_report_base_filename(self):
        self.ensure_one()
        return '%s' % (self.name)

    def action_create_journal_entry(self):
        struct_ids = self.mapped('struct_id')
        for struct in struct_ids:
            payslips = self.filtered(lambda x: x.struct_id.id == struct.id)
            invalid_payslips = payslips.filtered(lambda p: p.contract_id and (
                        p.contract_id.date_start > p.date_to or (
                            p.contract_id.date_end and p.contract_id.date_end < p.date_from)))
            if invalid_payslips:
                raise ValidationError(
                    _('The following employees have a contract outside of the payslip period:\n%s',
                      '\n'.join(invalid_payslips.mapped('employee_id.name'))))
            if any(slip.contract_id.state == 'cancel' for slip in payslips):
                raise ValidationError(
                    _('You cannot validate a payslip on which the contract is cancelled'))
            if any(slip.state == 'cancel' for slip in payslips):
                raise ValidationError(
                    _("You can't validate a cancelled payslip."))
            payslips.write({'state': 'done'})

            line_values = payslips._get_line_values(['NET'])

            payslips.filtered(
                lambda p: not p.credit_note and line_values['NET'][p.id][
                    'total'] < 0).write({'has_negative_net_to_report': True})
            payslips.mapped('payslip_run_id').action_close()
            # Validate work entries for regular payslips (exclude end of year bonus, ...)
            regular_payslips = self.filtered(
                lambda p: p.struct_id.type_id.default_struct_id == p.struct_id)
            work_entries = self.env['hr.work.entry']
            for regular_payslip in regular_payslips:
                work_entries |= self.env['hr.work.entry'].search([
                    ('date_start', '<=', regular_payslip.date_to),
                    ('date_stop', '>=', regular_payslip.date_from),
                    ('employee_id', '=', regular_payslip.employee_id.id),
                ])
            if work_entries:
                work_entries.action_validate()

            if self.env.context.get('payslip_generate_pdf'):
                if self.env.context.get('payslip_generate_pdf_direct'):
                    payslips._generate_pdf()
                else:
                    payslips.write({'queued_for_pdf': True})
                    payslip_cron = self.env.ref(
                        'hr_payroll.ir_cron_generate_payslip_pdfs',
                        raise_if_not_found=False)
                    if payslip_cron:
                        payslip_cron._trigger()

            precision = self.env['decimal.precision'].precision_get('Payroll')

            # Add payslip without run
            payslips_to_post = payslips.filtered(
                lambda slip: not slip.payslip_run_id)

            # Adding pay slips from a batch and deleting pay slips with a batch that is not ready for validation.
            payslip_runs = (payslips - payslips_to_post).payslip_run_id
            for run in payslip_runs:
                if run._are_payslips_ready():
                    payslips_to_post |= run.slip_ids

            # A payslip need to have a done state and not an accounting move.
            payslips_to_post = payslips_to_post.filtered(
                lambda slip: slip.state == 'done' and not slip.move_id)

            # Check that a journal exists on all the structures
            if any(not payslip.struct_id for payslip in payslips_to_post):
                raise ValidationError(
                    _('One of the contract for these payslips has no structure type.'))
            if any(not structure.journal_id for structure in
                   payslips_to_post.mapped('struct_id')):
                raise ValidationError(
                    _('One of the payroll structures has no account journal defined on it.'))

            # Map all payslips by structure journal and pay slips month.
            # Case 1: Batch all the payslips together -> {'journal_id': {'month': slips}}
            # Case 2: Generate account move separately -> [{'journal_id': {'month': slip}}]
            if payslips.company_id.batch_payroll_move_lines:
                all_slip_mapped_data = defaultdict(
                    lambda: defaultdict(lambda: self.env['hr.payslip']))
                for slip in payslips_to_post:
                    all_slip_mapped_data[slip.struct_id.journal_id.id][
                        slip.date or fields.Date().end_of(slip.date_to,
                                                          'month')] |= slip
                all_slip_mapped_data = [all_slip_mapped_data]
            else:
                all_slip_mapped_data = [{
                    slip.struct_id.journal_id.id: {
                        slip.date or fields.Date().end_of(slip.date_to,
                                                          'month'): slip
                    }
                } for slip in payslips_to_post]

            for slip_mapped_data in all_slip_mapped_data:
                for journal_id in slip_mapped_data:  # For each journal_id.
                    for slip_date in slip_mapped_data[
                        journal_id]:  # For each month.
                        line_ids = []
                        debit_sum = 0.0
                        credit_sum = 0.0
                        date = slip_date
                        move_dict = {
                            'narration': '',
                            'ref': fields.Date().end_of(
                                slip_mapped_data[journal_id][slip_date][
                                    0].date_to, 'month').strftime('%B %Y'),
                            'journal_id': journal_id,
                            'date': date,
                        }

                        for slip in slip_mapped_data[journal_id][slip_date]:
                            move_dict['narration'] += plaintext2html(
                                slip.number or '' + ' - ' + slip.employee_id.name or '')
                            move_dict['narration'] += Markup('<br/>')
                            slip_lines = slip._prepare_slip_lines(date,
                                                                  line_ids)
                            line_ids.extend(slip_lines)

                        for line_id in line_ids:  # Get the debit and credit sum.
                            debit_sum += line_id['debit']
                            credit_sum += line_id['credit']

                        # The code below is called if there is an error in the balance between credit and debit sum.
                        if float_compare(credit_sum, debit_sum,
                                         precision_digits=precision) == -1:
                            slip._prepare_adjust_line(line_ids, 'credit',
                                                      debit_sum, credit_sum,
                                                      date)
                        elif float_compare(debit_sum, credit_sum,
                                           precision_digits=precision) == -1:
                            slip._prepare_adjust_line(line_ids, 'debit',
                                                      debit_sum, credit_sum,
                                                      date)

                        # Add accounting lines in the move
                        move_dict['line_ids'] = [(0, 0, line_vals) for line_vals
                                                 in line_ids]
                        move = payslips._create_account_move(move_dict)
                        for slip in slip_mapped_data[journal_id][slip_date]:
                            slip.write({'move_id': move.id, 'date': date})
            payslips.expense_sheet_ids.action_create_journal_entry()

