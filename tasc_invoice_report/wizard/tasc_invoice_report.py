import base64
import io
import re
import xlsxwriter
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.safe_eval import datetime


class TascInvoiceReport(models.TransientModel):
    _name = 'tasc.invoice.report'
    _description = 'TASC Customer Receipt Report'

    payment_start_date = fields.Date(string="Payment From Date",
                             default=datetime.datetime.now(), required=True)
    payment_end_date = fields.Date(string="Payment To Date",
                           default=datetime.datetime.now(), required=True)

    company_id = fields.Many2one('res.company', 'Company',
                                 default=lambda self: self.env.company,
                                 required=True)
    excel_sheet = fields.Binary('Download Report')
    excel_sheet_name = fields.Char(string='Name', size=64)

    def clean_ref(self, ref):
        return re.sub(r'\s*\(.*?\)\s*', '', ref).strip()

    @api.constrains('payment_end_date')
    def onsave_end_date(self):
        if self.payment_end_date < self.payment_start_date:
            raise UserError(
                "The payment end date should be greater than or equal to payment start date.")


    def print_report_xlsx(self):
        """ Method for print TASC Customer Receipts report"""
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


        self.add_xlsx_sheet(report_data, workbook, STYLE_LINE_Data,
                            header_format, STYLE_LINE_HEADER, date_format)

        self.excel_sheet_name = 'TASC Customer Receipt Report'
        workbook.close()
        output.seek(0)
        self.excel_sheet = base64.b64encode(output.read())
        self.excel_sheet_name = str(self.excel_sheet_name) + '.xlsx'
        return {
            'type': 'ir.actions.act_url',
            'name': 'TASC Customer Receipt Report',
            'url': '/web/content/%s/%s/excel_sheet/%s?download=true' % (
                self._name, self.id, self.excel_sheet_name),
            'target': 'new'
        }

    def get_report_data(self):
        """Method to compute TASC Customer Receipt Report."""
        invoices = self.env['account.move'].search([('company_id', '=', self.company_id.id),('move_type','=','out_invoice')])
        return invoices

    def add_xlsx_sheet(self, report_data, workbook, STYLE_LINE_Data,
                       header_format, STYLE_LINE_HEADER, date_format):
        """ Method to add datas to the TASC Customer Receipt Report"""
        self.ensure_one()
        worksheet = workbook.add_worksheet(_('TASC Customer Receipt Report'))
        lang = self.env.user.lang
        if lang.startswith('ar_'):
            worksheet.right_to_left()

        row = 0
        col = 0
        worksheet.merge_range(row, row, col, col + 11,
                              _('TASC Customer Receipt Report'),
                              STYLE_LINE_HEADER)
        row += 1
        col = 0
        worksheet.write(row, col, _('Customer Invoice Number'), header_format)
        col += 1
        worksheet.write(row, col, _('Date'), header_format)
        col += 1
        worksheet.write(row, col, _('Partner'), header_format)
        col += 1
        worksheet.write(row, col, _('Due Date'), header_format)
        col += 1
        worksheet.write(row, col, _('Payment Terms'), header_format)
        col += 1
        worksheet.write(row, col, _('Currency'), header_format)
        col += 1
        worksheet.write(row, col, _('Total'), header_format)
        col += 1
        worksheet.write(row, col, _('Payment Date'), header_format)
        col += 1
        worksheet.write(row, col, _('Payment Amount'), header_format)
        col += 1
        worksheet.write(row, col, _('Amount Due'), header_format)
        row += 1
        start = self.payment_start_date
        end = self.payment_end_date
        for move in report_data:
            s = move.invoice_payments_widget
            if s:
                filtered_payments = [
                    p for p in s['content'] if start <= p['date'] <= end
                ]
                for payment in filtered_payments:
                    col = 0
                    worksheet.write(row, col, move.name if move.name else '',
                                    STYLE_LINE_Data)
                    col += 1
                    worksheet.write(row, col, move.invoice_date if move.invoice_date else '',
                                    date_format)
                    col += 1
                    worksheet.write(row, col, move.partner_id.name if move.partner_id else '',
                                    STYLE_LINE_Data)
                    col += 1
                    worksheet.write(row, col, move.invoice_date_due if move.invoice_date_due else '',
                                    date_format)
                    col += 1
                    worksheet.write(row, col,
                                    move.invoice_payment_term_id.name if move.invoice_payment_term_id else '',
                                    STYLE_LINE_Data)
                    col += 1
                    worksheet.write(row, col, move.currency_id.name if move.currency_id else '',
                                    STYLE_LINE_Data)
                    col += 1
                    worksheet.write(row, col, move.amount_total_signed if move.amount_total_signed else 0,
                                    STYLE_LINE_Data)
                    col += 1
                    worksheet.write(row, col, payment["date"] if payment["date"] else '',
                                    date_format)
                    col += 1
                    worksheet.write(row, col, payment["amount"] if payment["amount"] else 0,
                                    STYLE_LINE_Data)
                    col += 1
                    worksheet.write(row, col, move.amount_residual_signed if move.amount_residual_signed else 0,
                                    STYLE_LINE_Data)
                    col += 1
                    row += 1
            else:
                payment_ids = self.env['account.payment'].search([('date','>=',start),('date','<=',end)]).filtered(
                    lambda x: move.id in x.reconciled_invoice_ids.ids)
                if payment_ids:
                    for pay in payment_ids:
                        col=0
                        worksheet.write(row, col, move.name if move.name else '',
                                            STYLE_LINE_Data)
                        col += 1
                        worksheet.write(row, col, move.invoice_date if move.invoice_date else '',
                                        date_format)
                        col += 1
                        worksheet.write(row, col, move.partner_id.name if move.partner_id else '',
                                        STYLE_LINE_Data)
                        col += 1
                        worksheet.write(row, col, move.invoice_date_due if move.invoice_date_due else '',
                                        date_format)
                        col += 1
                        worksheet.write(row, col, move.invoice_payment_term_id.name if move.invoice_payment_term_id else '',
                                        STYLE_LINE_Data)
                        col += 1
                        worksheet.write(row, col, move.currency_id.name if move.currency_id else '',
                                        STYLE_LINE_Data)
                        col += 1
                        worksheet.write(row, col, move.amount_total_signed if move.amount_total_signed else 0,
                                        STYLE_LINE_Data)
                        col += 1
                        worksheet.write(row, col, pay.date if pay.date else '',
                                        date_format)
                        col += 1
                        worksheet.write(row, col, pay.amount if pay.amount else 0,
                                        STYLE_LINE_Data)
                        col += 1
                        worksheet.write(row, col, move.amount_residual_signed if move.amount_residual_signed else 0,
                                        STYLE_LINE_Data)
                        col += 1
                        row+=1
