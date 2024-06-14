from odoo import api, Command, models


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def write(self, vals):
        res = super().write(vals)
        if 'expense_sheet_ids' in vals:
            self._compute_expense_input_line_ids()
        if 'input_line_ids' in vals:
            self._update_expense_sheets()
        return res

    def _compute_expense_input_line_ids(self):
        expense_type = self.env['hr.payslip.input.type'].search(
            [('code', '=', 'EXPENSES'),
             ('country_id', '=', self.env.company.country_id.id)], limit=1)
        overtime_type = self.env['hr.payslip.input.type'].search(
            [('code', '=', 'OVT'),
             ('country_id', '=', self.env.company.country_id.id)], limit=1)
        perdiem_type = self.env['hr.payslip.input.type'].search(
            [('code', '=', 'PED'),
             ('country_id', '=', self.env.company.country_id.id)], limit=1)
        for payslip in self:
            total_exp = 0
            total_ovt = 0
            total_ped = 0
            for exp in payslip.expense_sheet_ids.expense_line_ids.filtered(
                    lambda x: x.product_id.product_expense_type == 'others'):
                if self.env.company.currency_id.id != payslip.currency_id.id:
                    tot = self.env.company.currency_id._convert(
                        exp.total_amount,
                        payslip.currency_id,
                        self.env.company,
                        exp.date)
                    total_exp += tot
                else:
                    total_exp += exp.total_amount

            for ovt in payslip.expense_sheet_ids.expense_line_ids.filtered(
                    lambda x: x.product_id.product_expense_type == 'overtime'):
                if self.env.company.currency_id.id != payslip.currency_id.id:
                    tot = self.env.company.currency_id._convert(
                        ovt.total_amount,
                        payslip.currency_id,
                        self.env.company,
                        ovt.date)
                    total_ovt += tot
                else:
                    total_ovt += ovt.total_amount

            for ped in payslip.expense_sheet_ids.expense_line_ids.filtered(
                    lambda x: x.product_id.product_expense_type == 'per_diem'):
                if self.env.company.currency_id.id != payslip.currency_id.id:
                    tot = self.env.company.currency_id._convert(
                        ped.total_amount,
                        payslip.currency_id,
                        self.env.company,
                        ped.date)
                    total_ped += tot
                else:
                    total_ped += ped.total_amount

            # total = sum(payslip.expense_sheet_ids.mapped('total_amount'))
            if not total_exp and not total_ovt and not total_ped:
                continue
            lines_to_remove = payslip.input_line_ids.filtered(
                lambda x: x.input_type_id.id in [expense_type.id,overtime_type.id,perdiem_type.id])
            input_lines_vals = [Command.delete(line.id) for line in
                                lines_to_remove]
            if expense_type:
                input_lines_vals.append(Command.create({
                    'amount': total_exp,
                    'input_type_id': expense_type.id
                }))
            if overtime_type:
                input_lines_vals.append(Command.create({
                    'amount': total_ovt,
                    'input_type_id': overtime_type.id
                }))
            if perdiem_type:
                input_lines_vals.append(Command.create({
                    'amount': total_ped,
                    'input_type_id': perdiem_type.id
                }))
            payslip.update({'input_line_ids': input_lines_vals})
