from odoo import api, fields, models
from odoo.addons.hr_payroll_expense.models.hr_payslip import HrPayslip


class HrPayslipMpatch(HrPayslip):

    @api.depends('expense_sheet_ids')
    def _compute_input_line_ids(self):
        expense_type = self.env.ref('hr_payroll_expense.expense_other_input',
                                    raise_if_not_found=False)
        for payslip in self:
            total = 0
            for sheet in payslip.expense_sheet_ids:
                    for exp in sheet.expense_line_ids:
                        if exp.currency_id.id != payslip.currency_id.id:
                            tot= sheet.currency_id._convert(exp.total_amount,
                                                             payslip.currency_id,
                                                             payslip.company_id,
                                                            exp.date)
                            total+= tot
                        else:
                            total+=exp.total_amount

            if not total or not expense_type:
                payslip.input_line_ids = payslip.input_line_ids
                continue
            lines_to_keep = payslip.input_line_ids.filtered(
                lambda x: x.input_type_id != expense_type)
            input_lines_vals = [(5, 0, 0)] + [(4, line.id, False) for line in
                                              lines_to_keep]
            input_lines_vals.append((0, 0, {
                'amount': total,
                'input_type_id': expense_type.id
            }))
            payslip.update({'input_line_ids': input_lines_vals})
    HrPayslip._compute_input_line_ids = _compute_input_line_ids
