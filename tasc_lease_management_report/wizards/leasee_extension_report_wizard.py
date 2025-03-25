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
    state = fields.Selection(string="Status", default='extended',selection=[('draft', 'Draft'),
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
            'target': 'new'
        }

    def add_xlsx_sheet(self, report_data, workbook, STYLE_LINE_Data,
                       header_format, STYLE_LINE_HEADER, date_format):
        self.ensure_one()
        worksheet = workbook.add_worksheet(_('Lease Extension Report'))
        lang = self.env.user.lang
        if lang.startswith('ar_'):
            worksheet.right_to_left()

        # row = 0
        # col = 0
        # worksheet.merge_range(row, row, col, col + 5, _('Lease Extension Report'), STYLE_LINE_HEADER)

        row = 0
        col = 3
        worksheet.merge_range(row, 0, row, col + 5, _('Original Lease'), header_format)

        row += 1
        col = 0
        headers = [_('Lease Name'), _('External Reference Number'), _('Project Site'),
                   _('Start Date'), _('End Date'), _('Installment Amount'),
                   _('Contract Period'), _('Leasor Type'),_('Creation Date')]

        for header in headers:
            worksheet.write(row, col, header, header_format)
            col += 1

        head_col = col  # Column where extended lease data starts

        for line in report_data:
            col = 0
            row += 1
            worksheet.write(row, col, line.name, STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line.external_reference_number, STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line.project_site_id.name, STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line.inception_date, date_format)
            col += 1
            worksheet.write(row, col, line.estimated_ending_date, date_format)
            col += 1
            worksheet.write(row, col, line.installment_amount, STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line.lease_contract_period, STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line.leasor_type, STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line.create_date, date_format)

            if line.child_ids:
                ext = 0
                for child in line.child_ids:
                    ext += 1  # Keep track of extended lease count
                    row2 = 0  # Header row for extended leasee

                    # Generate unique color
                    hexadecimal = ["#" + ''.join([random.choice('ABCDEF0123456789') for _ in range(6)])]

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

                    lease_name_ext = 'Extended Leasee ' + str(ext)

                    # Adjust column placement dynamically for multiple lease extensions
                    ext_col_start = head_col + (6 * (ext - 1))  # Dynamically shift right for each extension
                    ext_col_end = ext_col_start + 5

                    worksheet.merge_range(row2, ext_col_start, row2, ext_col_end, lease_name_ext, header_format_ext)

                    self.add_extension_data(workbook, worksheet, child, row, col, ext_col_start, STYLE_LINE_Data, ext,
                                            row2 + 1, header_format, date_format)

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
        col += 1
        worksheet.write(sub_head_row, col, _('Creation Date (EXT)'), header_format)
        worksheet.write(row, col, contract.create_date,
                        date_format)
        if contract.child_ids:
            for child in contract.child_ids:
                row2 = 0
                if extension_text == 'Original Leasee':
                    worksheet.merge_range(row2, 0, row2, head_col + 5,
                                          _(extension_text),
                                          header_format_subhead)
                else:
                    worksheet.merge_range(row2, head_col, row2, head_col + 5,
                                          _(extension_text),
                                          header_format_subhead)
                ext += 1
                self.add_extension_data(workbook, worksheet, child, row, col,
                                        head_col + 6,
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
