from odoo import api, fields, models
from odoo.addons.hr_payroll_expense.models.hr_payslip import HrPayslip


class HrPayslipMpatch(HrPayslip):

    @api.depends('expense_sheet_ids')
    def _compute_input_line_ids(self):
        expense_type = self.env.ref('hr_payroll_expense.expense_other_input',
                                    raise_if_not_found=False)
        overtime_type = self.env.ref('dev_hr_expense_portal.overtime_other_input',
                                    raise_if_not_found=False)
        perdiem_type = self.env.ref('dev_hr_expense_portal.perdiem_other_input',
                                    raise_if_not_found=False)
        for payslip in self:
            total_exp = 0
            total_ovt = 0
            total_ped = 0
            for exp in payslip.expense_sheet_ids.expense_line_ids.filtered(lambda x:x.product_id.product_expense_type == 'others'):
                if self.env.company.currency_id.id != payslip.currency_id.id:
                    tot = self.env.company.currency_id._convert(exp.total_amount_company,
                                                     payslip.currency_id,
                                                     self.env.company,
                                                    exp.date)
                    total_exp+= tot
                else:
                    total_exp+=exp.total_amount_company

            for ovt in payslip.expense_sheet_ids.expense_line_ids.filtered(lambda x:x.product_id.product_expense_type == 'overtime'):
                if self.env.company.currency_id.id != payslip.currency_id.id:
                    tot = self.env.company.currency_id._convert(ovt.total_amount_company,
                                                     payslip.currency_id,
                                                     self.env.company,
                                                    ovt.date)
                    total_ovt+= tot
                else:
                    total_ovt+=ovt.total_amount_company

            for ped in payslip.expense_sheet_ids.expense_line_ids.filtered(lambda x:x.product_id.product_expense_type == 'per_diem'):
                if self.env.company.currency_id.id != payslip.currency_id.id:
                    tot = self.env.company.currency_id._convert(ped.total_amount_company,
                                                     payslip.currency_id,
                                                     self.env.company,
                                                    ped.date)
                    total_ped+= tot
                else:
                    total_ped+=ped.total_amount_company

            if not total_exp and not total_ovt and not total_ped:
                payslip.input_line_ids = payslip.input_line_ids
                continue
            lines_to_keep = payslip.input_line_ids.filtered(
                lambda x: x.input_type_id not in [expense_type,overtime_type,perdiem_type])
            input_lines_vals = [(5, 0, 0)] + [(4, line.id, False) for line in
                                              lines_to_keep]
            input_lines_vals.append((0, 0, {
                'amount': total_exp,
                'input_type_id': expense_type.id
            }))
            input_lines_vals.append((0, 0, {
                'amount': total_ovt,
                'input_type_id': overtime_type.id
            }))
            input_lines_vals.append((0, 0, {
                'amount': total_ped,
                'input_type_id': perdiem_type.id
            }))
            payslip.update({'input_line_ids': input_lines_vals})
    HrPayslip._compute_input_line_ids = _compute_input_line_ids
