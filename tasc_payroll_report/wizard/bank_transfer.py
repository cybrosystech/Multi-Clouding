import base64
import datetime
import io
import xlsxwriter
from odoo import fields, models, _, api
from odoo.exceptions import UserError


class PayrollSummary(models.Model):
    _name = 'bank.transfer'
    _description = 'Bank Transfer'

    date = fields.Date(string="Date")
    struct_id = fields.Many2one('hr.payroll.structure',
                                'Payslip Structure',
                                required=True)
    bank_account = fields.Char(string="Bank Account")
    excel_sheet = fields.Binary('Download Report')
    excel_sheet_name = fields.Char(string='Name', size=64)
    template = fields.Selection(string="Template",
                                selection=[('general', 'General'),
                                           ('Jordan', 'Jordan')])

    def print_report_xlsx(self):
        report_data = self.get_report_data()
        print("report_data", report_data)
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})

        TABLE_HEADER = workbook.add_format({
            'bold': 1,
            'font_name': 'Tahoma',
            'border': 0,
            'font_size': 12,
            'align': 'center',
            'valign': 'vcenter',
            'font_color': 'black',
        })

        header_format = workbook.add_format({
            'bold': 1,
            'font_name': 'Aharoni',
            'border': 0,
            'font_size': 13,
            'align': 'center',
            'valign': 'vcenter',
            'font_color': 'black',
            'bg_color': '#c3c6c5',
        })

        TABLE_HEADER_Data = TABLE_HEADER
        TABLE_HEADER_Data.num_format_str = '#,##0.00_);(#,##0.00)'
        STYLE_LINE = workbook.add_format({
            'border': 0,
            'align': 'center',
            'valign': 'vcenter',
        })

        STYLE_LINE_EMP_NAME = workbook.add_format({
            'border': 0,
            'align': 'left',
            'valign': 'vcenter',
        })
        STYLE_LINE_HEADER = workbook.add_format({
            'bold': 1,
            'font_name': 'Aharoni',
            'font_size': 14,
            'border': 0,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#7f8eb8',
        })

        TABLE_data = workbook.add_format({
            'bold': 1,
            'font_name': 'Aharoni',
            'border': 0,
            'font_size': 12,
            'align': 'center',
            'valign': 'vcenter',
            'font_color': 'black',
        })
        TABLE_data.num_format_str = '#,##0.00'
        TABLE_data_tolal_line = workbook.add_format({
            'bold': 1,
            'font_name': 'Aharoni',
            'border': 1,
            'font_size': 12,
            'align': 'center',
            'valign': 'vcenter',
            'font_color': 'black',
            'bg_color': 'yellow',
        })

        TABLE_data_tolal_line.num_format_str = '#,##0.00'
        STYLE_LINE_Data = STYLE_LINE
        STYLE_LINE_Data_emp_name = STYLE_LINE_EMP_NAME

        STYLE_LINE_Data.num_format_str = '#,##0.00_);(#,##0.00)'

        if report_data:
            self.add_xlsx_sheet(report_data, workbook, STYLE_LINE_Data,
                                STYLE_LINE_Data_emp_name,
                                header_format, STYLE_LINE_HEADER)

        self.excel_sheet_name = 'Bank Transfer Report'
        workbook.close()
        output.seek(0)
        self.excel_sheet = base64.b64encode(output.read())
        self.excel_sheet_name = str(self.excel_sheet_name) + '.xlsx'
        return {
            'type': 'ir.actions.act_url',
            'name': 'Payment Summary',
            'url': '/web/content/%s/%s/excel_sheet/%s?download=true' % (
                self._name, self.id, self.excel_sheet_name),
            'target': 'self'
        }

    def get_report_data(self):
        print("get_report_data")
        print("month", self.date.month, type(self.date.month))
        if self.date:
            struct_ids = self.env['hr.payslip'].search(
                [('state', '!=', 'cancel'), ('date_from', '!=', False),
                 ('struct_id', '=', self.struct_id.id),
                 ('company_id', '=', self.env.company.id)]).filtered(
                lambda l: l.date_from.month == int(
                    self.date.month) and l.date_from.year == int(
                    self.date.year)).mapped(
                'struct_id')
        else:
            struct_ids = self.env['hr.payslip'].search([])
        return struct_ids

    def add_xlsx_sheet(self, report_data, workbook, STYLE_LINE_Data,
                       STYLE_LINE_Data_emp_name,
                       header_format, STYLE_LINE_HEADER):
        print("add_xlsx_sheet")
        self.ensure_one()
        worksheet = workbook.add_worksheet(_('Bank Transfer Report'))
        lang = self.env.user.lang
        if lang.startswith('ar_'):
            worksheet.right_to_left()
        struct_ids = report_data
        row = 0
        col = 0
        full_month_name = self.date.strftime("%B")
        heading = 'Bank Transfer Report' + " - " + full_month_name + " " + str(self.date.year)

        if self.template == 'general':
            worksheet.merge_range(row, row, col, col + 9,
                                  _(heading),
                                  STYLE_LINE_HEADER)
            for struct in struct_ids:
                row += 1
                col = 0
                worksheet.write(row, col, _('Employee Number'),
                                header_format)
                col += 1
                worksheet.write(row, col, _('Account Number'), header_format)
                col += 1
                worksheet.write(row, col, _('Employee IBAN'), header_format)
                col += 1
                worksheet.write(row, col, _('Employee Name'), header_format)
                col += 1
                worksheet.write(row, col, _('Swift Code'), header_format)
                col += 1
                worksheet.write(row, col, _('   '), header_format)
                col += 1
                worksheet.write(row, col, _('Payroll Date'), header_format)
                col += 1
                worksheet.write(row, col, _('Currency'), header_format)
                col += 1
                worksheet.write(row, col, _('Amount'), header_format)
                col += 1
                worksheet.write(row, col, _('Month'), header_format)
                col += 1

                payslip_lines = self.env['hr.payslip'].search(
                    [('state', '!=', 'cancel'), ('struct_id', '=', struct.id),
                     ('date_from', '!=', False)]).filtered(
                    lambda l: l.date_from.month == int(
                        self.date.month) and l.date_from.year == int(
                        self.date.year))
                print("payslip_lines", payslip_lines)
                row += 1
                if payslip_lines:
                    for p in payslip_lines:
                        precision = p.currency_id.decimal_places
                        print("prec", precision)
                        string_val = "0" * precision
                        float_str = '#,##0.' + string_val
                        print("float_str", float_str)
                        floating_point_bordered = workbook.add_format(
                            {'num_format': float_str})
                        col = 0
                        if p.employee_id.registration_number:
                            worksheet.write(row, col,
                                            p.employee_id.registration_number,
                                            STYLE_LINE_Data)
                        else:
                            worksheet.write(row, col, '',
                                            STYLE_LINE_Data)
                        col += 1
                        if self.bank_account:
                            worksheet.write(row, col, self.bank_account,
                                            STYLE_LINE_Data)
                        else:
                            worksheet.write(row, col, '',
                                            STYLE_LINE_Data)
                        col += 1
                        if p.employee_id.bank_account_id.bank_iban:
                            worksheet.write(row, col,
                                            p.employee_id.bank_account_id.bank_iban,
                                            STYLE_LINE_Data_emp_name)
                        else:
                            worksheet.write(row, col, '',
                                            STYLE_LINE_Data_emp_name)
                        col += 1
                        if p.employee_id.bank_account_id.acc_holder_name:
                            worksheet.write(row, col,
                                            p.employee_id.bank_account_id.acc_holder_name,
                                            STYLE_LINE_Data_emp_name)
                        elif p.employee_id.name:
                            worksheet.write(row, col,
                                            p.employee_id.name,
                                            STYLE_LINE_Data_emp_name)
                        else:
                            worksheet.write(row, col, '',
                                            STYLE_LINE_Data_emp_name)

                        col += 1
                        if p.employee_id.bank_account_id.bank_bic:

                            worksheet.write(row, col,
                                            p.employee_id.bank_account_id.bank_bic,
                                            STYLE_LINE_Data)
                        else:
                            worksheet.write(row, col,
                                            '',
                                            STYLE_LINE_Data)
                        col += 1
                        worksheet.write(row, col,
                                        13,
                                        STYLE_LINE_Data)
                        col += 1
                        if self.date:
                            date_format = workbook.add_format(
                                {'num_format': 'yyyy-mm-dd'})

                            worksheet.write(row, col,
                                            self.date,
                                            date_format)
                        else:
                            worksheet.write(row, col,
                                            '',
                                            STYLE_LINE_Data)
                        col += 1
                        if p.currency_id:

                            worksheet.write(row, col,
                                            p.currency_id.name,
                                            STYLE_LINE_Data)
                        else:
                            worksheet.write(row, col,
                                            '',
                                            STYLE_LINE_Data)
                        col += 1
                        if p.net_wage:

                            worksheet.write(row, col,
                                            p.net_wage,
                                            floating_point_bordered)
                        else:
                            worksheet.write(row, col, '', STYLE_LINE_Data)
                        col += 1
                        if self.date:
                            full_month_name = self.date.strftime("%B")

                            worksheet.write(row, col,
                                            'Salary ' + full_month_name,
                                            STYLE_LINE_Data)
                        else:
                            worksheet.write(row, col, '', STYLE_LINE_Data)
                        col += 1
                        row += 1
                else:
                    raise UserError(
                        _("No Payslips are found!!!"))
        elif self.template == 'Jordan':
            worksheet.merge_range(row, row, col, col + 12,
                                  _(heading),
                                  STYLE_LINE_HEADER)
            for struct in struct_ids:
                row += 1
                col = 0
                worksheet.write(row, col, _('Employee Number'),
                                header_format)
                col += 1
                worksheet.write(row, col,
                                _('BT/LBT Arab bank/Other local banks'),
                                header_format)
                col += 1
                worksheet.write(row, col, _('Account Number'), header_format)
                col += 1
                worksheet.write(row, col, _('Employee IBAN'), header_format)
                col += 1
                worksheet.write(row, col, _('Employee Name'), header_format)
                col += 1
                worksheet.write(row, col, _('Swift Code'), header_format)
                col += 1
                worksheet.write(row, col, _('   '), header_format)
                col += 1
                worksheet.write(row, col, _('Payroll Date'), header_format)
                col += 1
                worksheet.write(row, col, _('Currency'), header_format)
                col += 1
                worksheet.write(row, col, _('Amount'), header_format)
                col += 1
                worksheet.write(row, col, _(' '), header_format)
                col += 1
                worksheet.write(row, col, _('Month'), header_format)
                col += 1
                payslip_lines = self.env['hr.payslip'].search(
                    [('state', '!=', 'cancel'), ('struct_id', '=', struct.id),
                     ('date_from', '!=', False)]).filtered(
                    lambda l: l.date_from.month == int(
                        self.date.month) and l.date_from.year == int(
                        self.date.year))
                print("payslip_lines", payslip_lines)

                row += 1
                if payslip_lines:
                    for p in payslip_lines:
                        precision = p.currency_id.decimal_places
                        print("prec", precision)
                        string_val = "0" * precision
                        float_str = '#,##0.' + string_val
                        print("float_str", float_str)
                        floating_point_bordered = workbook.add_format(
                            {'num_format': float_str})
                        # working_days = p.worked_days_line_ids.mapped(
                        #     'number_of_days')
                        if p.employee_id.bank_account_id.bank_bic:
                            arbjo = p.employee_id.bank_account_id.bank_bic.startswith(
                                "ARABJO")
                        else:
                            arbjo = False
                        bt = ''
                        if arbjo:
                            bt = 'BT'
                        else:
                            bt = 'LBT'

                        col = 0
                        if p.employee_id.registration_number:
                            worksheet.write(row, col,
                                            p.employee_id.registration_number,
                                            STYLE_LINE_Data)
                        else:
                            worksheet.write(row, col, '',
                                            STYLE_LINE_Data)
                        col += 1
                        if bt:
                            worksheet.write(row, col,
                                            bt,
                                            STYLE_LINE_Data)
                        else:
                            worksheet.write(row, col, '',
                                            STYLE_LINE_Data)
                        col += 1
                        if self.bank_account:
                            worksheet.write(row, col, self.bank_account,
                                            STYLE_LINE_Data)
                        else:
                            worksheet.write(row, col, '',
                                            STYLE_LINE_Data)
                        col += 1
                        if p.employee_id.bank_account_id.bank_iban:
                            worksheet.write(row, col,
                                            p.employee_id.bank_account_id.bank_iban,
                                            STYLE_LINE_Data_emp_name)
                        else:
                            worksheet.write(row, col, '',
                                            STYLE_LINE_Data_emp_name)
                        col += 1
                        if p.employee_id.bank_account_id.acc_holder_name:
                            worksheet.write(row, col,
                                            p.employee_id.bank_account_id.acc_holder_name,
                                            STYLE_LINE_Data_emp_name)
                        elif p.employee_id.name:
                            worksheet.write(row, col,
                                            p.employee_id.name,
                                            STYLE_LINE_Data_emp_name)
                        else:
                            worksheet.write(row, col, '',
                                            STYLE_LINE_Data_emp_name)
                        col += 1
                        if p.employee_id.bank_account_id.bank_bic:
                            worksheet.write(row, col,
                                            p.employee_id.bank_account_id.bank_bic,
                                            STYLE_LINE_Data)
                        else:
                            worksheet.write(row, col,
                                            '',
                                            STYLE_LINE_Data)
                        col += 1
                        worksheet.write(row, col,
                                        13,
                                        STYLE_LINE_Data)
                        col += 1
                        if self.date:
                            date_format = workbook.add_format(
                                {'num_format': 'yyyy-mm-dd'})
                            worksheet.write(row, col,
                                            self.date,
                                            date_format)
                        else:
                            worksheet.write(row, col,
                                            '',
                                            STYLE_LINE_Data)
                        col += 1
                        if p.currency_id:

                            worksheet.write(row, col,
                                            p.currency_id.name,
                                            STYLE_LINE_Data)
                        else:
                            worksheet.write(row, col,
                                            '',
                                            STYLE_LINE_Data)
                        col += 1
                        if p.net_wage:

                            worksheet.write(row, col,
                                            p.net_wage,
                                            floating_point_bordered)
                        else:
                            worksheet.write(row, col, '', STYLE_LINE_Data)
                        col += 1
                        if bt:
                            if bt == 'BT':
                                worksheet.write(row, col,
                                                'ACH',
                                                STYLE_LINE_Data)
                            else:
                                worksheet.write(row, col,
                                                '',
                                                STYLE_LINE_Data)
                        else:
                            worksheet.write(row, col, '', STYLE_LINE_Data)
                        col += 1
                        if self.date:
                            full_month_name = self.date.strftime("%B")

                            worksheet.write(row, col,
                                            'Salary ' + full_month_name,
                                            STYLE_LINE_Data)
                        else:
                            worksheet.write(row, col, '', STYLE_LINE_Data)
                        col += 1
                        row += 1
                else:
                    raise UserError(
                        _("No Payslips are found!!!"))
        else:
            raise UserError(_("Please select a template."))
