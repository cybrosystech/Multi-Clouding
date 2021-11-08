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
            'description': 1,
            'month': 1,
            'due_date': 1,
            'leasor_name': 1,
            'lease_no': 1,
            'lease_payment_amount': 1,
            'interest_paid': 1,
            'principal_paid': 1,
            'operating_exp_paid': 1,
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

    def add_xlsx_total_sheet(self, report_data, workbook, STYLE_LINE_Data, header_format):
        self.ensure_one()
        worksheet = workbook.add_worksheet(_('RoU Asset Schedule'))
        lang = self.env.user.lang
        if lang.startswith('ar_'):
            worksheet.right_to_left()

        row = 0
        col = 0
        worksheet.write(row, col, _('Period No.'), header_format)
        col += 1
        worksheet.write(row, col, _('Period Start Date'), header_format)
        col += 1
        worksheet.write(row, col, _('Depreciation Term (mths)'), header_format)
        col += 1
        worksheet.write(row, col, _('Opening Balance'), header_format)
        col += 1
        worksheet.write(row, col, _('Initial Measurement'), header_format)
        col += 1
        worksheet.write(row, col, _('Impairment (-)'), header_format)
        col += 1
        worksheet.write(row, col, _('Direct Cost Added (+)'), header_format)
        col += 1
        worksheet.write(row, col, _('Depreciation (-)'), header_format)
        col += 1
        worksheet.write(row, col, _('Adjustment of Lease Liability (+)'), header_format)
        col += 1
        worksheet.write(row, col, _('ROU Sub-Leased'), header_format)
        col += 1
        worksheet.write(row, col, _('ROU increase/decrease'), header_format)
        col += 1
        worksheet.write(row, col, _('Losses on onerous leases (+)'), header_format)
        col += 1
        worksheet.write(row, col, _('Loss on Sub-lease Activation (-)'), header_format)
        col += 1
        worksheet.write(row, col, _('Closing Balance'), header_format)
        col += 1
        worksheet.write(row, col, _('Period End Date'), header_format)
        col += 1
        worksheet.write(row, col, _('Comment'), header_format)
        col += 1
        worksheet.write(row, col, _('Posted to G/L'), header_format)
        col += 1
        worksheet.write(row, col, _('Posting Date'), header_format)
        col += 1
        worksheet.write(row, col, _('Posting Document No.'), header_format)

        for line in report_data:
            col = 0
            row += 1
            worksheet.write(row, col, line['period_no'], STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['period_start_date'], STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['depreciation_term'], STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['opening_balance'], STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['initial_measurement'], STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['impairment'], STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['direct_cost_added'], STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['depreciation'], STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['adjustment_lease_liability'], STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['rou_sub_leased'], STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['rou_increase_decrease'], STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['loss_leases'], STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['loss_sub_lease'], STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['closing_balance'], STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['period_end_date'], STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['comment'], STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['posted_gl'], STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['posting_date'], STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['posting_doc_no'], STYLE_LINE_Data)






