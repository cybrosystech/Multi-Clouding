# # -*- coding: utf-8 -*-
import base64
from odoo import models, _, fields
from odoo.exceptions import ValidationError
from odoo.tools.safe_eval import safe_eval
from odoo.tools import float_compare, float_is_zero


class HrPayslip(models.Model):
    _inherit = "hr.payslip"

    def action_print_payslip(self):
        return {
            'name': 'Payslip',
            'type': 'ir.actions.act_url',
            'url': '/report/pdf/hr_payroll.report_payslip_lang/%(payslip_id)s' % {
                'payslip_id': self.id}
        }

    def action_create_journal_entry(self):
        struct_ids = self.mapped('struct_id')
        for struct in struct_ids:
            move_dict = {
                'narration': '',
                'date': fields.datetime.now().date(),
                'journal_id': struct.journal_id.id,
            }
            payslips = self.env['hr.payslip'].search(
                [('id', 'in', self.ids), ('struct_id', '=', struct.id),
                 ('state', '=', 'verify')])
            for rec in payslips:
                if any(slip.state == 'cancel' for slip in rec):
                    raise ValidationError(
                        _("You can't validate a cancelled payslip."))
                rec.write({'state': 'done'})
                rec.mapped('payslip_run_id').action_close()
                regular_payslips = rec.filtered(lambda
                                                    p: p.struct_id.type_id.default_struct_id == p.struct_id)
                for regular_payslip in regular_payslips:
                    work_entries = self.env['hr.work.entry'].search([
                        ('date_start', '<=', regular_payslip.date_to),
                        ('date_stop', '>=', regular_payslip.date_from),
                        ('employee_id', '=', regular_payslip.employee_id.id),
                    ])
                    work_entries.action_validate()
                if self.env.context.get('payslip_generate_pdf'):
                    for payslip in rec:
                        if not payslip.struct_id or not payslip.struct_id.report_id:
                            report = self.env.ref(
                                'hr_payroll.action_report_payslip', False)
                        else:
                            report = payslip.struct_id.report_id
                        pdf_content, content_type = report.sudo()._render_qweb_pdf(
                            payslip.id)
                        if payslip.struct_id.report_id.print_report_name:
                            pdf_name = safe_eval(
                                payslip.struct_id.report_id.print_report_name,
                                {'object': payslip})
                        else:
                            pdf_name = _("Payslip")
                        # Sudo to allow payroll managers to create document.document without access to the
                        # application
                        attachment = self.env['ir.attachment'].sudo().create({
                            'name': pdf_name,
                            'type': 'binary',
                            'datas': base64.encodebytes(pdf_content),
                            'res_model': payslip._name,
                            'res_id': payslip.id
                        })
                        # Send email to employees
                        subject = '%s, a new payslip is available for you' % (
                            payslip.employee_id.name)
                        template = self.env.ref(
                            'hr_payroll.mail_template_new_payslip',
                            raise_if_not_found=False)
                        if template:
                            email_values = {
                                'attachment_ids': attachment,
                            }
                            template.send_mail(
                                payslip.id,
                                email_values=email_values,
                                notif_layout='mail.mail_notification_light')
                precision = self.env['decimal.precision'].precision_get(
                    'Payroll')
                payslips_to_post = self.filtered(
                    lambda slip: not slip.payslip_run_id)
                payslip_runs = (self - payslips_to_post).mapped(
                    'payslip_run_id')
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
                # {'journal_id': {'month': [slip_ids]}}
                slip_mapped_data = {slip.struct_id.journal_id.id: {
                    slip.date or fields.Date().end_of(slip.date_to, 'month'):
                        self.env['hr.payslip']} for slip in payslips_to_post}
                for slip in payslips_to_post:
                    slip_mapped_data[slip.struct_id.journal_id.id][
                        slip.date or fields.Date().end_of(slip.date_to,
                                                          'month')] |= slip

                for journal_id in slip_mapped_data:  # For each journal_id.
                    for slip_date in slip_mapped_data[
                        journal_id]:  # For each month.
                        line_ids = []
                        debit_sum = 0.0
                        credit_sum = 0.0
                        date = slip_date
                        for slip in slip_mapped_data[journal_id][slip_date]:
                            move_dict[
                                'narration'] += slip.number or '' + ' - ' + slip.employee_id.name or ''
                            move_dict['narration'] += '\n'
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
                                                      debit_sum,
                                                      credit_sum, date)
                        elif float_compare(debit_sum, credit_sum,
                                           precision_digits=precision) == -1:
                            slip._prepare_adjust_line(line_ids, 'debit',
                                                      debit_sum,
                                                      credit_sum, date)
                        move_dict['line_ids'] = [(0, 0, line_vals) for line_vals
                                                 in
                                                 line_ids]
            move = self._create_account_move(move_dict)
            for payslip in payslips:
                payslip.move_id = move.id
