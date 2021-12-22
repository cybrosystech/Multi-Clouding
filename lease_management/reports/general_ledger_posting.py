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


class GeneralLedgerPostingWizard(models.TransientModel):
    _name = 'general.ledger.posting.wizard'
    _description = 'General Ledger Posting Wizard'

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
    account_ids = fields.Many2many(comodel_name="account.account",required=True )
    leasee_contract_ids = fields.Many2many(comodel_name="leasee.contract", domain=[('parent_id', '=', False)] )
    analytic_account_ids = fields.Many2many(comodel_name="account.analytic.account", )
    is_posted = fields.Boolean(string="Show Posted Entries Only ?", default=False  )
    excel_sheet = fields.Binary('Download Report')
    excel_sheet_name = fields.Char(string='Name', size=64)

    def get_report_data(self):
        data = []
        domain = [('move_id.date', '<=', self.date_to),('move_id.date', '>=', self.date_from),]
        if self.is_posted:
            domain.append(('move_id.state', '=', 'posted'))
        if self.account_ids:
            domain.append(('account_id', 'in', self.account_ids.ids))
        if self.analytic_account_ids:
            domain.append(('analytic_account_id', 'in', self.analytic_account_ids.ids))
        if self.leasee_contract_ids:
            # domain.append(('move_id.leasee_contract_id', 'in', self.leasee_contract_ids.ids))
            domain.append(('move_id.leasee_contract_id', 'child_of', self.leasee_contract_ids.ids))

        journal_items = self.env['account.move.line'].search(domain,order='account_id')
        for line in journal_items:
            data.append({
                'posting_date': line.move_id.posting_date.strftime(DF) if line.move_id.posting_date else '',
                'document_no': line.move_id.name,
                'account_number': line.account_id.code,
                'account_name': line.account_id.name,
                'description': line.name,
                'amount': line.amount_currency,
                'lease_no': line.move_id.leasee_contract_id.name or '',
                'dimension_1': line.analytic_account_id.name or '',
                'dimension_2': line.project_site_id.name or '',
                'dimension_3': line.type_id.name or '',
                'dimension_4': line.location_id.name or '',
                'company_name': line.company_id.name,
                # 'accounting_period_end_date': 1,
                # 'line_no': 1,
                'download_datetime': fieldsDatetime.now().strftime(DTF),
                'debit': line.debit,
                'credit': line.credit,
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

        self.excel_sheet_name = 'General Ledger Posting'
        workbook.close()
        output.seek(0)
        self.excel_sheet = base64.b64encode(output.read())
        self.excel_sheet_name = str(self.excel_sheet_name) + '.xlsx'
        return {
            'type': 'ir.actions.act_url',
            'name': 'General Ledger Posting',
            'url': '/web/content/%s/%s/excel_sheet/%s?download=true' % (self._name, self.id, self.excel_sheet_name),
            'target': 'self'
        }

    def add_xlsx_sheet(self, report_data, workbook, STYLE_LINE_Data, header_format):
        self.ensure_one()
        worksheet = workbook.add_worksheet(_('IFRS16 GL Output file'))
        lang = self.env.user.lang
        if lang.startswith('ar_'):
            worksheet.right_to_left()

        row = 0
        col = 0
        worksheet.merge_range(row , row, col, col + 10, _('General Ledger postings'), STYLE_LINE_Data)
        worksheet.merge_range('L1:P1', _('Interface technical fields'), STYLE_LINE_Data)

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
        # col += 1
        # worksheet.write(row, col, _('Accounting Period End Date'), header_format)
        # col += 1
        # worksheet.write(row, col, _('Line No.'), header_format)
        col += 1
        worksheet.write(row, col, _('Download Date and Time'), header_format)
        col += 1
        worksheet.write(row, col, _('Debit'), header_format)
        col += 1
        worksheet.write(row, col, _('Credit'), header_format)

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
            # col += 1
            # worksheet.write(row, col, line['accounting_period_end_date'], STYLE_LINE_Data)
            # col += 1
            # worksheet.write(row, col, line['line_no'], STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['download_datetime'], STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['debit'], STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['credit'], STYLE_LINE_Data)





