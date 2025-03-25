import base64
import io
import datetime
import xlsxwriter
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class LeaseDetailsReportWizard(models.TransientModel):
    """ Class for Lease Details Report Xlsx"""
    _name = "lease.details.report.wizard"
    _description = "Lease Details Report"

    start_date = fields.Date(string="Commencement Start Date",
                             default=datetime.datetime.now())
    end_date = fields.Date(string="Commencement End Date",
                           default=datetime.datetime.now())
    state = fields.Selection(string="Lease Status",
                             selection=[('draft', 'Draft'),
                                        ('active', 'Active'),
                                        ('extended', 'Extended'),
                                        ('expired', 'Expired'),
                                        ('terminated', 'Terminated')])
    excel_sheet = fields.Binary('Download Report')
    excel_sheet_name = fields.Char(string='Name', size=64)

    @api.constrains('end_date')
    def onsave_end_date(self):
        if self.end_date < self.start_date:
            raise UserError(
                "The end date should be greater than or equal to start date.")

    def print_report_xlsx(self):
        """ Method for print Lease Details xlsx report"""
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
            'align': 'left',
            'valign': 'vcenter',
            'font_color': 'black',
            'bg_color': '#c3c6c5',
        })

        TABLE_HEADER_Data = TABLE_HEADER
        TABLE_HEADER_Data.num_format_str = '#,##0.00_);(#,##0.00)'
        STYLE_LINE = workbook.add_format({
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
        date_format = workbook.add_format({
            'border': 0,
            'align': 'left',
            'valign': 'vcenter',
            'num_format': 'dd/mm/yyyy'})

        TABLE_data_tolal_line.num_format_str = '#,##0.00'
        STYLE_LINE_Data = STYLE_LINE
        STYLE_LINE_Data.num_format_str = '#,##0.00_);(#,##0.00)'

        if report_data:
            self.add_xlsx_sheet(report_data, workbook, STYLE_LINE_Data,
                                header_format, STYLE_LINE_HEADER, date_format)

        self.excel_sheet_name = 'Tasc Lease Details Report'
        workbook.close()
        output.seek(0)
        self.excel_sheet = base64.b64encode(output.read())
        self.excel_sheet_name = str(self.excel_sheet_name) + '.xlsx'
        return {
            'type': 'ir.actions.act_url',
            'name': 'Tasc Bill Payment Report',
            'url': '/web/content/%s/%s/excel_sheet/%s?download=true' % (
                self._name, self.id, self.excel_sheet_name),
            'target': 'new'
        }

    def get_report_data(self):
        """Method to compute Tasc Bill Payment Report."""
        if self.state and self.start_date and self.end_date:
            lease_ids = self.env['leasee.contract'].search(
                [('parent_id', '=', False),
                 ('state', '=', self.state),
                 ('commencement_date', '>=', self.start_date),
                 ('commencement_date', '<=', self.end_date)],
                order="name DESC")
        elif self.state and self.start_date:
            lease_ids = self.env['leasee.contract'].search(
                [('parent_id', '=', False),
                 ('state', '=', self.state),
                 ('commencement_date', '>=', self.start_date),
                 ], order="name DESC")
        elif self.state and self.end_date:
            lease_ids = self.env['leasee.contract'].search(
                [('parent_id', '=', False),
                 ('state', '=', self.state),
                 ('commencement_date', '<=', self.end_date)], order="name DESC")
        elif self.end_date and self.start_date:
            lease_ids = self.env['leasee.contract'].search(
                [('parent_id', '=', False),
                 ('commencement_date', '>=', self.start_date),
                 ('commencement_date', '<=', self.end_date)], order="name DESC")
        elif self.state:
            lease_ids = self.env['leasee.contract'].search(
                [('parent_id', '=', False),
                 ('state', '=', self.state),
                 ], order="name DESC")
        else:
            lease_ids = self.env['leasee.contract'].search(
                [('parent_id', '=', False)], order="name DESC")
        return lease_ids

    def add_xlsx_sheet(self, report_data, workbook, STYLE_LINE_Data,
                       header_format, STYLE_LINE_HEADER, date_format):
        """ Method to add datas to the Tasc BIll Payment xlsx report"""
        self.ensure_one()
        worksheet = workbook.add_worksheet(_('Tasc Lease Details Report'))
        lang = self.env.user.lang
        if lang.startswith('ar_'):
            worksheet.right_to_left()

        row = 0
        col = 0
        worksheet.merge_range(row, row, col, col + 12,
                              _('Tasc Lease Details Report'),
                              STYLE_LINE_HEADER)
        row += 1
        col = 0
        worksheet.write(row, col, _('Lease Number'), header_format)
        col += 1
        worksheet.write(row, col, _('Original Contract Period'), header_format)
        col += 1
        worksheet.write(row, col, _('Total Contract period'),
                        header_format)
        col += 1
        worksheet.write(row, col, _('Commencement Date'), header_format)
        col += 1
        worksheet.write(row, col, _('End Date'), header_format)
        col += 1
        worksheet.write(row, col, _('Current Status'), header_format)
        col += 1
        worksheet.write(row, col, _('Original End Date'), header_format)
        col += 1
        worksheet.write(row, col, _('Extended End Date'), header_format)
        col += 1
        worksheet.write(row, col, _('Termination Date'), header_format)
        col += 1
        worksheet.write(row, col, _('Installment Amount'), header_format)
        col += 1
        worksheet.write(row, col, _('SD Amount'), header_format)
        col += 1
        worksheet.write(row, col, _('Lessor Type'), header_format)
        col += 1
        worksheet.write(row, col, _('Company'), header_format)
        row += 1
        for line in report_data:
            col = 0
            if line.name:
                worksheet.write(row, col, line.name,
                                STYLE_LINE_Data)
            else:
                worksheet.write(row, col, '', STYLE_LINE_Data)
            col += 1
            if line.lease_contract_period:
                worksheet.write(row, col, line.lease_contract_period,
                                STYLE_LINE_Data)
            else:
                worksheet.write(row, col, '', STYLE_LINE_Data)
            col += 1
            if line.total_lease_period:
                worksheet.write(row, col, line.total_lease_period,
                                STYLE_LINE_Data)
            else:
                worksheet.write(row, col, '', STYLE_LINE_Data)
            col += 1

            if line.commencement_date:
                worksheet.write(row, col, line.commencement_date,
                                date_format)
            else:
                worksheet.write(row, col, '', date_format)
            col += 1
            if line.end_date:
                worksheet.write(row, col, line.end_date,
                                date_format)
            else:
                worksheet.write(row, col, '', date_format)
            col += 1
            if line.state:
                worksheet.write(row, col, line.state,
                                STYLE_LINE_Data)
            else:
                worksheet.write(row, col, '', STYLE_LINE_Data)
            col += 1

            if line.estimated_ending_date:
                worksheet.write(row, col, line.estimated_ending_date,
                                date_format)
            else:
                worksheet.write(row, col, '', date_format)
            col += 1
            if line.end_date:
                worksheet.write(row, col, line.end_date,
                                date_format)
            else:
                worksheet.write(row, col, '', date_format)
            col += 1
            if line.termination_date:
                worksheet.write(row, col, line.termination_date,
                                date_format)
            else:
                worksheet.write(row, col, '', date_format)
            col += 1
            if line.installment_amount:
                worksheet.write(row, col, line.installment_amount,
                                STYLE_LINE_Data)
            else:
                worksheet.write(row, col, '', STYLE_LINE_Data)
            col += 1
            if line.security_amount:
                worksheet.write(row, col, line.security_amount,
                                STYLE_LINE_Data)
            else:
                worksheet.write(row, col, '', STYLE_LINE_Data)
            col += 1
            if line.leasor_type:
                worksheet.write(row, col, line.leasor_type,
                                STYLE_LINE_Data)
            else:
                worksheet.write(row, col, '', STYLE_LINE_Data)
            col += 1
            if line.company_id:
                worksheet.write(row, col, line.company_id.name,
                                STYLE_LINE_Data)
            else:
                worksheet.write(row, col, '', STYLE_LINE_Data)
            col += 1
            row += 1
