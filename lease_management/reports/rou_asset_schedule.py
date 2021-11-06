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


class CostVarianceWizard(models.TransientModel):
    _name = 'cost.variance.wizard'
    _description = 'Cost Variance Wizard'

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

    date_from = fields.Date(string="Date From",default=_get_date_from_now , required=False, )
    date_to = fields.Date(string="Date To",default=_get_date_to , required=False, )
    excel_sheet = fields.Binary('Download Report')
    excel_sheet_name = fields.Char(string='Name', size=64)

    def get_report_data(self):
        data = []
        data.append({
            'posting_date': 1,
            'document_no': 1,
            'account_number': 1,
            'account_name': 1,
            'description': 1,
            'amount': 1,
            'lease_no': 1,
            'dimension_1': 1,
            'dimension_2': 1,
            'dimension_3': 1,
            'dimension_4': 1,
            'company_name': 1,
            'accounting_period_end_date': 1,
            'line_no': 1,
            'download_datetime': 1,
            'user_id': 1,
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

        for cf_values in report_data:
            self.add_xlsx_sheet(cf_values,workbook, STYLE_LINE_Data, header_format)

        if report_data:
            self.add_xlsx_total_sheet(report_data, workbook, STYLE_LINE_Data, header_format)

        self.excel_sheet_name = 'Cost Variance Report '
        workbook.close()
        output.seek(0)
        self.excel_sheet = base64.b64encode(output.read())
        self.excel_sheet_name = str(self.excel_sheet_name) + '.xlsx'
        return {
            'type': 'ir.actions.act_url',
            'name': 'Cost Variance Report',
            'url': '/web/content/%s/%s/excel_sheet/Cost Variance Report.xlsx?download=true' % (self._name, self.id),
            'target': 'self'
        }

    def add_xlsx_sheet(self, cf_values, workbook, STYLE_LINE_Data, header_format):
        self.ensure_one()
        worksheet = workbook.add_worksheet(cf_values['name'])
        lang = self.env.user.lang
        if lang.startswith('ar_'):
            worksheet.right_to_left()

        row = 0
        col = 0
        worksheet.merge_range(row , row, col, col + 3, _('Cost Variance Report'), STYLE_LINE_Data)

        row += 1
        col = 0
        worksheet.write(row, col, _('Name'), STYLE_LINE_Data)
        col += 1
        worksheet.merge_range(row , row, col, col + 3, cf_values['name'], STYLE_LINE_Data)

        row += 2
        col = 0
        worksheet.write(row, col, _('Date From'), STYLE_LINE_Data)
        col += 1
        worksheet.write(row, col, cf_values['date_start'], STYLE_LINE_Data)
        col += 1
        worksheet.write(row, col, _('Date To'), STYLE_LINE_Data)
        col += 1
        worksheet.write(row, col, cf_values['date_end'], STYLE_LINE_Data)

        row += 2
        col = 0
        worksheet.write(row, col, _('Estimated Account'), header_format)
        col += 1
        worksheet.write(row, col, _('Estimated Amount'), header_format)
        col += 1
        worksheet.write(row, col, _('Actual Account'), header_format)
        col += 1
        worksheet.write(row, col, _('Actual Amount'), header_format)
        col += 1
        worksheet.write(row, col, _('Variance Account'), header_format)
        col += 1
        worksheet.write(row, col, _('Variance Amount'), header_format)

        for line in cf_values['cost_lines']:
            col = 0
            row += 1
            worksheet.write(row, col, line['estimated_account_id'], STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['estimated_cost'], STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['actual_account_id'], STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['actual_cost'], STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['variance_account_id'], STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['variance_amount'], STYLE_LINE_Data)

        row += 1
        col = 0
        worksheet.write(row, col, _('Total'), header_format)
        col += 1
        worksheet.write(row, col, cf_values['total_estimated_cost'], header_format)
        col += 1
        worksheet.write(row, col, _('Total'), header_format)
        col += 1
        worksheet.write(row, col, cf_values['total_actual_cost'], header_format)
        col += 1
        worksheet.write(row, col, _('Total'), header_format)
        col += 1
        worksheet.write(row, col, cf_values['total_variance_amount'], header_format)

    def add_xlsx_total_sheet(self, report_data, workbook, STYLE_LINE_Data, header_format):
        self.ensure_one()
        worksheet = workbook.add_worksheet(_('IFRS16 GL Output file'))
        lang = self.env.user.lang
        if lang.startswith('ar_'):
            worksheet.right_to_left()

        row = 0
        col = 0
        worksheet.merge_range(row , row, col, col + 10, _('General Ledger postings'), STYLE_LINE_Data)
        worksheet.merge_range(row , row, col+11, col + 15, _('Interface technical fields'), STYLE_LINE_Data)

        row += 1
        col = 0
        worksheet.write(row, col, _('Posting Date'), header_format)
        col += 1
        worksheet.write(row, col, _('Document No.'), header_format)
        col += 1
        worksheet.write(row, col, _('G/L Account No.'), header_format)
        col += 1
        worksheet.write(row, col, _('G/L Account Name'), header_format)
        col += 1
        worksheet.write(row, col, _('Description'), header_format)
        col += 1
        worksheet.write(row, col, _('Amount'), header_format)
        col += 1
        worksheet.write(row, col, _('Lease No.'), header_format)
        col += 1
        worksheet.write(row, col, _('Dimension 1'), header_format)
        col += 1
        worksheet.write(row, col, _('Dimension 2'), header_format)
        col += 1
        worksheet.write(row, col, _('Dimension 3'), header_format)
        col += 1
        worksheet.write(row, col, _('Dimension 4'), header_format)

        col += 1
        worksheet.write(row, col, _('Company Name'), header_format)
        col += 1
        worksheet.write(row, col, _('Accounting Period End Date'), header_format)
        col += 1
        worksheet.write(row, col, _('Line No.'), header_format)
        col += 1
        worksheet.write(row, col, _('Download Date and Time'), header_format)
        col += 1
        worksheet.write(row, col, _('User ID'), header_format)

        for line in report_data:
            col = 0
            row += 1
            worksheet.write(row, col, line['posting_date'], STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['document_no'], STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['account_number'], STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['account_name'], STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['description'], STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['amount'], STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['lease_no'], STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['dimension_1'], STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['dimension_2'], STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['dimension_3'], STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['dimension_4'], STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['company_name'], STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['accounting_period_end_date'], STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['line_no'], STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['download_datetime'], STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['user_id'], STYLE_LINE_Data)





