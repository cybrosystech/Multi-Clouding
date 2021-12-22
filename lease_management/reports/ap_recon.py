# -*- coding: utf-8 -*-
""" init object """
import pytz
import base64
import io
from io import BytesIO
from psycopg2.extensions import AsIs
from babel.dates import format_date, format_datetime, format_time
from odoo import fields, models, api, _ ,tools, SUPERUSER_ID
from odoo.exceptions import ValidationError,UserError
from datetime import datetime , date ,timedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DTF
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from dateutil.relativedelta import relativedelta
from odoo.fields import Datetime as fieldsDatetime
import calendar
from odoo import http
from odoo.http import request
from odoo import tools

try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    import xlsxwriter


class APRecon(models.TransientModel):
    _name = 'ap.recon.wizard'
    _description = 'ap.recon.wizard'

    def _get_date_from_now(self):
            today=datetime.now().today()
            first_day_this_month = date(day=1, month=today.month, year=today.year)
            return first_day_this_month

    def _get_date_to(self):
        # import calendar
        today = datetime.now().today()
        last_day = calendar.monthrange(today.year,today.month)
        last_day_this_month = date(day=last_day[1], month=today.month, year=today.year)
        return last_day_this_month

    date_from = fields.Date(string="Date From",default=_get_date_from_now , required=True, )
    date_to = fields.Date(string="Date To",default=_get_date_to , required=True, )
    vendor_ids = fields.Many2many(comodel_name="res.partner", string="Leasor", required=False,)
    analytic_account_ids = fields.Many2many(comodel_name="account.analytic.account",)

    excel_sheet = fields.Binary('Download Report')
    excel_sheet_name = fields.Char(string='Name', size=64)

    def get_report_data(self):
        data = []
        domain = [('move_type', '=', 'in_invoice'),('leasee_contract_id', '!=', False)]

        vendor_bills = self.env['account.move'].search(domain).filtered(lambda bill: bill.invoice_date <= self.date_to and bill.invoice_date >= self.date_from)
        for bill in vendor_bills:
            leasee_installment_id = self.env['leasee.installment'].search([('installment_invoice_id', '=', bill.id)],limit=1)
            if leasee_installment_id:
                data.append({
                    'description': bill.display_name,
                    'month': bill.invoice_date.strftime(DF) if bill.invoice_date else '',
                    'due_date': bill.invoice_date_due.strftime(DF) if bill.invoice_date_due else '',
                    'leasor_name': bill.partner_id.name,
                    'lease_no': bill.leasee_contract_id.name,
                    'lease_payment_amount': bill.amount_untaxed,
                    'interest_paid': leasee_installment_id.subsequent_amount,
                    'principal_paid': bill.amount_untaxed - leasee_installment_id.subsequent_amount,
                    'operating_exp_paid': bill.payment_state,
                })
        return data

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
            'font_size': 12,
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
        TABLE_data_o = workbook.add_format({
            'bold': 1,
            'font_name': 'Aharoni',
            'border': 0,
            'font_size': 12,
            'align': 'center',
            'valign': 'vcenter',
            'font_color': 'black',
        })
        STYLE_LINE_Data = STYLE_LINE
        STYLE_LINE_Data.num_format_str = '#,##0.00_);(#,##0.00)'

        if report_data:
            self.add_xlsx_sheet(report_data, workbook, STYLE_LINE_Data, header_format)

        self.excel_sheet_name = 'AP Reconcile'
        workbook.close()
        output.seek(0)
        self.excel_sheet = base64.b64encode(output.read())
        self.excel_sheet_name = str(self.excel_sheet_name) + '.xlsx'
        return {
            'type': 'ir.actions.act_url',
            'name': 'AP Reconcile',
            'url': '/web/content/%s/%s/excel_sheet/%s?download=true' % (self._name, self.id, self.excel_sheet_name),
            'target': 'self'
        }

    def add_xlsx_sheet(self, report_data, workbook, STYLE_LINE_Data, header_format):
        self.ensure_one()
        worksheet = workbook.add_worksheet(_('Report'))
        lang = self.env.user.lang
        if lang.startswith('ar_'):
            worksheet.right_to_left()

        row = 0
        col = 0
        worksheet.merge_range(row , row, col, col + 8, _('A/P Reconcile'), STYLE_LINE_Data)

        row += 1
        col = 0
        worksheet.write(row, col, _('Description'), header_format)
        col += 1
        worksheet.write(row, col, _('Month'), header_format)
        col += 1
        worksheet.write(row, col, _('Due Date'), header_format)
        col += 1
        worksheet.write(row, col, _('Lessor Name'), header_format)
        col += 1
        worksheet.write(row, col, _('Lease No.'), header_format)
        col += 1
        worksheet.write(row, col, _('Lease Payment Amt (LCY, exVAT)'), header_format)
        col += 1
        worksheet.write(row, col, _('CF Interest Paid (LCY)'), header_format)
        col += 1
        worksheet.write(row, col, _('CF Principal Paid (LCY)'), header_format)
        col += 1
        worksheet.write(row, col, _('CF Operating Exp. Paid (LCY)'), header_format)

        for line in report_data:
            col = 0
            row += 1
            worksheet.write(row, col, line['description'], STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['month'], STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['due_date'], STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['leasor_name'], STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['lease_no'], STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['lease_payment_amount'], STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['interest_paid'], STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['principal_paid'], STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['operating_exp_paid'], STYLE_LINE_Data)










