# -*- coding: utf-8 -*-
""" init object """
import base64
import io
from odoo import fields, models, _
from datetime import datetime, date
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from dateutil.relativedelta import relativedelta
import calendar


try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    import xlsxwriter


class LeaseLiabilitySchedule(models.TransientModel):
    _name = 'lease.liability.schedule.wizard'
    _description = 'Lease Liability Schedule'

    def _get_date_from_now(self):
        today = datetime.now().today()
        first_day_this_month = date(day=1, month=today.month, year=today.year)
        return first_day_this_month

    def _get_date_to(self):
        # import calendar
        today = datetime.now().today()
        last_day = calendar.monthrange(today.year, today.month)
        last_day_this_month = date(day=last_day[1], month=today.month,
                                   year=today.year)
        return last_day_this_month

    date_from = fields.Date(string="Date From", default=_get_date_from_now,
                            required=False, )
    date_to = fields.Date(string="Date To", default=_get_date_to,
                          required=False, )
    contract_ids = fields.Many2many(comodel_name="leasee.contract",
                                    domain=[('parent_id', '=', False)])
    analytic_account_ids = fields.Many2many(
        comodel_name="account.analytic.account")
    partner_ids = fields.Many2many(comodel_name="res.partner", )
    excel_sheet = fields.Binary('Download Report')
    excel_sheet_name = fields.Char(string='Name', size=64)

    def get_report_data(self):
        data = []
        domain = [('date', '>=', self.date_from), ('date', '<=', self.date_to)]
        if self.contract_ids:
            # domain.append(('leasee_contract_id', 'in', self.contract_ids.ids))
            domain.append(
                ('leasee_contract_id', 'child_of', self.contract_ids.ids))
        elif self.analytic_account_ids:
            domain.append(('leasee_contract_id.analytic_account_id', 'in',
                           self.analytic_account_ids.ids))
        elif self.partner_ids:
            domain.append(
                ('leasee_contract_id.vendor_id', 'in', self.partner_ids.ids))
        installments = self.env['leasee.installment'].search(domain,
                                                             order='leasee_contract_id,date,period')
        period_closing = 0
        for contract1 in installments.mapped('leasee_contract_id'):
            period_contract = 0
            for installment in installments:
                if installment.id in contract1.mapped('installment_ids').ids:
                    contract = installment.leasee_contract_id
                    first_period = 0
                    period_no = installment.get_period_order()
                    opening_balance = installment.remaining_lease_liability - installment.subsequent_amount + installment.amount
                    closing_balance = installment.remaining_lease_liability
                    # closing_balance = opening_balance + installment.subsequent_amount - installment.amount
                    if installment.leasee_contract_id.payment_frequency_type == 'months':
                        delta = relativedelta(months=contract.payment_frequency)
                    else:
                        delta = relativedelta(years=contract.payment_frequency)
                    start_date = contract.commencement_date + (
                        period_no - 1 if period_no else 0) * delta
                    end_date = contract.commencement_date + (
                            period_no or 1) * delta + relativedelta(days=-1)
                    previous_installment = contract.installment_ids[
                                           1:].filtered(
                        lambda i: i.period < installment.period)[-1:]
                    reassessment = 0
                    if previous_installment:
                        reassessment = opening_balance - previous_installment.remaining_lease_liability
                        opening_balance = opening_balance - reassessment
                    reasses = 0
                    if round(installment.interest_amount, 0) > round(
                            installment.subsequent_amount, 0):
                        reasses = installment.leasee_contract_id.asset_id.gross_increase_value
                    opening_balance_lcy = self.env.company.currency_id._convert(
                        opening_balance,
                        installment.leasee_contract_id.leasee_currency_id,
                        self.env.company,
                        installment.date) if period_no != first_period else 0
                    initial_measurement = opening_balance if period_no == first_period else 0
                    interest = installment.interest_amount
                    remeasuring_lcy = round(reasses, 0)
                    payment = installment.amount
                    if installment.leasee_contract_id.termination_date:
                        if installment.date <= installment.leasee_contract_id.termination_date:
                            data.append({
                                'period_no': period_no,
                                'project_site': installment.leasee_contract_id.project_site_id.name,
                                'lease_no': installment.leasee_contract_id.name,
                                'period_start_date': start_date.strftime(DF),
                                'opening_balance': opening_balance if period_no != first_period else 0,
                                'opening_balance_lcy': opening_balance_lcy,
                                'initial_measurement': initial_measurement,
                                'interest': interest,
                                'interest_lcy': self.env.company.currency_id._convert(
                                    installment.interest_amount,
                                    installment.leasee_contract_id.leasee_currency_id,
                                    self.env.company,
                                    installment.date),
                                'payment': payment,
                                'remeasuring_lcy': remeasuring_lcy,
                                'closing_balance': closing_balance,
                                'closing_balance_lcy': self.env.company.currency_id._convert(
                                    closing_balance,
                                    installment.leasee_contract_id.leasee_currency_id,
                                    self.env.company,
                                    installment.date),
                                'period_end_date': end_date.strftime(DF),
                                'posted_to_gl': True if installment.installment_invoice_id.state == 'posted' else False,
                                'closing_new': (
                                                       opening_balance_lcy + initial_measurement + interest + remeasuring_lcy) - payment
                            })
                            period_contract = period_no
                            period_closing = (
                                                       opening_balance_lcy + initial_measurement + interest + remeasuring_lcy) - payment
                    else:
                        data.append({
                            'period_no': period_no,
                            'project_site': installment.leasee_contract_id.project_site_id.name,
                            'lease_no': installment.leasee_contract_id.name,
                            'period_start_date': start_date.strftime(DF),
                            'opening_balance': opening_balance if period_no != first_period else 0,
                            'opening_balance_lcy': opening_balance_lcy,
                            'initial_measurement': initial_measurement,
                            'interest': interest,
                            'interest_lcy': self.env.company.currency_id._convert(
                                installment.interest_amount,
                                installment.leasee_contract_id.leasee_currency_id,
                                self.env.company,
                                installment.date),
                            'payment': payment,
                            'remeasuring_lcy': remeasuring_lcy,
                            'closing_balance': closing_balance,
                            'closing_balance_lcy': self.env.company.currency_id._convert(
                                closing_balance,
                                installment.leasee_contract_id.leasee_currency_id,
                                self.env.company,
                                installment.date),
                            'period_end_date': end_date.strftime(DF),
                            'posted_to_gl': True if installment.installment_invoice_id.state == 'posted' else False,
                            'closing_new': (
                                                   opening_balance_lcy + initial_measurement + interest + remeasuring_lcy) - payment
                        })
            if contract1.termination_date:
                terminated_move = self.env['account.move'].search(
                    [('leasee_contract_id', '=', contract1.id),
                     ('ref', 'ilike', 'Disposal')])
                abc = terminated_move.line_ids.filtered(lambda x: x.account_id.id in [contract1.lease_liability_account_id.id, contract1.long_lease_liability_account_id.id])
                data.append({
                    'period_no': period_contract + 1,
                    'project_site': contract1.project_site_id.name,
                    'lease_no': contract1.name,
                    'period_start_date': contract1.termination_date.strftime(
                        DF),
                    'opening_balance': 0,
                    'opening_balance_lcy': 0,
                    'initial_measurement': 0,
                    'interest': 0,
                    'interest_lcy': abs(period_closing - sum(abc.mapped('debit'))),
                    'payment': 0,
                    'remeasuring_lcy': -abs(sum(abc.mapped('debit'))),
                    'closing_balance': 0,
                    'closing_balance_lcy': 0,
                    'period_end_date': 0,
                    'posted_to_gl': '',
                    'closing_new': 0
                })
            count = 0
            for i in range(1, len(data)):
                data[i]['opening_balance'] = data[count]['closing_new']
                count += 1
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
            self.add_xlsx_sheet(report_data, workbook, STYLE_LINE_Data,
                                header_format)

        self.excel_sheet_name = 'Lease Liability Schedule'
        workbook.close()
        output.seek(0)
        self.excel_sheet = base64.b64encode(output.read())
        self.excel_sheet_name = str(self.excel_sheet_name) + '.xlsx'
        return {
            'type': 'ir.actions.act_url',
            'name': 'Lease Liability Schedule',
            'url': '/web/content/%s/%s/excel_sheet/Lease Liability Schedule.xlsx?download=true' % (
                self._name, self.id),
            'target': 'self'
        }

    def add_xlsx_sheet(self, report_data, workbook, STYLE_LINE_Data,
                       header_format):
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
        worksheet.write(row, col, _('Project / Site'), header_format)
        col += 1
        worksheet.write(row, col, _('Period Start Date'), header_format)
        col += 1
        worksheet.write(row, col, _('Opening Balance (lease liability)'),
                        header_format)
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
        worksheet.write(row, col, _('Remeasuring / Reassessment (LCY) (+)'),
                        header_format)
        col += 1
        worksheet.write(row, col, _('Closing Balance'), header_format)
        col += 1
        worksheet.write(row, col, _('Closing Balance (LCY)'), header_format)
        col += 1
        worksheet.write(row, col, _('Period End Date'), header_format)
        col += 1
        worksheet.write(row, col, _('Posted to G/L'), header_format)
        col += 1
        worksheet.write(row, col, _('Closing New'), header_format)

        for line in report_data:
            col = 0
            row += 1
            worksheet.write(row, col, line['period_no'], STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['lease_no'], STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['project_site'], STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['period_start_date'],
                            STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['opening_balance'], STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['opening_balance_lcy'],
                            STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['initial_measurement'],
                            STYLE_LINE_Data)
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
            worksheet.write(row, col, line['closing_balance_lcy'],
                            STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['period_end_date'], STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['posted_to_gl'], STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['closing_new'], STYLE_LINE_Data)
