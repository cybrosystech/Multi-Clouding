import base64
import io
import random
import xlsxwriter
from odoo import fields, models, _


class LeaseContractExtensionXlsxWizard(models.TransientModel):
    """ Class for Lease Extension Report Xlsx"""
    _name = "lease.contract.extension.xlsx.report.wizard"
    _description = "Leasee Extension xlsx report"

    lease_contract_ids = fields.Many2many('leasee.contract',
                                          string="Lease Contract")
    state = fields.Selection(string="Status", selection=[('draft', 'Draft'),
                                                         ('active', 'Active'),
                                                         ('extended',
                                                          'Extended'),
                                                         ('expired', 'Expired'),
                                                         ('terminated',
                                                          'Terminated')])
    excel_sheet = fields.Binary('Download Report')
    excel_sheet_name = fields.Char(string='Name', size=64)

    def print_report_xlsx(self):
        """Method to print xlsx report based on the selected parameters."""
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
            'align': 'center',
            'valign': 'vcenter',
            'num_format': 'yyyy/mm/dd'
        })

        TABLE_data_tolal_line.num_format_str = '#,##0.00'
        STYLE_LINE_Data = STYLE_LINE
        STYLE_LINE_Data.num_format_str = '#,##0.00_);(#,##0.00)'

        if report_data:
            self.add_xlsx_sheet(report_data, workbook, STYLE_LINE_Data,
                                header_format, STYLE_LINE_HEADER,date_format)

        self.excel_sheet_name = 'Lease Extension Report'
        workbook.close()
        output.seek(0)
        self.excel_sheet = base64.b64encode(output.read())
        self.excel_sheet_name = str(self.excel_sheet_name) + '.xlsx'
        return {
            'type': 'ir.actions.act_url',
            'name': 'Lease Extension Report',
            'url': '/web/content/%s/%s/excel_sheet/%s?download=true' % (
                self._name, self.id, self.excel_sheet_name),
            'target': 'self'
        }

    def add_xlsx_sheet(self, report_data, workbook, STYLE_LINE_Data,
                       header_format, STYLE_LINE_HEADER,date_format):
        self.ensure_one()
        worksheet = workbook.add_worksheet(
            _('Lease Extension Report'))
        lang = self.env.user.lang
        if lang.startswith('ar_'):
            worksheet.right_to_left()

        row = 0
        col = 0
        worksheet.merge_range(row, row, col, col + 5,
                              _('Lease Extension Report'),
                              STYLE_LINE_HEADER)
        row = 1
        col = 3
        worksheet.merge_range(row, col, row, col + 4,
                              _('Original Lease'),
                              header_format)

        row += 1
        col = 0
        worksheet.write(row, col, _('Lease Name'), header_format)
        col += 1
        worksheet.write(row, col, _('External Reference Number'), header_format)
        col += 1
        worksheet.write(row, col, _('Project Site'), header_format)
        col += 1
        worksheet.write(row, col, _('Start Date'), header_format)
        col += 1
        worksheet.write(row, col, _('End Date'), header_format)
        col += 1
        worksheet.write(row, col, _('Installment Amount'), header_format)
        col += 1
        worksheet.write(row, col, _('Contract Period'), header_format)
        col += 1
        worksheet.write(row, col, _('Leasor Type'), header_format)
        col += 1

        head_col = col
        sub_head_row = 2
        for line in report_data:
            ext = 0
            col = 0
            row += 1
            worksheet.write(row, col, line.name, STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line.external_reference_number,
                            STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line.project_site_id.name,
                            STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line.inception_date,
                            date_format)
            col += 1
            worksheet.write(row, col, line.estimated_ending_date,
                            date_format)
            col += 1
            worksheet.write(row, col, line.installment_amount,
                            STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line.lease_contract_period,
                            STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line.leasor_type,
                            STYLE_LINE_Data)
            if line.child_ids:
                hexadecimal = ["#" + ''.join(
                    [random.choice('ABCDEF0123456789') for i in range(6)])]

                header_format_ext = workbook.add_format({
                    'bold': 1,
                    'font_name': 'Aharoni',
                    'border': 0,
                    'font_size': 13,
                    'align': 'center',
                    'valign': 'vcenter',
                    'font_color': 'black',
                    'bg_color': hexadecimal[0],
                })
                row2 = 1
                ext += 1
                lease_name_ext = 'Extended Leasee' + str(ext)
                worksheet.merge_range(row2, head_col, row2, head_col + 4,
                                      _(lease_name_ext),
                                      header_format_ext)
                for child in line.child_ids:
                    ext += 1

                    self.add_extension_data(workbook, worksheet, child, row,
                                            col, head_col + 5,
                                            STYLE_LINE_Data, ext, sub_head_row,header_format,date_format)

    def add_extension_data(self, workbook, worksheet, contract, row, col,
                           head_col, STYLE_LINE_Data, ext, sub_head_row,
                           header_format,date_format):
        if ext == 0:
            extension_text = 'Original Leasee'
        else:
            extension_text = 'Extended Leasee ' + str(ext)
        hexadecimal = ["#" + ''.join([random.choice('ABCDEF0123456789') for i in range(6)])]
        header_format_subhead = workbook.add_format({
            'bold': 1,
            'font_name': 'Aharoni',
            'border': 0,
            'font_size': 13,
            'align': 'center',
            'valign': 'vcenter',
            'font_color': 'black',
            'bg_color': hexadecimal[0],
        })

        col += 1
        worksheet.write(sub_head_row, col, _('Start Date'), header_format)

        worksheet.write(row, col, contract.inception_date,
                        date_format)
        col += 1
        worksheet.write(sub_head_row, col, _('End Date'), header_format)

        worksheet.write(row, col, contract.estimated_ending_date,
                        date_format)
        col += 1
        worksheet.write(sub_head_row, col, _('Installment Amount'), header_format)
        worksheet.write(row, col, contract.installment_amount, STYLE_LINE_Data)
        col += 1
        worksheet.write(sub_head_row, col, _('Contract Period'), header_format)
        worksheet.write(row, col, contract.lease_contract_period,
                        STYLE_LINE_Data)
        col += 1
        worksheet.write(sub_head_row, col, _('Leasor Type'), header_format)
        worksheet.write(row, col, contract.leasor_type,
                        STYLE_LINE_Data)
        if contract.child_ids:
            for child in contract.child_ids:
                row2 = 1
                worksheet.merge_range(row2, head_col, row2, head_col + 4,
                                      _(extension_text),
                                      header_format_subhead)
                ext += 1
                self.add_extension_data(workbook, worksheet, child, row, col,
                                        head_col + 5,
                                        STYLE_LINE_Data, ext, sub_head_row,header_format,date_format)

    def get_report_data(self):
        data = []
        if self.lease_contract_ids:
            lease_contract_ids = self.env['leasee.contract'].search(
                [('id', 'in', self.lease_contract_ids.ids),
                 ('parent_id', '=', False)
                 ])
        else:
            lease_contract_ids = self.env['leasee.contract'].search(
                [('company_id', '=', self.env.company.id),
                 ('parent_id', '=', False)],
                order='id ASC')
        if lease_contract_ids:
            if self.state:
                data = lease_contract_ids.filtered(
                    lambda l: l.state == self.state)
            else:
                data = lease_contract_ids
        return data
