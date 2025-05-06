import re
import base64
import io
import datetime
import xlsxwriter
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class CashBurnReportGLWizard(models.Model):
    """ Class for Cash Burn GL Report xlsx """
    _name = 'cash.burn.report.gl.wizard'
    _description = 'Cash Burn GL Report'

    start_date = fields.Date(string="From Date",
                             default=datetime.datetime.now(), required=True)
    end_date = fields.Date(string="To Date",
                           default=datetime.datetime.now(), required=True)
    company_id = fields.Many2one('res.company', 'Company',
                                 default=lambda self: self.env.company,
                                 required=True)
    excel_sheet = fields.Binary('Download Report')
    excel_sheet_name = fields.Char(string='Name', size=64)

    def clean_ref(self, ref):
        return re.sub(r'\s*\(.*?\)\s*', '', ref).strip()

    @api.constrains('end_date')
    def onsave_end_date(self):
        if self.end_date < self.start_date:
            raise UserError(
                "The end date should be greater than or equal to start date.")

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

        self.excel_sheet_name = 'Tasc Cash Burn GL Report'
        workbook.close()
        output.seek(0)
        self.excel_sheet = base64.b64encode(output.read())
        self.excel_sheet_name = str(self.excel_sheet_name) + '.xlsx'
        return {
            'type': 'ir.actions.act_url',
            'name': 'Tasc Cash Burn GL Report',
            'url': '/web/content/%s/%s/excel_sheet/%s?download=true' % (
                self._name, self.id, self.excel_sheet_name),
            'target': 'new'
        }

    def get_report_data(self):
        """Method to compute Tasc Cash Burn GL Report."""
        move_line_ids = self.env['account.move.line'].search(
            [('date', '>=', self.start_date),
             ('date', '<=', self.end_date),
             ('company_id', '=', self.company_id.id),
             ('account_id.code_num', '>=', '111101'),
             ('account_id.code_num', '<=', '111201'),
             ('move_id.state', '!=', 'cancel')]).mapped('move_id')
        move_line_ids = list(set(move_line_ids))
        return move_line_ids

    def add_row(self, worksheet, row, STYLE_LINE_Data, date_format, date,
                number, reference,
                bill_no, label,
                journal,
                cc,
                project_site,
                invoice_account,
                bank_account,
                partner,
                currency,
                invoice_amount,
                debit,
                credit):
        col = 0
        worksheet.write(row, col, date if date else '',
                        date_format)
        col += 1
        worksheet.write(row, col, number if number else '',
                        STYLE_LINE_Data)
        col += 1
        worksheet.write(row, col, reference if reference else '',
                        STYLE_LINE_Data)
        col += 1
        worksheet.write(row, col, bill_no if bill_no else '',
                        STYLE_LINE_Data)
        col += 1
        worksheet.write(row, col, label if label else '',
                        STYLE_LINE_Data)
        col += 1
        worksheet.write(row, col, journal.name if journal else '',
                        STYLE_LINE_Data)
        col += 1
        if cc.name and cc.code:
            worksheet.write(row, col,
                            cc.code + "-" + cc.name,
                            STYLE_LINE_Data)
        elif cc.name:
            worksheet.write(row, col,
                            cc.name,
                            STYLE_LINE_Data)
        else:
            worksheet.write(row, col,
                            '',
                            STYLE_LINE_Data)
        col += 1
        if project_site.name and project_site.code:
            worksheet.write(row, col,
                            project_site.code + "-" + project_site.name,
                            STYLE_LINE_Data)
        elif cc.name:
            worksheet.write(row, col,
                            project_site.name,
                            STYLE_LINE_Data)
        else:
            worksheet.write(row, col,
                            '',
                            STYLE_LINE_Data)
        col += 1
        if invoice_account.name and invoice_account.code:
            worksheet.write(row, col,
                            invoice_account.code + "-" + invoice_account.name,
                            STYLE_LINE_Data)
        elif cc.name:
            worksheet.write(row, col,
                            invoice_account.name,
                            STYLE_LINE_Data)
        else:
            worksheet.write(row, col,
                            '',
                            STYLE_LINE_Data)
        col += 1

        if bank_account and len(bank_account.ids)>=1:
            bank_account_details = ", ".join(
                f"{getattr(account, 'code', '')} - {getattr(account, 'name', '')}"
                for account in bank_account
            )
            worksheet.write(row, col,
                            bank_account_details,
                            STYLE_LINE_Data)
        else:
            worksheet.write(row, col,
                            '',
                            STYLE_LINE_Data)
        col += 1
        worksheet.write(row, col, partner.name if partner else '',
                        STYLE_LINE_Data)
        col += 1
        worksheet.write(row, col, currency.name if currency else '',
                        STYLE_LINE_Data)
        col += 1
        worksheet.write(row, col, invoice_amount,
                        STYLE_LINE_Data)
        col += 1
        worksheet.write(row, col,
                        debit if debit else 0.0,
                        STYLE_LINE_Data)
        col += 1
        worksheet.write(row, col,
                        credit if credit else 0.0,
                        STYLE_LINE_Data)
        col += 1
        net = abs(credit) - abs(debit)
        worksheet.write(row, col,
                        net,
                        STYLE_LINE_Data)
        accountable_net = net
        col += 1
        worksheet.write(row, col,
                        accountable_net,
                        STYLE_LINE_Data)


    def add_xlsx_sheet(self, report_data, workbook, STYLE_LINE_Data,
                       header_format, STYLE_LINE_HEADER, date_format):
        """ Method to add datas to the Tasc Cash Burn xlsx report"""
        self.ensure_one()
        worksheet = workbook.add_worksheet(_('Tasc Cash Burn GL Report'))
        lang = self.env.user.lang
        if lang.startswith('ar_'):
            worksheet.right_to_left()

        row = 0
        col = 0
        worksheet.merge_range(row, row, col, col + 16,
                              _('Tasc Cash Burn GL Report'),
                              STYLE_LINE_HEADER)
        row += 1
        col = 0
        worksheet.write(row, col, _('Date'), header_format)
        col += 1
        worksheet.write(row, col, _('Number'), header_format)
        col += 1
        worksheet.write(row, col, _('Reference'), header_format)
        col += 1
        worksheet.write(row, col, _('Invoice lines/label'), header_format)
        col += 1
        worksheet.write(row, col, _('Bill No.'), header_format)
        col += 1
        worksheet.write(row, col, _('Journal'), header_format)
        col += 1
        worksheet.write(row, col, _('Cost Center'), header_format)
        col += 1
        worksheet.write(row, col, _('Project'), header_format)
        col += 1
        worksheet.write(row, col, _('Invoice lines/Account'), header_format)
        col += 1
        worksheet.write(row, col, _('Bank Account'), header_format)
        col += 1
        worksheet.write(row, col, _('Partner'), header_format)
        col += 1
        worksheet.write(row, col, _('Payment Currency'), header_format)
        col += 1
        worksheet.write(row, col, _('Invoice Amount'), header_format)
        col += 1
        worksheet.write(row, col, _('Invoice lines/Debit'), header_format)
        col += 1
        worksheet.write(row, col, _('Invoice lines/Credit'), header_format)
        col += 1
        worksheet.write(row, col, _('Net'), header_format)
        col += 1
        worksheet.write(row, col, _('Accounted Net'), header_format)
        col += 1
        row += 1
        for line in report_data:
            print("lineeeeeeee",line)

            if line.payment_id:
                bank_account_line = line.line_ids.filtered(
                    lambda x: x.account_id.account_type == 'asset_current')
                print("bank_account_line",bank_account_line)
                if len(bank_account_line) > 1:
                    bank_account_line = bank_account_line.filtered(
                        lambda x: 'Bank Clearing' in x.account_id.name)

                if line.payment_id.reconciled_bill_ids or line.payment_id.reconciled_invoice_ids:
                    if line.payment_id.reconciled_bill_ids:
                        for rec in line.payment_id.reconciled_bill_ids:
                            s = rec.invoice_payments_widget
                            total = sum(rec.invoice_line_ids.mapped('price_total'))
                            company_currency_amount = next(
                                (float(item['amount_company_currency'].split('\xa0')[-1].replace(',', '')) for item in s['content'] if
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
                                print("bank_account_line",bank_account_line)
                                if bank_account_line.debit:
                                    debit_amount = final_amount
                                    credit_amount = 0.0
                                else:
                                    credit_amount = final_amount
                                    debit_amount = 0.0

                                self.add_row(worksheet, row,
                                             STYLE_LINE_Data, date_format,
                                             line.date, line.name, rec.ref,
                                              item.name,rec.name,
                                             line.journal_id,
                                             item.analytic_account_id,
                                             item.project_site_id,
                                             item.account_id,
                                             bank_account_line.account_id,
                                             rec.partner_id,
                                             rec.currency_id,
                                             inv_amount,
                                             debit_amount,
                                             credit_amount
                                             )
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
                                    print("bank_account_line1", bank_account_line)

                                    if bank_account_line.debit:
                                        debit_amount=exch["amount"]
                                        credit_amount=0
                                    else:
                                        debit_amount = 0
                                        credit_amount = exch["amount"]
                                    self.add_row(worksheet, row,
                                                 STYLE_LINE_Data, date_format,
                                                 line.date, line.name, exch_move_id.ref,
                                                 exch_line.name, exch_move_id.name,
                                                 line.journal_id,
                                                 exch_line.analytic_account_id,
                                                 exch_line.project_site_id,
                                                 exch_line.account_id,
                                                 bank_account_line.account_id,
                                                 exch_move_id.partner_id,
                                                 exch_move_id.currency_id,
                                                 exch["amount"],
                                                 debit_amount,
                                                 credit_amount
                                                 )
                                    row += 1
                    else:
                        for rec in line.payment_id.reconciled_invoice_ids:
                            s = rec.invoice_payments_widget
                            total = sum(
                                rec.invoice_line_ids.mapped('price_total'))
                            company_currency_amount = next(
                                (float(item['amount_company_currency'].split(
                                    '\xa0')[-1].replace(',', '')) for item in
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
                                inv_amount = round(amount * proportion,
                                                   rec.currency_id.decimal_places)
                                final_amount = round(
                                    company_currency_amount * proportion,
                                    rec.company_id.currency_id.decimal_places)
                                print("bank_account_line3",bank_account_line)

                                if bank_account_line.debit:
                                    debit_amount =final_amount
                                    credit_amount = 0.0
                                else:
                                    credit_amount = final_amount
                                    debit_amount = 0.0
                                self.add_row(worksheet, row,
                                             STYLE_LINE_Data, date_format,
                                             line.date, line.name, rec.ref,
                                             item.name, rec.name,
                                             line.journal_id,
                                             item.analytic_account_id,
                                             item.project_site_id,
                                             item.account_id,
                                             bank_account_line.account_id,
                                             rec.partner_id,
                                             rec.currency_id,
                                             inv_amount,
                                             debit_amount,
                                             credit_amount
                                             )
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
                                print("bank_account_line4",bank_account_line)

                                if bank_account_line.debit:
                                    debit_amount = exch["amount"]
                                    credit_amount = 0
                                else:
                                    debit_amount = 0
                                    credit_amount = exch["amount"]
                                self.add_row(worksheet, row,
                                             STYLE_LINE_Data, date_format,
                                             line.date, line.name,
                                             exch_move_id.ref,
                                             exch_line.name, exch_move_id.name,
                                             line.journal_id,
                                             exch_line.analytic_account_id,
                                             exch_line.project_site_id,
                                             exch_line.account_id,
                                             bank_account_line.account_id,
                                             exch_move_id.partner_id,
                                             exch_move_id.currency_id,
                                             exch["amount"],
                                             debit_amount,
                                             credit_amount
                                             )
                                row += 1
                    if line.payment_id.reconciled_statement_line_ids:
                        reconciled_entry =line.payment_id.reconciled_statement_line_ids.mapped('move_id')
                        bank_line = reconciled_entry.line_ids.filtered(
                        lambda x: x.account_id.account_type == 'asset_cash')
                        clearing_account_line = reconciled_entry.line_ids.filtered(
                        lambda x: x.account_id.account_type != 'asset_cash')
                        for l in clearing_account_line:
                            self.add_row(worksheet, row,
                                         STYLE_LINE_Data, date_format,
                                         reconciled_entry.date, reconciled_entry.name, reconciled_entry.ref,
                                         l.name, reconciled_entry.name,
                                         reconciled_entry.journal_id,
                                         l.analytic_account_id,
                                         l.project_site_id,
                                         l.account_id,
                                         bank_line.account_id,
                                         reconciled_entry.partner_id,
                                         reconciled_entry.currency_id,
                                         0,
                                         l.debit,
                                         l.credit
                                         )
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
                                if line.credit != 0:
                                    exchange_rate = abs(
                                        line.credit) / abs(
                                        line.amount_currency)
                                else:
                                    exchange_rate = abs(
                                        line.debit) / abs(
                                        line.amount_currency)
                                amount = purchase_id.company_id.currency_id.round(
                                    exchange_rate * amount)

                            payble_account_line = line.line_ids.filtered(
                                lambda
                                    x: x.account_id.account_type != 'asset_current'
                                       or 'Bank Clearing' not in x.account_id.name)

                            bank_acct_line = line.line_ids.filtered(
                                lambda
                                    x: x.account_id.account_type == 'asset_current')
                            if len(bank_acct_line) > 1:
                                bank_acct_line = bank_acct_line.filtered(
                                    lambda x: 'Bank Clearing' in x.account_id.name)
                            credit_amount = 0
                            debit_amount = 0
                            print("bank_account_line5", bank_account_line)

                            if bank_account_line.credit:
                                credit_amount = amount
                                debit_amount = 0
                            else:
                                debit_amount = amount
                                credit_amount = 0
                            self.add_row(worksheet, row,
                                         STYLE_LINE_Data, date_format,
                                         line.date, line.name, line.ref,
                                         order_line.name, '',
                                         line.journal_id,
                                         order_line.cost_center_id,
                                         order_line.project_site_id,
                                         order_line.sudo().product_id.property_account_expense_id if order_line.sudo().product_id.property_account_expense_id else payble_account_line.account_id,
                                         bank_acct_line.account_id,
                                         line.partner_id,
                                         line.currency_id,
                                         0,
                                         debit_amount,
                                         credit_amount
                                         )
                            row += 1
                    else:
                        bank_acct_line = line.line_ids.filtered(
                            lambda x: x.account_id.account_type == 'asset_current')
                        if len(bank_acct_line) > 1:
                            bank_acct_line = bank_acct_line.filtered(
                                lambda x: 'Bank Clearing' in x.account_id.name)
                        payble_account_line = line.line_ids.filtered(
                            lambda x: x.account_id.account_type != 'asset_current' or  'Bank Clearing' not in x.account_id.name)

                        self.add_row(worksheet, row,
                                     STYLE_LINE_Data, date_format,
                                     line.date, line.name, line.ref,
                                     bank_acct_line.name, line.name,
                                     line.journal_id,
                                     bank_acct_line.analytic_account_id,
                                     bank_acct_line.project_site_id,
                                     payble_account_line.account_id,
                                     bank_acct_line.account_id,
                                     line.partner_id,
                                     line.currency_id,
                                     0,
                                     bank_acct_line.debit,
                                     bank_acct_line.credit
                                     )
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
                                    (
                                    float(item['amount_company_currency'].split(
                                        '\xa0')[-1].replace(',', '')) for item
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
                                    line_payment = round(amount * proportion,mv.currency_id.decimal_places)
                                    final_amount = round(company_currency_amount* proportion,mv.company_id.currency_id.decimal_places)
                                    if bank_line_id.credit:
                                        invoice_amount = line_payment
                                        credit_amount = final_amount
                                    else:
                                        invoice_amount = line_payment
                                        debit_amount = final_amount

                                    self.add_row(worksheet, row,
                                                 STYLE_LINE_Data, date_format,
                                                 line.date, line.name,
                                                 line.ref,
                                                 ml.name, mv.name,
                                                 line.journal_id,
                                                 ml.analytic_account_id,
                                                 ml.project_site_id,
                                                 ml.account_id,
                                                 bank_line_id.account_id,
                                                 line.partner_id,
                                                 line.currency_id,
                                                 invoice_amount,
                                                 debit_amount,
                                                 credit_amount
                                                 )
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
                                                if bank_line_id.debit:
                                                    debit_amount = exch["amount"]
                                                    credit_amount = 0
                                                else:
                                                    debit_amount = 0
                                                    credit_amount = exch["amount"]
                                                self.add_row(worksheet, row,
                                                             STYLE_LINE_Data,
                                                             date_format,
                                                             line.date, line.name,
                                                             line.ref,
                                                             exch_line.name, mv.name,
                                                             line.journal_id,
                                                             exch_line.analytic_account_id,
                                                             exch_line.project_site_id,
                                                             exch_line.account_id,
                                                             bank_line_id.account_id,
                                                             line.partner_id,
                                                             line.currency_id,
                                                             exch["amount"],
                                                             debit_amount,
                                                             credit_amount
                                                             )
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
                                                    (
                                                        float(item[
                                                                  'amount_company_currency'].split(
                                                            '\xa0')[-1].replace(
                                                            ',', '')) for item
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
                                                        invoice_amount = line_payment
                                                        credit_amount = final_amount
                                                    else:
                                                        invoice_amount = line_payment
                                                        debit_amount = final_amount
                                                    self.add_row(worksheet, row,
                                                                 STYLE_LINE_Data,
                                                                 date_format,
                                                                 line.date,
                                                                 line.name,
                                                                 line.ref,
                                                                 ml.name,
                                                                 mv.name,
                                                                 line.journal_id,
                                                                 ml.analytic_account_id,
                                                                 ml.project_site_id,
                                                                 ml.account_id,
                                                                 bank_line_id.account_id,
                                                                 line.partner_id,
                                                                 line.currency_id,
                                                                 invoice_amount,
                                                                 debit_amount,
                                                                 credit_amount
                                                                 )
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

                                                                self.add_row(
                                                                    worksheet,
                                                                    row,
                                                                    STYLE_LINE_Data,
                                                                    date_format,
                                                                    line.date,
                                                                    line.name,
                                                                    line.ref,
                                                                    exch_line.name,
                                                                    mv.name,
                                                                    line.journal_id,
                                                                    exch_line.analytic_account_id,
                                                                    exch_line.project_site_id,
                                                                    exch_line.account_id,
                                                                    bank_line_id.account_id,
                                                                    line.partner_id,
                                                                    line.currency_id,
                                                                    exch[
                                                                        "amount"],
                                                                    debit_amount,
                                                                    credit_amount
                                                                    )
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
                                                    (
                                                        float(item[
                                                            'amount_company_currency'].split(
                                                            '\xa0')[-1].replace(
                                                            ',', '')) for item
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
                                                    self.add_row(worksheet, row,
                                                                 STYLE_LINE_Data,
                                                                 date_format,
                                                                 line.date,
                                                                 line.name,
                                                                 line.ref,
                                                                 ml.name,
                                                                 mv.name,
                                                                 line.journal_id,
                                                                 ml.analytic_account_id,
                                                                 ml.project_site_id,
                                                                 ml.account_id,
                                                                 bank_line_id.account_id,
                                                                 line.partner_id,
                                                                 line.currency_id,
                                                                 invoice_amount,
                                                                 debit_amount,
                                                                 credit_amount
                                                                 )
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
                                                                self.add_row(
                                                                    worksheet,
                                                                    row,
                                                                    STYLE_LINE_Data,
                                                                    date_format,
                                                                    line.date,
                                                                    line.name,
                                                                    line.ref,
                                                                    exch_line.name,
                                                                    mv.name,
                                                                    line.journal_id,
                                                                    exch_line.analytic_account_id,
                                                                    exch_line.project_site_id,
                                                                    exch_line.account_id,
                                                                    bank_line_id.account_id,
                                                                    line.partner_id,
                                                                    line.currency_id,
                                                                    exch[
                                                                        "amount"],
                                                                    debit_amount,
                                                                    credit_amount
                                                                    )
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
                                                    if line.credit != 0:
                                                        exchange_rate = abs(
                                                            line.credit) / abs(
                                                            line.amount_currency)
                                                    else:
                                                        exchange_rate = abs(
                                                            line.debit) / abs(
                                                            line.amount_currency)
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
                                                print("bank_account_line6", bank_account_line)

                                                if bank_account_line.credit:
                                                    credit_amount = amount
                                                    debit_amount = 0
                                                else:
                                                    debit_amount = amount
                                                    credit_amount = 0
                                                self.add_row(worksheet, row,
                                                             STYLE_LINE_Data,
                                                             date_format,
                                                             line.date,
                                                             line.name,
                                                             line.ref,
                                                             order_line.name,
                                                             '',
                                                             line.journal_id,
                                                             order_line.cost_center_id,
                                                             order_line.project_site_id,
                                                             order_line.sudo().product_id.property_account_expense_id if order_line.sudo().product_id.property_account_expense_id else payble_account_line.account_id,
                                                             bank_acct_line.account_id,
                                                             line.partner_id,
                                                             line.currency_id,
                                                             0,
                                                             debit_amount,
                                                             credit_amount
                                                             )
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
                                            self.add_row(worksheet, row,
                                                         STYLE_LINE_Data,
                                                         date_format,
                                                         line.date, line.name,
                                                         line.ref,
                                                         bank_acct_line.name,
                                                         line.name,
                                                         line.journal_id,
                                                         bank_acct_line.analytic_account_id,
                                                         bank_acct_line.project_site_id,
                                                         payble_account_line.account_id,
                                                         bank_acct_line.account_id,
                                                         line.partner_id,
                                                         line.currency_id,
                                                         0,
                                                         bank_acct_line.debit,
                                                         bank_acct_line.credit
                                                         )
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
                                        amt = exch_line.credit if exch_line.credit else exch_line.debit

                                        if bank_line_id.credit !=0:
                                            credit_amount = amt
                                        else:
                                            debit_amount = amt
                                        invoice_amount = 0
                                        self.add_row(worksheet, row,
                                                     STYLE_LINE_Data,
                                                     date_format,
                                                     line.date, line.name,
                                                     line.ref,
                                                     exch_line.name, mv.name,
                                                     line.journal_id,
                                                     exch_line.analytic_account_id,
                                                     exch_line.project_site_id,
                                                     exch_line.account_id,
                                                     bank_line_id.account_id,
                                                     line.partner_id,
                                                     line.currency_id,
                                                     invoice_amount,
                                                     debit_amount,
                                                     credit_amount
                                                     )
                                        row += 1
                        if open_balance_line_ids:
                            for ob in open_balance_line_ids:
                                amount = ob.credit if ob.credit else ob.debit
                                if ob.credit:
                                    credit_amount = 0
                                    debit_amount = amount
                                    invoice_amount = 0

                                    self.add_row(worksheet, row,
                                                 STYLE_LINE_Data,
                                                 date_format,
                                                 line.date, line.name,
                                                 line.ref,
                                                 ob.name, '',
                                                 line.journal_id,
                                                 ob.analytic_account_id,
                                                 ob.project_site_id,
                                                 ob.account_id,
                                                 bank_line_id.account_id,
                                                 line.partner_id,
                                                 line.currency_id,
                                                 invoice_amount,
                                                 debit_amount,
                                                 credit_amount
                                                 )
                                else:
                                    credit_amount = amount
                                    debit_amount = 0
                                    invoice_amount = 0

                                    self.add_row(worksheet, row,
                                                 STYLE_LINE_Data,
                                                 date_format,
                                                 line.date, line.name,
                                                 line.ref,
                                                 ob.name, '',
                                                 line.journal_id,
                                                 ob.analytic_account_id,
                                                 ob.project_site_id,
                                                 ob.account_id,
                                                 bank_line_id.account_id,
                                                 line.partner_id,
                                                 line.currency_id,
                                                 invoice_amount,
                                                 debit_amount,
                                                 credit_amount
                                                 )

                                row += 1
                else:
                    bank_line = line.line_ids.filtered(
                        lambda x: x.account_id.account_type == 'asset_cash')
                    clearing_lines = line.line_ids.filtered(
                        lambda x: x.account_id.account_type != 'asset_cash')
                    for l in clearing_lines:
                        self.add_row(worksheet, row,
                                     STYLE_LINE_Data, date_format,
                                     line.date, line.name,
                                     line.ref,
                                     l.name, line.name,
                                     line.journal_id,
                                     l.analytic_account_id,
                                     l.project_site_id,
                                     l.account_id,
                                     bank_line.account_id,
                                     line.partner_id,
                                     line.currency_id,
                                     0,
                                     l.debit,
                                     l.credit
                                     )
                        row += 1
