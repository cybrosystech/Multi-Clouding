import base64
import xlsxwriter
import io
from odoo import fields, models, _


class PaymentReportBankIntegration(models.Model):
    _name = 'payment.report.bank.integration'

    company_id = fields.Many2one('res.company', string='Company',
                                 required=True,
                                 readonly=True,
                                 default=lambda self: self.env.company)
    date_from = fields.Date(string="Payment Date From")
    date_to = fields.Date(string="Payment Date To")
    journal_id = fields.Many2one('account.journal',
                                 domain="[('company_id','=',company_id),"
                                        "('type','=','bank')]", required=True)
    excel_sheet = fields.Binary('Download Report')
    excel_sheet_name = fields.Char(string='Name', size=64)

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
        STYLE_LINE_Data.num_format_str = '#,##0.00_);(#,##0.00)'

        if report_data:
            self.add_xlsx_sheet(report_data, workbook, STYLE_LINE_Data,
                                header_format, STYLE_LINE_HEADER)

        self.excel_sheet_name = 'Payment Report - Bank Integration'
        workbook.close()
        output.seek(0)
        self.excel_sheet = base64.b64encode(output.read())
        self.excel_sheet_name = str(self.excel_sheet_name) + '.xlsx'
        return {
            'type': 'ir.actions.act_url',
            'name': 'Payment Report - Bank Integration',
            'url': '/web/content/%s/%s/excel_sheet/%s?download=true' % (
                self._name, self.id, self.excel_sheet_name),
            'target': 'new'
        }

    def get_report_data(self):
        """Method to compute  Payment Report - Bank Integration Report data."""
        payments = self.env['account.payment'].search(
            [('company_id', '=', self.company_id.id),
             ('date', '>=', self.date_from), ('date', '<=', self.date_to),
             ('journal_id', '=', self.journal_id.id)])
        return payments

    def add_xlsx_sheet(self, report_data, workbook, STYLE_LINE_Data,
                       header_format, STYLE_LINE_HEADER):
        """ Method to add datas to the Payment Report - Bank Integration xlsx
        report"""
        date_format = workbook.add_format(
            {'num_format': 'yyyy/mm/dd', 'align': 'center'})
        self.ensure_one()
        worksheet = workbook.add_worksheet(
            _('Payment Report - Bank Integration'))
        lang = self.env.user.lang
        if lang.startswith('ar_'):
            worksheet.right_to_left()

        row = 0
        col = 0
        worksheet.merge_range(row, row, col, col + 16,
                              _('Payment Report - Bank Integration'),
                              STYLE_LINE_HEADER)
        row += 1
        col = 0
        worksheet.write(row, col, _('Transaction type code'), header_format)
        col += 1
        worksheet.write(row, col, _('Debit Account No'), header_format)
        col += 1
        worksheet.write(row, col, _('Beneficiary Account No'), header_format)
        col += 1
        worksheet.write(row, col, _('Beneficiary Name'), header_format)
        col += 1
        worksheet.write(row, col, _('Beneficiary addr. Line 1'), header_format)
        col += 1
        worksheet.write(row, col, _('Beneficiary addr. Line 2'), header_format)
        col += 1
        worksheet.write(row, col, _('Beneficiary addr. Line 3'), header_format)
        col += 1
        worksheet.write(row, col,
                        _('Beneficiary addr. Line 4(Bene Country 3 digit ISO code)'),
                        header_format)
        col += 1
        worksheet.write(row, col,
                        _('Beneficiary Bank swift code/IFSC Code'),
                        header_format)
        col += 1
        worksheet.write(row, col,
                        _('Customer reference no'),
                        header_format)
        col += 1
        worksheet.write(row, col,
                        _('Purpose code'),
                        header_format)
        col += 1
        worksheet.write(row, col,
                        _('Purpose of Payment'),
                        header_format)
        col += 1
        worksheet.write(row, col,
                        _('Date'),
                        header_format)
        col += 1
        worksheet.write(row, col,
                        _('Transaction currency'),
                        header_format)
        col += 1
        worksheet.write(row, col,
                        _('Payment amount'),
                        header_format)
        col += 1
        worksheet.write(row, col,
                        _('Charge Type'),
                        header_format)
        col += 1
        worksheet.write(row, col,
                        _('Transaction Type'),
                        header_format)
        col += 1
        for line in report_data:
            col = 0
            row += 1
            if line.partner_bank_id.bank_id.id == self.journal_id.bank_id.id:
                worksheet.write(row, col, 'BT', STYLE_LINE_Data)
            elif line.partner_bank_id.bank_id.country.id == self.journal_id.bank_id.country.id:
                worksheet.write(row, col, 'LBT', STYLE_LINE_Data)
            else:
                worksheet.write(row, col, 'TT', STYLE_LINE_Data)

            col += 1
            if line.journal_id.bank_account_id.acc_number:

                worksheet.write(row, col,
                                line.journal_id.bank_account_id.acc_number,
                                STYLE_LINE_Data)
            else:
                worksheet.write(row, col,
                                '',
                                STYLE_LINE_Data)
            col += 1
            if line.partner_bank_id.bank_iban:
                worksheet.write(row, col, line.partner_bank_id.bank_iban,
                                STYLE_LINE_Data)
            else:
                worksheet.write(row, col, '',
                                STYLE_LINE_Data)
            col += 1
            if line.partner_id.name:
                worksheet.write(row, col, line.partner_id.name,
                                STYLE_LINE_Data)
            else:
                worksheet.write(row, col, '',
                                STYLE_LINE_Data)
            col += 1

            if line.partner_id.street and line.partner_id.street2:
                worksheet.write(row, col,
                                line.partner_id.street + "," + line.partner_id.street2,
                                STYLE_LINE_Data)
            elif line.partner_id.street:
                worksheet.write(row, col,
                                line.partner_id.street,
                                STYLE_LINE_Data)
            elif line.partner_id.street2:
                worksheet.write(row, col,
                                line.partner_id.street2,
                                STYLE_LINE_Data)
            else:
                worksheet.write(row, col,
                                '',
                                STYLE_LINE_Data)

            col += 1
            if line.partner_id.city and line.partner_id.state_id:
                worksheet.write(row, col,
                                line.partner_id.city + ", " + line.partner_id.state_id.name,
                                STYLE_LINE_Data)
            elif line.partner_id.city:
                worksheet.write(row, col,
                                line.partner_id.city,
                                STYLE_LINE_Data)
            elif line.partner_id.state_id:
                worksheet.write(row, col,
                                line.partner_id.state_id.name,
                                STYLE_LINE_Data)
            else:
                worksheet.write(row, col,
                                '',
                                STYLE_LINE_Data)
            col += 1
            if line.partner_id.country_id and line.partner_id.zip:
                worksheet.write(row, col,
                                line.partner_id.country_id.name + ", " + line.partner_id.zip,
                                STYLE_LINE_Data)
            elif line.partner_id.country_id:
                worksheet.write(row, col,
                                line.partner_id.country_id.name,
                                STYLE_LINE_Data)
            elif line.partner_id.zip:
                worksheet.write(row, col,
                                line.partner_id.zip,
                                STYLE_LINE_Data)
            else:
                worksheet.write(row, col,
                                '',
                                STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, '', STYLE_LINE_Data)
            col += 1
            if line.partner_bank_id.bank_bic:
                worksheet.write(row, col, line.partner_bank_id.bank_bic,
                                STYLE_LINE_Data)
            else:
                worksheet.write(row, col, '',
                                STYLE_LINE_Data)
            col += 1
            if line.name:
                worksheet.write(row, col, line.name,
                                STYLE_LINE_Data)
            else:
                worksheet.write(row, col, '',
                                STYLE_LINE_Data)
            col += 1
            if line.purpose_code_id.code:
                worksheet.write(row, col, line.purpose_code_id.code,
                                STYLE_LINE_Data)
            else:
                worksheet.write(row, col, '',
                                STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, 'Vendor Payment',
                            STYLE_LINE_Data)
            col += 1
            if line.date:
                worksheet.write(row, col, line.date,
                                date_format)
            else:
                worksheet.write(row, col, '',
                                STYLE_LINE_Data)
            col += 1
            if line.currency_id:
                worksheet.write(row, col, line.currency_id.name,
                                STYLE_LINE_Data)
            else:
                worksheet.write(row, col, '',
                                STYLE_LINE_Data)
            col += 1
            if line.amount:
                worksheet.write(row, col, line.amount,
                                STYLE_LINE_Data)
            else:
                worksheet.write(row, col, '',
                                STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, 'OUR',
                            STYLE_LINE_Data)
            col += 1

            if line.partner_bank_id.bank_id.id == self.journal_id.bank_id.id:
                worksheet.write(row, col, 'BT', STYLE_LINE_Data)
            else:
                worksheet.write(row, col, 'RTGS', STYLE_LINE_Data)
