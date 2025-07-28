# -*- coding: utf-8 -*-
import re
import base64
import io
import datetime
from datetime import timedelta
import xlsxwriter
import calendar
from dateutil.relativedelta import relativedelta
from collections import defaultdict
from odoo import  _, api, fields, models
from odoo.exceptions import UserError


class MonthlyCashBurn(models.Model):
    """ Class for Cash Burn Monthly Report xlsx """
    _name = 'monthly.cash.burn'
    _description = 'Monthly Cash Burn'

    @api.model
    def _get_year_selection(self):
        """Generate year options dynamically"""
        current_year = datetime.datetime.today().year
        years = []

        for year in range(current_year, current_year - 11, -1):
            years.append((str(year), f'{year}'))

        return years

    year = fields.Selection(
        selection='_get_year_selection',
        string='Fiscal Year',
        default=lambda self: str(datetime.datetime.today().year),
        help='Select the fiscal year',
        required=True
    )

    company_id = fields.Many2one('res.company', 'Company',
                                 default=lambda self: self.env.company,
                                 required=True)
    excel_sheet = fields.Binary('Download Report')
    excel_sheet_name = fields.Char(string='Name', size=64)

    def clean_ref(self, ref):
        return re.sub(r'\s*\(.*?\)\s*', '', ref).strip()

    def print_report_xlsx(self):
        """ Method for print Cash Burn xlsx report"""
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

        if report_data:
            self.add_xlsx_sheet(report_data, workbook, STYLE_LINE_Data,
                                header_format, STYLE_LINE_HEADER, date_format)

        self.excel_sheet_name = 'Tasc Cash Burn Monthly Report'
        workbook.close()
        output.seek(0)
        self.excel_sheet = base64.b64encode(output.read())
        self.excel_sheet_name = str(self.excel_sheet_name) + '.xlsx'
        return {
            'type': 'ir.actions.act_url',
            'name': 'Tasc Cash Burn Monthly Report',
            'url': '/web/content/%s/%s/excel_sheet/%s?download=true' % (
                self._name, self.id, self.excel_sheet_name),
            'target': 'new'
        }

    def get_report_data(self):
        """Method to compute Tasc Cash Burn Monthly Report."""
        start_date = datetime.date(int(self.year),1,1)
        end_date = datetime.date(int(self.year),12,31)

        move_line_ids = self.env['account.move.line'].search(
            [('date', '>=', start_date),
             ('date', '<=', end_date),
             ('company_id', '=', self.company_id.id),
             ('account_id.code_num', '>=', '111101'),
             ('account_id.code_num', '<=', '111201'),
             ('move_id.state', '!=', 'cancel')]).mapped('move_id')
        move_line_ids = list(set(move_line_ids))
        return move_line_ids

    def prepare_monthly_cf_data(self,data, year):
        """Method to prepare monthly data"""
        grouped = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
        totals = defaultdict(lambda: defaultdict(float))  # YTD totals

        for item in data:
            date = item['date']
            if not date or date.year != year:
                continue

            cf = item.get('cf') or 'Uncategorized'
            account = item['account_id']
            month = date.month

            grouped[cf][account][month] += item['balance']
            totals[cf][account] += item['balance']

        return grouped, totals

    def add_row(self, worksheet,header_format ,STYLE_LINE_Data,STYLE_LINE_HEADER,data_for_xlsx):
        worksheet.write(1, 0, "Account", header_format)
        col = 1
        row = 1
        for month in calendar.month_abbr[1:13]:
            worksheet.write(row, col, f"{month}", header_format)
            col += 1
        worksheet.write(1, col, "YTD", header_format)
        row += 2
        year = int(self.year)
        col = 0
        worksheet.write(row, col, "Opening Balance", header_format)
        col += 1

        init_ytd = 0
        opening_balance_accounts = self.env['account.account'].search([('cf','=','Bank')])
        ending_balance_totals = defaultdict(float)

        for i in range(1, 13):
            end_dt = datetime.date(year, i, 1) - relativedelta(days=1)
            domain_initial = [
                ('account_id', 'in', opening_balance_accounts.ids),
                ('date', '<=', end_dt),
                ('parent_state','!=','cancel'),
                ('company_id','=',self.company_id.id)
            ]
            initial_group_data = self.env['account.move.line']._read_group(
                domain_initial,
                aggregates=['balance:sum'],
            )
            init_ytd += initial_group_data[0][0]
            ending_balance_totals[
                i] += initial_group_data[0][0]
            worksheet.write(row, col, initial_group_data[0][0],
                            STYLE_LINE_Data)
            col += 1

        worksheet.write(row, col, init_ytd, STYLE_LINE_Data)
        row += 2
        grouped, totals = self.prepare_monthly_cf_data(data_for_xlsx, int(self.year))
        # Write data by CF group
        # Initialize grand monthly totals outside the loop
        grand_monthly_totals = defaultdict(float)

        for cf_group, account_data in grouped.items():
            worksheet.write(row, 0, cf_group, header_format)
            row += 1

            for account, monthly_data in account_data.items():
                worksheet.write(row, 0, f"{account.code} - {account.name}",
                                STYLE_LINE_Data)

                for i in range(1, 13):
                    value = monthly_data.get(i, 0.0)
                    worksheet.write_number(row, i, value, STYLE_LINE_Data)
                    grand_monthly_totals[
                        i] += value  # Accumulate in grand total
                    ending_balance_totals[
                        i] += value

                # YTD total for the account (optional)
                worksheet.write_number(row, 13, totals[cf_group][account],
                                       STYLE_LINE_Data)
                row += 1

            # Optional: Add a blank row between CF groups
            row += 1

        # Write final grand monthly totals row
        worksheet.write(row, 0, "Total", header_format)
        monthly_total_ytd = 0
        col = 1
        for i in range(1, 13):
            monthly_total_ytd += grand_monthly_totals[i]
            worksheet.write_number(row, i, grand_monthly_totals[i],
                                   STYLE_LINE_Data)
            col +=1

        worksheet.write_number(row, col, monthly_total_ytd,
                               STYLE_LINE_Data)
        row += 2  # Final row position if needed
        col = 0
        worksheet.write(row, col, "Ending Balance", header_format)
        col += 1
        ending_total_ytd = 0
        for i in range(1, 13):
            ending_total_ytd += ending_balance_totals[i]
            worksheet.write_number(row, i, ending_balance_totals[i],
                                   STYLE_LINE_Data)
            col += 1

        worksheet.write_number(row, col, ending_total_ytd,
                               STYLE_LINE_Data)


    def extract_amount(self,amount_str):
        parts = amount_str.split('\xa0')
        for part in parts:
            try:
                return float(part.replace(',', '').strip())
            except ValueError:
                continue
        raise ValueError(f"Could not extract numeric amount from: {amount_str}")

    def add_xlsx_sheet(self, report_data, workbook, STYLE_LINE_Data,
                       header_format, STYLE_LINE_HEADER, date_format):
        """ Method to add datas to the Tasc Cash Burn xlsx report"""
        self.ensure_one()
        worksheet = workbook.add_worksheet(_('Tasc Cash Burn Monthly Report'))
        lang = self.env.user.lang
        if lang.startswith('ar_'):
            worksheet.right_to_left()

        row = 0
        col = 0
        worksheet.merge_range(row, row, col, col + 13,
                              _('Tasc Cash Burn Monthly Report'),
                              STYLE_LINE_HEADER)

        data_for_xlsx = []
        for line in report_data:

            if line.payment_id:
                bank_account_line = line.line_ids.filtered(
                    lambda x: x.account_id.account_type == 'asset_current')
                if len(bank_account_line) > 1:
                    bank_account_line = bank_account_line.filtered(
                        lambda x: 'Bank Clearing' in x.account_id.name)

                if line.payment_id.reconciled_bill_ids or line.payment_id.reconciled_invoice_ids:
                    if line.payment_id.reconciled_bill_ids:
                        for rec in line.payment_id.reconciled_bill_ids:
                            s = rec.invoice_payments_widget
                            total = sum(rec.invoice_line_ids.mapped('price_total'))
                            company_currency_amount = next(
                                (self.extract_amount(item['amount_company_currency']) for item in s['content'] if
                                 item['amount_company_currency'] and self.clean_ref(
                                     item['ref']) == self.clean_ref(line.payment_id.name)),
                                0)
                            amount = next(
                                (item['amount'] for item in
                                 s['content'] if
                                 item['amount'] and self.clean_ref(
                                     item['ref']) == self.clean_ref(
                                     line.payment_id.name)),
                                0)
                            for item in rec.invoice_line_ids:
                                proportion = item.price_total / total
                                inv_amount = round(amount * proportion,rec.currency_id.decimal_places)
                                final_amount = round(company_currency_amount* proportion, rec.company_id.currency_id.decimal_places)
                                if bank_account_line.debit:
                                    debit_amount = final_amount
                                    credit_amount = 0.0
                                else:
                                    credit_amount = final_amount
                                    debit_amount = 0.0
                                data_for_xlsx.append({
                                    'date':line.date,
                                    'account_id':item.account_id,
                                    'cf': item.account_id.cf,
                                    'balance':abs(credit_amount)-abs(debit_amount)
                                })
                                row += 1
                            exchange_entries = [item for
                                                item in
                                                s["content"]
                                                if item[
                                                    'is_exchange']]
                            if exchange_entries:
                                for exch in exchange_entries:
                                    exch_move_id = self.env[
                                        'account.move'].browse(
                                        exch["move_id"])
                                    exch_line = exch_move_id.line_ids.filtered(lambda
                                                                              x: x.account_id.account_type not in [
                                        'asset_receivable',
                                        'liability_payable'])
                                    if len(exch_line.ids) > 1:
                                        for exc in exch_line:
                                            if bank_account_line.debit:
                                                debit_amount = exch["amount"]
                                                credit_amount = 0
                                            else:
                                                debit_amount = 0
                                                credit_amount = exch["amount"]
                                            data_for_xlsx.append({
                                                'date': line.date,
                                                'account_id': exc.account_id,
                                                'cf': exc.account_id.cf,
                                                'balance': abs(
                                                    credit_amount) - abs(
                                                    debit_amount)
                                            })
                                            row += 1
                                    else:
                                        if bank_account_line.debit:
                                            debit_amount=exch["amount"]
                                            credit_amount=0
                                        else:
                                            debit_amount = 0
                                            credit_amount = exch["amount"]
                                        data_for_xlsx.append({
                                            'date': line.date,
                                            'account_id': exch_line.account_id,
                                            'cf': exch_line.account_id.cf,
                                            'balance': abs(
                                                credit_amount) - abs(
                                                debit_amount)
                                        })
                                        row += 1
                    else:
                        for rec in line.payment_id.reconciled_invoice_ids:
                            s = rec.invoice_payments_widget
                            total = sum(
                                rec.invoice_line_ids.mapped('price_total'))
                            company_currency_amount = next(
                                (self.extract_amount(item['amount_company_currency']) for item in
                                 s['content'] if
                                 item[
                                     'amount_company_currency'] and self.clean_ref(
                                     item['ref']) == self.clean_ref(
                                     line.payment_id.name)),
                                0)
                            amount = next(
                                (item['amount'] for item in
                                 s['content'] if
                                 item['amount'] and self.clean_ref(
                                     item['ref']) == self.clean_ref(
                                     line.payment_id.name)),
                                0)

                            for item in rec.invoice_line_ids:
                                proportion = item.price_total / total
                                # inv_amount = round(amount * proportion,
                                #                    rec.currency_id.decimal_places)
                                final_amount = round(
                                    company_currency_amount * proportion,
                                    rec.company_id.currency_id.decimal_places)

                                if bank_account_line.debit:
                                    debit_amount =final_amount
                                    credit_amount = 0.0
                                else:
                                    credit_amount = final_amount
                                    debit_amount = 0.0
                                data_for_xlsx.append({
                                    'date': line.date,
                                    'account_id': item.account_id,
                                    'cf': item.account_id.cf,
                                    'balance': abs(credit_amount) - abs(
                                        debit_amount)
                                })
                                row += 1
                        exchange_entries = [item for
                                            item in
                                            s["content"]
                                            if item[
                                                'is_exchange']]
                        if exchange_entries:
                            for exch in exchange_entries:
                                exch_move_id = self.env[
                                    'account.move'].browse(
                                    exch["move_id"])
                                exch_line = exch_move_id.line_ids.filtered(
                                    lambda
                                        x: x.account_id.account_type not in [
                                        'asset_receivable',
                                        'liability_payable'])
                                if len(exch_line.ids) >1:
                                    for exc in exch_line:
                                        if bank_account_line.debit:
                                            debit_amount = exch["amount"]
                                            credit_amount = 0
                                        else:
                                            debit_amount = 0
                                            credit_amount = exch["amount"]
                                        data_for_xlsx.append({
                                            'date': line.date,
                                            'account_id': exc.account_id,
                                            'cf': exc.account_id.cf,
                                            'balance': abs(
                                                credit_amount) - abs(
                                                debit_amount)
                                        })
                                        row += 1
                                else:
                                    if bank_account_line.debit:
                                        debit_amount = exch["amount"]
                                        credit_amount = 0
                                    else:
                                        debit_amount = 0
                                        credit_amount = exch["amount"]
                                    data_for_xlsx.append({
                                        'date': line.date,
                                        'account_id': exch_line.account_id,
                                        'cf': exch_line.account_id.cf,
                                        'balance': abs(credit_amount) - abs(
                                            debit_amount)
                                    })
                                    row += 1
                    if line.payment_id.reconciled_statement_line_ids:
                        reconciled_entry =line.payment_id.reconciled_statement_line_ids.mapped('move_id')
                        # bank_line = reconciled_entry.line_ids.filtered(
                        # lambda x: x.account_id.account_type == 'asset_cash')
                        clearing_account_line = reconciled_entry.line_ids.filtered(
                        lambda x: x.account_id.account_type != 'asset_cash')
                        for l in clearing_account_line:
                            data_for_xlsx.append({
                                'date': reconciled_entry.date,
                                'account_id': l.account_id,
                                'cf': l.account_id.cf,
                                'balance': abs(l.credit) - abs(
                                    l.debit)
                            })
                            row += 1
                else:
                    if line.payment_id.purchase_order_id:
                        purchase_id = line.payment_id.purchase_order_id
                        total_price = sum(
                            purchase_id.order_line.mapped(
                                'price_total'))
                        for order_line in purchase_id.order_line:
                            proportion = order_line.price_total / total_price
                            order_line_amount = line.payment_id.amount * proportion
                            amount =order_line_amount
                            exchange_rate =0
                            if purchase_id.currency_id.id != purchase_id.company_id.currency_id.id:
                                company_value = purchase_id.company_id.currency_id._convert(order_line.price_total, purchase_id.currency_id,
                                                                          order_line.order_id.company_id,
                                                                          order_line.order_id.date_order)
                                exchange_rate = company_value / order_line.price_total
                                amount = purchase_id.company_id.currency_id.round(
                                    exchange_rate * amount)

                            payble_account_line = line.line_ids.filtered(
                                lambda
                                    x: x.account_id.account_type != 'asset_current'
                                       or 'Bank Clearing' not in x.account_id.name)

                            credit_amount = 0
                            debit_amount = 0
                            if bank_account_line.credit:
                                credit_amount = amount
                                debit_amount = 0
                            else:
                                debit_amount = amount
                                credit_amount = 0
                            data_for_xlsx.append({
                                'date': line.date,
                                'account_id': order_line.sudo().product_id.property_account_expense_id if order_line.sudo().product_id.property_account_expense_id else payble_account_line.account_id,
                                'cf':  order_line.sudo().product_id.property_account_expense_id.cf if order_line.sudo().product_id.property_account_expense_id else payble_account_line.account_id.cf,
                                'balance': abs(credit_amount) - abs(
                                    debit_amount)
                            })
                            row += 1
                    else:
                        bank_acct_line = line.line_ids.filtered(
                            lambda x: x.account_id.account_type == 'asset_current')
                        if len(bank_acct_line) > 1:
                            bank_acct_line = bank_acct_line.filtered(
                                lambda x: 'Bank Clearing' in x.account_id.name)
                        payble_account_line = line.line_ids.filtered(
                            lambda x: x.account_id.account_type != 'asset_current' or  'Bank Clearing' not in x.account_id.name)
                        data_for_xlsx.append({
                            'date': line.date,
                            'account_id': payble_account_line.account_id,
                            'cf': payble_account_line.account_id.cf,
                            'balance': abs(bank_acct_line.credit) - abs(
                                bank_acct_line.debit)
                        })
                        row += 1
            else:
                exchange_moves = []
                bank_line_id = line.line_ids.filtered(
                    lambda x: x.account_id.account_type == 'asset_cash')
                open_balance_line_ids = self.env['account.move.line'].search(
                    [('id', 'in', line.line_ids.ids),
                     '|', ('name', 'ilike', 'Open balance'),
                     ('account_id.code', 'in', ['582201', '582202'])])
                reconcile_items = line.open_reconcile_view()
                move_line_ids = self.env['account.move.line'].search(
                    reconcile_items['domain']).filtered(
                    lambda x: x.move_id.journal_id.type in ['sale',
                                                            'purchase',
                                                            'general'])
                if move_line_ids:
                    move = move_line_ids.mapped('move_id')
                    if move:
                        for mv in move:
                            if mv.journal_id.type in ['sale',
                                                      'purchase'] and not mv.payment_id and mv.move_type != 'entry':
                                credit_amount = 0
                                debit_amount = 0
                                s = mv.invoice_payments_widget
                                move_line = self.env[
                                    'account.move.line'].search(
                                    [('id', 'in', mv.invoice_line_ids.ids)],
                                    order='id ASC')
                                total = sum(move_line.mapped('price_total'))
                                company_currency_amount = next(
                                    (self.extract_amount(item['amount_company_currency']) for item
                                    in
                                    s['content'] if
                                    item[
                                        'amount_company_currency'] and self.clean_ref(
                                        item['ref']) == self.clean_ref(
                                        line.name)),
                                    0)
                                amount = next(
                                    (item['amount'] for item in
                                     s['content'] if
                                     item['amount'] and self.clean_ref(
                                         item['ref']) == self.clean_ref(
                                         line.name)),
                                    0)
                                for ml in move_line:
                                    proportion = ml.price_total / total
                                    final_amount = round(company_currency_amount* proportion,mv.company_id.currency_id.decimal_places)
                                    if bank_line_id.credit:
                                        credit_amount = final_amount
                                    else:
                                        debit_amount = final_amount
                                    data_for_xlsx.append({
                                        'date': line.date,
                                        'account_id': ml.account_id,
                                        'cf': ml.account_id.cf,
                                        'balance': abs(
                                            credit_amount) - abs(
                                            debit_amount)
                                    })
                                    row += 1
                                if s:
                                    exchange_entries = [item for
                                                        item in
                                                        s["content"]
                                                        if item[
                                                            'is_exchange']]
                                    if exchange_entries:
                                        for exch in exchange_entries:
                                            move_id = self.env[
                                                'account.move'].browse(
                                                exch["move_id"])
                                            if move_id.id not in exchange_moves:
                                                exchange_moves.append((move_id.id))
                                                exch_line = move_id.line_ids.filtered(
                                                    lambda
                                                        x: x.account_id.account_type not in [
                                                        'asset_receivable',
                                                        'liability_payable'])
                                                if len(exch_line.ids)>1:
                                                    for exc in exch_line:
                                                        if bank_line_id.debit:
                                                            debit_amount = exch["amount"]
                                                            credit_amount = 0
                                                        else:
                                                            debit_amount = 0
                                                            credit_amount = exch["amount"]
                                                        data_for_xlsx.append({
                                                            'date': line.date,
                                                            'account_id': exc.account_id,
                                                            'cf': exc.account_id.cf,
                                                            'balance': abs(
                                                                credit_amount) - abs(
                                                                debit_amount)
                                                        })
                                                        row += 1
                                                else:
                                                    if bank_line_id.debit:
                                                        debit_amount = exch["amount"]
                                                        credit_amount = 0
                                                    else:
                                                        debit_amount = 0
                                                        credit_amount = exch["amount"]
                                                    data_for_xlsx.append({
                                                        'date': line.date,
                                                        'account_id': exch_line.account_id,
                                                        'cf': exch_line.account_id.cf,
                                                        'balance': abs(
                                                            credit_amount) - abs(
                                                            debit_amount)
                                                    })
                                                    row += 1
                            else:
                                if mv.payment_id:
                                    if mv.payment_id.reconciled_bill_ids or mv.payment_id.reconciled_invoice_ids:
                                        if mv.payment_id.reconciled_bill_ids:
                                            for m in mv.payment_id.reconciled_bill_ids:
                                                s = m.invoice_payments_widget
                                                col = 0
                                                credit_amount = 0
                                                debit_amount = 0
                                                move_line = self.env[
                                                    'account.move.line'].search(
                                                    [('id', 'in',
                                                      m.invoice_line_ids.ids)],
                                                    order='id ASC',
                                                )
                                                total = sum(
                                                    move_line.mapped(
                                                        'price_total'))
                                                company_currency_amount = next(
                                                    (self.extract_amount(item['amount_company_currency']) for item
                                                        in
                                                        s['content'] if
                                                        item[
                                                            'amount_company_currency'] and self.clean_ref(
                                                            item[
                                                                'ref']) == self.clean_ref(
                                                            mv.payment_id.name)),
                                                    0)
                                                amount = next(
                                                    (item['amount'] for item in
                                                     s['content'] if
                                                     item[
                                                         'amount'] and self.clean_ref(
                                                         item[
                                                             'ref']) == self.clean_ref(
                                                         mv.payment_id.name)),
                                                    0)
                                                for ml in move_line:
                                                    proportion = ml.price_total / total
                                                    line_payment = round(amount * proportion,m.currency_id.decimal_places)
                                                    final_amount = round(company_currency_amount * proportion,m.company_id.currency_id.decimal_places)

                                                    if bank_line_id.credit:
                                                        credit_amount = final_amount
                                                    else:
                                                        debit_amount = final_amount
                                                    data_for_xlsx.append({
                                                        'date': line.date,
                                                        'account_id': ml.account_id,
                                                        'cf': ml.account_id.cf,
                                                        'balance': abs(
                                                            credit_amount) - abs(
                                                            debit_amount)
                                                    })
                                                    row += 1
                                                if s:
                                                    exchange_entries = [item for
                                                                        item in
                                                                        s[
                                                                            "content"]
                                                                        if item[
                                                                            'is_exchange']
                                                                        ]
                                                    if exchange_entries:
                                                        for exch in exchange_entries:
                                                            move_id = self.env[
                                                                'account.move'].browse(
                                                                exch["move_id"])
                                                            if move_id.id not in exchange_moves:
                                                                exchange_moves.append(
                                                                    (
                                                                        move_id.id))
                                                                exch_line = move_id.line_ids.filtered(
                                                                    lambda
                                                                        x: x.account_id.account_type not in [
                                                                        'asset_receivable',
                                                                        'liability_payable'])
                                                                if len(exch_line.ids)>1:
                                                                    for exc in exch_line:
                                                                        if bank_line_id.credit:
                                                                            debit_amount = 0
                                                                            credit_amount = \
                                                                                exch[
                                                                                    "amount"]
                                                                        else:
                                                                            debit_amount = \
                                                                                exch[
                                                                                    "amount"]
                                                                            credit_amount = 0
                                                                        data_for_xlsx.append(
                                                                            {
                                                                                'date': line.date,
                                                                                'account_id': exc.account_id,
                                                                                'cf': exc.account_id.cf,
                                                                                'balance': abs(
                                                                                    credit_amount) - abs(
                                                                                    debit_amount)
                                                                            })
                                                                        row += 1
                                                                else:
                                                                    if bank_line_id.credit:
                                                                        debit_amount = 0
                                                                        credit_amount = \
                                                                            exch[
                                                                                "amount"]
                                                                    else:
                                                                        debit_amount = \
                                                                        exch[
                                                                            "amount"]
                                                                        credit_amount = 0
                                                                    data_for_xlsx.append(
                                                                        {
                                                                            'date': line.date,
                                                                            'account_id': exch_line.account_id,
                                                                            'cf': exch_line.account_id.cf,
                                                                            'balance': abs(
                                                                                credit_amount) - abs(
                                                                                debit_amount)
                                                                        })
                                                                    row += 1
                                        else:
                                            for m in mv.payment_id.reconciled_invoice_ids:
                                                s = m.invoice_payments_widget
                                                col = 0
                                                credit_amount = 0
                                                debit_amount = 0
                                                move_line = self.env[
                                                    'account.move.line'].search(
                                                    [('id', 'in',
                                                      m.invoice_line_ids.ids)],
                                                    order='id ASC',
                                                )
                                                total = sum(
                                                    move_line.mapped(
                                                        'price_total'))
                                                company_currency_amount = next(
                                                    (self.extract_amount(item['amount_company_currency']) for item
                                                        in
                                                        s['content'] if
                                                        item[
                                                            'amount_company_currency'] and self.clean_ref(
                                                            item[
                                                                'ref']) == self.clean_ref(
                                                            mv.payment_id.name)),
                                                    0)
                                                amount = next(
                                                    (item['amount'] for item in
                                                     s['content'] if
                                                     item[
                                                         'amount'] and self.clean_ref(
                                                         item[
                                                             'ref']) == self.clean_ref(
                                                         mv.payment_id.name)),
                                                    0)
                                                for ml in move_line:
                                                    proportion = ml.price_total / total
                                                    line_payment = round(
                                                        amount * proportion,
                                                        m.currency_id.decimal_places)
                                                    final_amount = round(
                                                        company_currency_amount * proportion,
                                                        m.company_id.currency_id.decimal_places)
                                                    if bank_line_id.credit:
                                                        invoice_amount = line_payment
                                                        credit_amount = final_amount
                                                    else:
                                                        invoice_amount = line_payment
                                                        debit_amount = final_amount
                                                    data_for_xlsx.append({
                                                        'date': line.date,
                                                        'account_id': ml.account_id,
                                                        'cf': ml.account_id.cf,
                                                        'balance': abs(
                                                            credit_amount) - abs(
                                                            debit_amount)
                                                    })
                                                    row += 1
                                                if s:
                                                    exchange_entries = [item for
                                                                        item in
                                                                        s[
                                                                            "content"]
                                                                        if item[
                                                                            'is_exchange']]
                                                    if exchange_entries:
                                                        for exch in exchange_entries:
                                                            move_id = self.env[
                                                                'account.move'].browse(
                                                                exch["move_id"])
                                                            if move_id.id not in exchange_moves:
                                                                exchange_moves.append(
                                                                    (
                                                                        move_id.id))
                                                                exch_line = move_id.line_ids.filtered(
                                                                    lambda
                                                                        x: x.account_id.account_type not in [
                                                                        'asset_receivable',
                                                                        'liability_payable'])
                                                                if len(exch_line.ids) > 1:
                                                                    for exc  in exch_line:
                                                                        if bank_line_id.credit:
                                                                            debit_amount = 0
                                                                            credit_amount = \
                                                                                exch[
                                                                                    "amount"]
                                                                        else:
                                                                            debit_amount = \
                                                                                exch[
                                                                                    "amount"]
                                                                            credit_amount = 0
                                                                        data_for_xlsx.append(
                                                                            {
                                                                                'date': line.date,
                                                                                'account_id': exc.account_id,
                                                                                'cf': exc.account_id.cf,
                                                                                'balance': abs(
                                                                                    credit_amount) - abs(
                                                                                    debit_amount)
                                                                            })
                                                                else:
                                                                    if bank_line_id.credit:
                                                                        debit_amount = 0
                                                                        credit_amount = \
                                                                            exch[
                                                                                "amount"]
                                                                    else:
                                                                        debit_amount = \
                                                                        exch[
                                                                            "amount"]
                                                                        credit_amount = 0
                                                                    data_for_xlsx.append(
                                                                        {
                                                                            'date': line.date,
                                                                            'account_id': exch_line.account_id,
                                                                            'cf': exch_line.account_id.cf,
                                                                            'balance': abs(
                                                                                credit_amount) - abs(
                                                                                debit_amount)
                                                                        })
                                                                    row += 1
                                    else:
                                        if mv.payment_id.purchase_order_id:
                                            total_price = sum(
                                                mv.payment_id.purchase_order_id.order_line.mapped(
                                                    'price_total'))
                                            for order_line in mv.payment_id.purchase_order_id.order_line:
                                                proportion = order_line.price_total / total_price
                                                order_line_amount = mv.payment_id.amount * proportion
                                                col = 0
                                                credit_amount = 0
                                                debit_amount = 0
                                                if purchase_id.currency_id.id != purchase_id.company_id.currency_id.id:
                                                    company_value = purchase_id.company_id.currency_id._convert(
                                                        order_line.price_total, purchase_id.currency_id,
                                                        order_line.order_id.company_id,
                                                        order_line.order_id.date_order)
                                                    exchange_rate = company_value / order_line.price_total
                                                    amount = purchase_id.company_id.currency_id.round(
                                                        exchange_rate * amount)

                                                payble_account_line = line.line_ids.filtered(
                                                    lambda
                                                        x: x.account_id.account_type != 'asset_current' or 'Bank Clearing' not in x.account_id.name)

                                                bank_acct_line = line.line_ids.filtered(
                                                    lambda
                                                        x: x.account_id.account_type == 'asset_current')
                                                if len(bank_acct_line) > 1:
                                                    bank_acct_line = bank_acct_line.filtered(
                                                        lambda x: 'Bank Clearing' in x.account_id.name)
                                                credit_amount = 0
                                                debit_amount = 0
                                                if bank_account_line.credit:
                                                    credit_amount = amount
                                                    debit_amount = 0
                                                else:
                                                    debit_amount = amount
                                                    credit_amount = 0
                                                data_for_xlsx.append({
                                                    'date': line.date,
                                                    'account_id': order_line.sudo().product_id.property_account_expense_id if order_line.sudo().product_id.property_account_expense_id else payble_account_line.account_id,
                                                    'cf': order_line.sudo().product_id.property_account_expense_id.cf if order_line.sudo().product_id.property_account_expense_id else payble_account_line.account_id.cf,
                                                    'balance': abs(
                                                        credit_amount) - abs(
                                                        debit_amount)
                                                })
                                                row += 1
                                        else:
                                            bank_acct_line = line.line_ids.filtered(
                                                lambda
                                                    x: x.account_id.account_type == 'asset_current')
                                            if len(bank_acct_line) > 1:
                                                bank_acct_line = bank_acct_line.filtered(
                                                    lambda x: 'Bank Clearing' in x.account_id.name)
                                            payble_account_line = line.line_ids.filtered(
                                                lambda
                                                    x: x.account_id.account_type != 'asset_current'
                                                       or 'Bank Clearing' not in x.account_id.name)
                                            data_for_xlsx.append({
                                                'date': line.date,
                                                'account_id': payble_account_line.account_id,
                                                'cf': payble_account_line.account_id.cf,
                                                'balance': abs(
                                                    bank_acct_line.credit) - abs(
                                                    bank_acct_line.debit)
                                            })
                                            row += 1
                                else:
                                    if mv.id not in exchange_moves:
                                        exchange_moves.append(
                                            (mv.id))
                                        credit_amount = 0
                                        debit_amount = 0
                                        amt = 0
                                        exch_line = mv.line_ids.filtered(
                                            lambda x: x.account_id.account_type not in [
                                                'asset_receivable',
                                                'liability_payable'])
                                        if len(exch_line.ids) > 1:
                                            for exc in exch_line:
                                                amt = exc.credit if exc.credit else exc.debit

                                                if bank_line_id.credit != 0:
                                                    credit_amount = amt
                                                else:
                                                    debit_amount = amt
                                                invoice_amount = 0
                                                data_for_xlsx.append({
                                                    'date': line.date,
                                                    'account_id': exc.account_id,
                                                    'cf': exc.account_id.cf,
                                                    'balance': abs(
                                                        credit_amount) - abs(
                                                        debit_amount)
                                                })
                                                row += 1

                                        else:
                                            amt = exch_line.credit if exch_line.credit else exch_line.debit

                                            if bank_line_id.credit !=0:
                                                credit_amount = amt
                                            else:
                                                debit_amount = amt
                                            invoice_amount = 0
                                            data_for_xlsx.append({
                                                'date': line.date,
                                                'account_id': exch_line.account_id,
                                                'cf': exch_line.account_id.cf,
                                                'balance': abs(
                                                    credit_amount) - abs(
                                                    debit_amount)
                                            })
                                            row += 1
                        if open_balance_line_ids:
                            for ob in open_balance_line_ids:
                                amount = ob.credit if ob.credit else ob.debit
                                if ob.credit:
                                    credit_amount = 0
                                    debit_amount = amount
                                    invoice_amount = 0
                                    data_for_xlsx.append({
                                        'date': line.date,
                                        'account_id': ob.account_id,
                                        'cf': ob.account_id.cf,
                                        'balance': abs(
                                            credit_amount) - abs(
                                            debit_amount)
                                    })
                                else:
                                    credit_amount = amount
                                    debit_amount = 0
                                    invoice_amount = 0
                                    data_for_xlsx.append({
                                        'date': line.date,
                                        'account_id': ob.account_id,
                                        'cf': ob.account_id.cf,
                                        'balance': abs(
                                            credit_amount) - abs(
                                            debit_amount)
                                    })

                                row += 1
                else:
                    clearing_lines = line.line_ids.filtered(
                        lambda x: x.account_id.account_type != 'asset_cash')
                    for l in clearing_lines:
                        data_for_xlsx.append({
                            'date': line.date,
                            'account_id': l.account_id,
                            'cf': l.account_id.cf,
                            'balance': abs(
                                l.credit) - abs(
                                l.debit)
                        })
                        row += 1
        self.add_row(worksheet, header_format, STYLE_LINE_Data, STYLE_LINE_HEADER,data_for_xlsx)


