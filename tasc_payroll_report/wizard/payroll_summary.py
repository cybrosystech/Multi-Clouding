import base64
import datetime
import io
import xlsxwriter
from odoo import fields, models, _, api
from odoo.exceptions import UserError


class PayrollSummary(models.Model):
    _name = 'payroll.summary'
    _description = 'Payroll Summary'

    month = fields.Selection(string="Month", selection=[('1', 'January'),
                                                        ('2', 'February'),
                                                        ('3', 'March'),
                                                        ('4', 'April'),
                                                        ('5', 'May'),
                                                        ('6', 'June'),
                                                        ('7', 'July'),
                                                        ('8', 'August'),
                                                        ('9', 'September'),
                                                        ('10', 'October'),
                                                        ('11', 'November'),
                                                        ('12', 'December'),
                                                        ], required=True)
    year = fields.Char(string="Year", required=True)
    struct_id = fields.Many2one('hr.payroll.structure',
                                'Payslip Structure',
                                required=True)
    excel_sheet = fields.Binary('Download Report')
    excel_sheet_name = fields.Char(string='Name', size=64)

    @api.constrains('year')
    def on_save_year(self):
        if len(self.year) > 4:
            raise UserError('Invalid year!!!')

    def print_report_xlsx(self):
        report_data = self.get_report_data()
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
        date_format = workbook.add_format({
            'border': 0,
            'align': 'center',
            'valign': 'vcenter',
            'num_format': 'dd/mm/yyyy'})
        STYLE_LINE_Data.num_format_str = '#,##0.00_);(#,##0.00)'

        if report_data:
            self.add_xlsx_sheet(report_data, workbook, STYLE_LINE_Data,
                                STYLE_LINE_Data_emp_name,
                                header_format, STYLE_LINE_HEADER, date_format)

        self.excel_sheet_name = 'Payment Summary Report'
        workbook.close()
        output.seek(0)
        self.excel_sheet = base64.b64encode(output.read())
        self.excel_sheet_name = str(self.excel_sheet_name) + '.xlsx'
        return {
            'type': 'ir.actions.act_url',
            'name': 'Payment Summary',
            'url': '/web/content/%s/%s/excel_sheet/%s?download=true' % (
                self._name, self.id, self.excel_sheet_name),
            'target': 'new'
        }

    def get_report_data(self):
        if self.month and self.year:
            struct_ids = self.env['hr.payslip'].search(
                [('state', '!=', 'cancel'), ('date_from', '!=', False),
                 ('struct_id', '=', self.struct_id.id),
                 ('company_id', '=', self.env.company.id)]).filtered(
                lambda l: l.date_from.month == int(
                    self.month) and l.date_from.year == int(self.year)).mapped(
                'struct_id')
            payslip_structure = {}
            for struct in struct_ids:
                data = []
                payslip_structure.update({struct.id: data})
        return payslip_structure

    def add_xlsx_sheet(self, report_data, workbook, STYLE_LINE_Data,
                       STYLE_LINE_Data_emp_name,
                       header_format, STYLE_LINE_HEADER, date_format):
        self.ensure_one()
        worksheet = workbook.add_worksheet(_('Payment Summary Report'))
        lang = self.env.user.lang
        if lang.startswith('ar_'):
            worksheet.right_to_left()
        struct_ids = list(report_data.keys())
        stru = self.env['hr.payroll.structure'].browse(struct_ids[0])
        length = len(stru.rule_ids.ids)
        row = 0
        col = 0
        datetime_object = datetime.datetime.strptime(self.month, "%m")

        full_month_name = datetime_object.strftime("%B")
        heading = 'Payment Summary Report' + ' - ' + full_month_name + ' - ' + self.year
        worksheet.merge_range(row, row, col, col + 7 + length,
                              _(heading),
                              STYLE_LINE_HEADER)
        for s in struct_ids:
            struct = self.env['hr.payroll.structure'].browse(s)
            row += 1
            col = 0
            worksheet.write(row, col, _('Employee Registration Number'),
                            header_format)
            col += 1
            worksheet.write(row, col, _('Employee Name'), header_format)
            col += 1
            worksheet.write(row, col, _('Designation'), header_format)
            col += 1
            worksheet.write(row, col, _('Department'), header_format)
            col += 1
            worksheet.write(row, col, _('Date of Joining'), header_format)
            col += 1
            worksheet.write(row, col, _('Currency'), header_format)
            col += 1
            worksheet.write(row, col, _('Working Days'), header_format)
            col += 1
            payslip_lines = self.env['hr.payslip'].search(
                [('state', '!=', 'cancel'), ('struct_id', '=', struct.id),
                 ('date_from', '!=', False)]).filtered(
                lambda l: l.date_from.month == int(
                    self.month) and l.date_from.year == int(self.year))
            # datas = self.prepare_datas(payslip_lines, s)
            row += 1
            if payslip_lines:
                for p in payslip_lines:
                    precision = p.currency_id.decimal_places
                    string_val = "0" * precision
                    float_str = '#,##0.' + string_val
                    floating_point_bordered = workbook.add_format(
                        {'num_format': float_str})

                    working_days = p.worked_days_line_ids.mapped(
                        'number_of_days')
                    col = 0
                    if p.employee_id.registration_number:
                        worksheet.write(row, col,
                                        p.employee_id.registration_number,
                                        STYLE_LINE_Data)
                    else:
                        worksheet.write(row, col, '',
                                        STYLE_LINE_Data)
                    col += 1
                    if p.employee_id.name:
                        worksheet.write(row, col, p.employee_id.name,
                                        STYLE_LINE_Data_emp_name)
                    else:
                        worksheet.write(row, col, '',
                                        STYLE_LINE_Data)
                    col += 1
                    if p.employee_id.job_id.name:
                        worksheet.write(row, col, p.employee_id.job_id.name,
                                        STYLE_LINE_Data)
                    else:
                        worksheet.write(row, col, '',
                                        STYLE_LINE_Data)
                    col += 1
                    if p.employee_id.department_id.name:
                        worksheet.write(row, col,
                                        p.employee_id.department_id.name,
                                        STYLE_LINE_Data)
                    else:
                        worksheet.write(row, col, '',
                                        STYLE_LINE_Data)
                    col += 1
                    if p.employee_id.date_of_joining:
                        worksheet.write(row, col, p.employee_id.date_of_joining,
                                        date_format)
                    else:
                        worksheet.write(row, col, '',
                                        date_format)

                    col += 1
                    if p.currency_id.name:

                        worksheet.write(row, col,
                                        p.currency_id.name,
                                        STYLE_LINE_Data)
                    else:
                        worksheet.write(row, col,
                                        '',
                                        STYLE_LINE_Data)
                    col += 1
                    if working_days:
                        worksheet.write(row, col,
                                        sum(working_days),
                                        STYLE_LINE_Data)
                    else:
                        worksheet.write(row, col,
                                        0,
                                        STYLE_LINE_Data)
                    row += 1

            row = 1
            rules = struct.rule_ids.ids
            for line in struct.rule_ids:
                col += 1
                worksheet.write(row, col, _(line.name), header_format)

            data = self.prepare_data(payslip_lines, struct)
            if payslip_lines:
                c = 6
                r = 2
                for i in range(0, len(data)):
                    for val in data[i].values():
                        c += 1

                        worksheet.write(r, c, val, floating_point_bordered)
                    c = 6
                    r += 1

    def prepare_data(self, payslip_lines, struct_id):
        data = []
        i = 0
        for slip in payslip_lines:
            rules = struct_id.rule_ids.ids
            out = dict.fromkeys(rules, 0)
            data.append(out)
            for line in slip.line_ids:
                data[i][line.salary_rule_id.id] = line.total
            i += 1
        return data
