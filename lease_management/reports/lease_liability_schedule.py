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


class LeaseLiabilitySchedule(models.TransientModel):
    _name = 'lease.liability.schedule.wizard'
    _description = 'Lease Liability Schedule'

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
    contract_ids = fields.Many2many(comodel_name="leasee.contract")
    analytic_account_ids = fields.Many2many(comodel_name="account.analytic.account")
    partner_ids = fields.Many2many(comodel_name="res.partner",)
    excel_sheet = fields.Binary('Download Report')
    excel_sheet_name = fields.Char(string='Name', size=64)

    def get_report_data(self):
        data = []
        domain = [('date','>=', self.date_from),('date', '<=', self.date_to)]
        if self.contract_ids:
            domain.append(('leasee_contract_id', 'in', self.contract_ids.ids))
        elif self.analytic_account_ids:
            domain.append(('leasee_contract_id.analytic_account_id', 'in', self.analytic_account_ids.ids))
        elif self.partner_ids:
            domain.append(('leasee_contract_id.vendor_id', 'in', self.partner_ids.ids))
        installments = self.env['leasee.installment'].search(domain, order='leasee_contract_id,date')
        for installment in installments:
            period_no = installment.get_period_order()
            opening_balance = installment.remaining_lease_liability
            closing_balance = opening_balance + installment.subsequent_amount - installment.amount
            if installment.leasee_contract_id.lease_contract_period_type == 'months':
                delta = relativedelta(months=installment.leasee_contract_id.lease_contract_period,days=-1)
            else:
                delta = relativedelta(years=installment.leasee_contract_id.lease_contract_period,days=-1)
            data.append({
                'period_no': period_no,
                'lease_no': installment.leasee_contract_id.name,
                'period_start_date': installment.date.strftime(DF),
                'opening_balance': opening_balance if period_no != 1 else 0,
                'opening_balance_lcy': self.env.company.currency_id._convert(opening_balance,
                                                                             installment.leasee_contract_id.leasee_currency_id,
                                                                             self.env.company,
                                                                             installment.date) if period_no != 1 else 0,
                'initial_measurement': opening_balance if period_no == 1 else 0,
                'interest': installment.subsequent_amount,
                'interest_lcy': self.env.company.currency_id._convert(installment.subsequent_amount,
                                                                      installment.leasee_contract_id.leasee_currency_id,
                                                                      self.env.company,
                                                                      installment.date),
                'payment': installment.amount,
                'remeasuring_lcy': 0,
                'closing_balance': closing_balance,
                'closing_balance_lcy': self.env.company.currency_id._convert(closing_balance,
                                                                             installment.leasee_contract_id.leasee_currency_id,
                                                                             self.env.company,
                                                                             installment.date),
                'period_end_date': (installment.date + delta).strftime(DF),
                'posted_to_gl': True if installment.installment_invoice_id.state == 'posted' else False,
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

        self.excel_sheet_name = 'Lease Liability Schedule'
        workbook.close()
        output.seek(0)
        self.excel_sheet = base64.b64encode(output.read())
        self.excel_sheet_name = str(self.excel_sheet_name) + '.xlsx'
        return {
            'type': 'ir.actions.act_url',
            'name': 'Lease Liability Schedule',
            'url': '/web/content/%s/%s/excel_sheet/Lease Liability Schedule.xlsx?download=true' % (self._name, self.id),
            'target': 'self'
        }

    def add_xlsx_sheet(self, report_data, workbook, STYLE_LINE_Data, header_format):
        self.ensure_one()
        worksheet = workbook.add_worksheet(_('Lease Liability Schedule'))
        lang = self.env.user.lang
        if lang.startswith('ar_'):
            worksheet.right_to_left()

        row = 0
        col = 0
        worksheet.write(row, col, _('Period No.'), header_format)
        col += 1
        worksheet.write(row, col, _('Lease No.'), header_format)
        col += 1
        worksheet.write(row, col, _('Period Start Date'), header_format)
        col += 1
        worksheet.write(row, col, _('Opening Balance (lease liability)'), header_format)
        col += 1
        worksheet.write(row, col, _('Opening Balance (LCY)'), header_format)
        col += 1
        worksheet.write(row, col, _('Initial Measurement'), header_format)
        col += 1
        worksheet.write(row, col, _('Interest (+)'), header_format)
        col += 1
        worksheet.write(row, col, _('Interest (LCY) (+)'), header_format)
        col += 1
        worksheet.write(row, col, _('Payment (-)'), header_format)
        col += 1
        worksheet.write(row, col, _('Remeasuring / Reassessment (LCY) (+)'), header_format)
        col += 1
        worksheet.write(row, col, _('Closing Balance'), header_format)
        col += 1
        worksheet.write(row, col, _('Closing Balance (LCY)'), header_format)
        col += 1
        worksheet.write(row, col, _('Period End Date'), header_format)
        col += 1
        worksheet.write(row, col, _('Posted to G/L'), header_format)

        for line in report_data:
            col = 0
            row += 1
            worksheet.write(row, col, line['period_no'], STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['lease_no'], STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['period_start_date'], STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['opening_balance'], STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['opening_balance_lcy'], STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['initial_measurement'], STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['interest'], STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['interest_lcy'], STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['payment'], STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['remeasuring_lcy'], STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['closing_balance'], STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['closing_balance_lcy'], STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['period_end_date'], STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['posted_to_gl'], STYLE_LINE_Data)




