import re
import base64
import io
import datetime
import xlsxwriter
from html2text import element_style

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class CashBurnReportWizard(models.Model):
    """ Class for Cash Burn Report xlsx """
    _name = 'cash.burn.report.wizard'
    _description = 'Cash Burn Report'

    start_date = fields.Date(string="From Date",
                             default=datetime.datetime.now(), required=True)
    end_date = fields.Date(string="To Date",
                           default=datetime.datetime.now(), required=True)
    company_id = fields.Many2one('res.company', 'Company',
                                 default=lambda self: self.env.company,
                                 required=True)
    excel_sheet = fields.Binary('Download Report')
    excel_sheet_name = fields.Char(string='Name', size=64)

    def clean_ref(self,ref):
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

        self.excel_sheet_name = 'Tasc Cash Burn Report'
        workbook.close()
        output.seek(0)
        self.excel_sheet = base64.b64encode(output.read())
        self.excel_sheet_name = str(self.excel_sheet_name) + '.xlsx'
        return {
            'type': 'ir.actions.act_url',
            'name': 'Tasc Cash Burn Report',
            'url': '/web/content/%s/%s/excel_sheet/%s?download=true' % (
                self._name, self.id, self.excel_sheet_name),
            'target': 'new'
        }

    def get_report_data(self):
        """Method to compute Tasc Cash Burn Report."""
        move_ids = self.env['account.bank.statement.line'].search(
            [('is_reconciled', '=', True), ('date', '>=', self.start_date),
             ('date', '<=', self.end_date),
             ('company_id', '=', self.company_id.id), ]).mapped('move_id')
        return move_ids

    def add_row(self, worksheet, date_format, STYLE_LINE_Data, col, row, line,
                move, move_line, debit_amount, credit_amount, ob, payment_id,
                invoice_amount,bank_line_id):
        if line.date:
            worksheet.write(row, col, line.date,
                            date_format)
        else:
            worksheet.write(row, col, '', date_format)

        col += 1
        if line.name:
            worksheet.write(row, col, line.name,
                            STYLE_LINE_Data)
        else:
            worksheet.write(row, col, '', STYLE_LINE_Data)

        col += 1
        if line.ref:
            worksheet.write(row, col, line.ref,
                            STYLE_LINE_Data)
        else:
            worksheet.write(row, col, '', STYLE_LINE_Data)

        col += 1
        if move and move.journal_id.type == 'general':
            move_line = move.line_ids.filtered(lambda x: x.debit != 0)
            if move_line and move_line.name:
                worksheet.write(row, col, move_line.name,
                                STYLE_LINE_Data)
            else:
                if ob:
                    worksheet.write(row, col, ob.name,
                                    STYLE_LINE_Data)
                else:
                    worksheet.write(row, col, '',
                                    STYLE_LINE_Data)
            col += 1
            if move and move.name:
                worksheet.write(row, col, move.name,
                                STYLE_LINE_Data)
            else:
                worksheet.write(row, col, '', STYLE_LINE_Data)

            col += 1
            if line.journal_id.name:
                worksheet.write(row, col, line.journal_id.name,
                                STYLE_LINE_Data)
            else:
                worksheet.write(row, col, '',
                                STYLE_LINE_Data)
            col += 1
            if move_line and move_line.analytic_account_id.name:
                if move_line.analytic_account_id.code:
                    worksheet.write(row, col,
                                    move_line.analytic_account_id.code + " " + move_line.analytic_account_id.name,
                                    STYLE_LINE_Data)
                else:
                    worksheet.write(row, col,
                                    move_line.analytic_account_id.name,
                                    STYLE_LINE_Data)
            else:
                if ob and ob.analytic_account_id.name:
                    if ob.analytic_account_id.code:
                        worksheet.write(row, col,
                                        ob.analytic_account_id.code + " " + ob.analytic_account_id.name,
                                        STYLE_LINE_Data)
                    else:
                        worksheet.write(row, col,
                                        ob.analytic_account_id.name,
                                        STYLE_LINE_Data)
                else:
                    worksheet.write(row, col, '',
                                    STYLE_LINE_Data)
            col += 1
            if move_line and move_line.project_site_id.name:
                if move_line.project_site_id.code:
                    worksheet.write(row, col,
                                    move_line.project_site_id.code + " " + move_line.project_site_id.name,
                                    STYLE_LINE_Data)
                else:
                    worksheet.write(row, col,
                                    move_line.project_site_id.name,
                                    STYLE_LINE_Data)
            else:
                if ob and ob.project_site_id.name:
                    if ob.project_site_id.code:
                        worksheet.write(row, col,
                                        ob.project_site_id.code + " " + ob.project_site_id.name,
                                        STYLE_LINE_Data)
                    else:
                        worksheet.write(row, col,
                                        ob.project_site_id.name,
                                        STYLE_LINE_Data)
                else:
                    worksheet.write(row, col,
                                    '',
                                    STYLE_LINE_Data)
            col += 1
            if move_line and move_line.account_id:
                worksheet.write(row, col,
                                str(move_line.account_id.code) + " " + move_line.account_id.name,
                                STYLE_LINE_Data)
            else:
                if ob and ob.account_id:
                    worksheet.write(row, col,
                                    str(ob.account_id.code) + " " + ob.account_id.name,
                                    STYLE_LINE_Data)
                else:
                    worksheet.write(row, col, '', STYLE_LINE_Data)
            col += 1
            if bank_line_id and bank_line_id.account_id:
                worksheet.write(row, col,
                                str(bank_line_id.account_id.code) + " " + bank_line_id.account_id.name,
                                STYLE_LINE_Data)
            else:
                worksheet.write(row, col, '', STYLE_LINE_Data)
            col += 1
        else:
            if move_line and move_line.name:
                worksheet.write(row, col, move_line.name,
                                STYLE_LINE_Data)
            else:
                if ob:
                    worksheet.write(row, col, ob.name,
                                    STYLE_LINE_Data)
                else:
                    worksheet.write(row, col, '',
                                    STYLE_LINE_Data)
            col += 1
            if move and move.name:
                worksheet.write(row, col, move.name,
                                STYLE_LINE_Data)
            else:
                worksheet.write(row, col, '', STYLE_LINE_Data)

            col += 1
            if line.journal_id.name:
                worksheet.write(row, col, line.journal_id.name,
                                STYLE_LINE_Data)
            else:
                worksheet.write(row, col, '',
                                STYLE_LINE_Data)
            col += 1
            if move_line and move_line.analytic_account_id.name:
                if move_line.analytic_account_id.code:
                    worksheet.write(row, col,
                                    move_line.analytic_account_id.code + " " + move_line.analytic_account_id.name,
                                    STYLE_LINE_Data)
                else:
                    worksheet.write(row, col,
                                    move_line.analytic_account_id.name,
                                    STYLE_LINE_Data)
            else:
                if ob and ob.analytic_account_id.name:
                    if ob.analytic_account_id.code:
                        worksheet.write(row, col,
                                        ob.analytic_account_id.code + " " + ob.analytic_account_id.name,
                                        STYLE_LINE_Data)
                    else:
                        worksheet.write(row, col,
                                        ob.analytic_account_id.name,
                                        STYLE_LINE_Data)
                else:
                    worksheet.write(row, col, '',
                                    STYLE_LINE_Data)

            col += 1
            if move_line and move_line.project_site_id.name:
                if move_line.project_site_id.code:
                    worksheet.write(row, col,
                                    move_line.project_site_id.code + " " + move_line.project_site_id.name,
                                    STYLE_LINE_Data)
                else:
                    worksheet.write(row, col,
                                    move_line.project_site_id.name,
                                    STYLE_LINE_Data)
            else:
                if ob and ob.project_site_id.name:
                    if ob.project_site_id.code:
                        worksheet.write(row, col,
                                        ob.project_site_id.code + " " + ob.project_site_id.name,
                                        STYLE_LINE_Data)
                    else:
                        worksheet.write(row, col,
                                        ob.project_site_id.name,
                                        STYLE_LINE_Data)
                else:
                    worksheet.write(row, col,
                                    '',
                                    STYLE_LINE_Data)
            col += 1
            if move_line and move_line.account_id:
                worksheet.write(row, col,
                                str(move_line.account_id.code) + " " + move_line.account_id.name,
                                STYLE_LINE_Data)
            else:
                if ob and ob.account_id:
                    worksheet.write(row, col,
                                    str(ob.account_id.code) + " " + ob.account_id.name,
                                    STYLE_LINE_Data)
                else:
                    worksheet.write(row, col, '', STYLE_LINE_Data)
            col += 1
            if bank_line_id and bank_line_id.account_id:
                worksheet.write(row, col,
                                str(bank_line_id.account_id.code) + " " + bank_line_id.account_id.name,
                                STYLE_LINE_Data)
            else:
                worksheet.write(row, col, '', STYLE_LINE_Data)
            col += 1
        if move and move.partner_id:
            worksheet.write(row, col,
                            move.partner_id.name,
                            STYLE_LINE_Data)
        else:
            if move_line.partner_id:
                worksheet.write(row, col,
                                move_line.partner_id.name,
                                STYLE_LINE_Data)
            else:
                worksheet.write(row, col,
                                '',
                                STYLE_LINE_Data)
        col += 1

        if payment_id:
            worksheet.write(row, col,
                            payment_id.currency_id.name,
                            STYLE_LINE_Data)
        else:
            if move_line and move_line.currency_id:
                worksheet.write(row, col,
                                move_line.currency_id.name,
                                STYLE_LINE_Data)
            else:
                worksheet.write(row, col,
                                '',
                                STYLE_LINE_Data)
        col += 1
        if invoice_amount:
            worksheet.write(row, col,
                            invoice_amount,
                            STYLE_LINE_Data)
        else:
            worksheet.write(row, col,
                            0,
                            STYLE_LINE_Data)
        col += 1

        worksheet.write(row, col, credit_amount,
                        STYLE_LINE_Data)
        col += 1
        worksheet.write(row, col, debit_amount,
                        STYLE_LINE_Data)
        col += 1
        worksheet.write(row, col,
                        abs(credit_amount)-abs(debit_amount),
                        STYLE_LINE_Data)

    def add_xlsx_sheet(self, report_data, workbook, STYLE_LINE_Data,
                       header_format, STYLE_LINE_HEADER, date_format):
        """ Method to add datas to the Tasc Cash Burn xlsx report"""
        self.ensure_one()
        worksheet = workbook.add_worksheet(_('Tasc Cash Burn Report'))
        lang = self.env.user.lang
        if lang.startswith('ar_'):
            worksheet.right_to_left()

        row = 0
        col = 0
        worksheet.merge_range(row, row, col, col + 15,
                              _('Tasc Cash Burn Report'),
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
        row += 1
        for line in report_data:
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
                                                        'general'] or x.payment_id)
            move = move_line_ids.mapped('move_id')
            if move:
                for mv in move:
                    reconciled_line_id = move_line_ids.filtered(
                        lambda x: x.move_id.id == mv.id and x.debit!=0)
                    col = 0
                    if mv.journal_id.type in ['sale',
                                              'purchase'] and not mv.payment_id and mv.move_type != 'entry':
                        credit_amount = 0
                        debit_amount = 0
                        s = mv.invoice_payments_widget
                        move_line = self.env[
                            'account.move.line'].search(
                            [('id','in', mv.invoice_line_ids.ids)],
                            order='id ASC')
                        total = sum(move_line.mapped('price_total'))
                        amount = next(
                            (item['amount'] for item in s['content'] if
                             item['amount'] and self.clean_ref(item['ref']) == self.clean_ref(line.name)), 0)
                        for ml in move_line:
                            proportion = ml.price_total / total
                            line_payment = amount * proportion
                            if ml.credit != 0:
                                exchange_rate = abs(
                                    ml.credit) / abs(
                                    ml.amount_currency)
                            else:
                                exchange_rate = abs(
                                    ml.debit) / abs(
                                    ml.amount_currency)
                            final_amount = self.env.company.currency_id.round(
                                exchange_rate * line_payment)
                            col = 0
                            if bank_line_id.credit:
                                invoice_amount = line_payment
                                credit_amount = final_amount
                            else:
                                invoice_amount = line_payment
                                debit_amount = final_amount
                            self.add_row(worksheet, date_format,
                                         STYLE_LINE_Data, col, row, line,
                                         mv,
                                         ml,
                                         debit_amount, credit_amount, False,
                                         False, invoice_amount,bank_line_id)
                            row += 1
                        if s:
                            exchange_entries = [item for
                                                item in
                                                s["content"]
                                                if item[
                                                    'is_exchange']]
                            if exchange_entries:
                                for exch in exchange_entries:
                                    col = 0
                                    move_id = self.env[
                                        'account.move'].browse(
                                        exch["move_id"])
                                    if move_id.id not in exchange_moves:
                                        exchange_moves.append((move_id.id))
                                        if bank_line_id.debit:
                                            db_line = self.env[
                                                'account.move.line'].search(
                                                [('move_id', '=',
                                                  exch["move_id"]),
                                                 ('debit', '!=', 0)])

                                            debit_amount = exch["amount"]
                                            credit_amount = 0
                                        else:
                                            db_line = self.env[
                                                'account.move.line'].search(
                                                [('move_id', '=',
                                                  exch["move_id"]),
                                                 ('credit', '!=', 0)])

                                            debit_amount = 0
                                            credit_amount = exch["amount"]
                                        self.add_row(worksheet,
                                                     date_format,
                                                     STYLE_LINE_Data,
                                                     col,
                                                     row,
                                                     line, move_id,
                                                     db_line,
                                                     debit_amount,
                                                     credit_amount,
                                                     False,
                                                     False,
                                                     False,
                                                     bank_line_id)
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
                                            move_line.mapped('price_total'))
                                        amount = next(
                                            (item['amount'] for item in
                                             s['content']
                                             if item['amount'] and
                                             self.clean_ref(item['ref']) == self.clean_ref(mv.payment_id.name)),
                                            0
                                        )
                                        for ml in move_line:
                                            proportion = ml.price_total / total
                                            line_payment = amount * proportion
                                            if ml.credit != 0:
                                                exchange_rate = abs(
                                                    ml.credit) / abs(
                                                    ml.amount_currency)
                                            else:
                                                exchange_rate = abs(
                                                    ml.debit) / abs(
                                                    ml.amount_currency)
                                            final_amount = self.env.company.currency_id.round(exchange_rate*line_payment)
                                            col = 0
                                            if bank_line_id.credit:
                                                invoice_amount = line_payment
                                                credit_amount = final_amount
                                            else:
                                                invoice_amount = line_payment
                                                debit_amount = final_amount

                                            self.add_row(worksheet,
                                                         date_format,
                                                         STYLE_LINE_Data,
                                                         col,
                                                         row,
                                                         line, m, ml,
                                                         debit_amount,
                                                         credit_amount,
                                                         False,
                                                         mv.payment_id,
                                                         invoice_amount,
                                                         bank_line_id)
                                            row += 1
                                        if s:
                                            exchange_entries = [item for
                                                                item in
                                                                s["content"]
                                                                if item[
                                                                    'is_exchange']
                                                                ]
                                            if exchange_entries:
                                                for exch in exchange_entries:
                                                    col =0
                                                    move_id = self.env['account.move'].browse(exch["move_id"])
                                                    if move_id.id not in exchange_moves:
                                                        exchange_moves.append(
                                                            (move_id.id))
                                                        if bank_line_id.credit:
                                                            db_line = self.env[
                                                                'account.move.line'].search(
                                                                [(
                                                                    'move_id',
                                                                    '=',
                                                                    exch[
                                                                        "move_id"]),
                                                                    ('credit',
                                                                     '!=',
                                                                     0)])
                                                            debit_amount = 0
                                                            credit_amount = \
                                                            exch[
                                                                "amount"]
                                                        else:
                                                            db_line = self.env[
                                                                'account.move.line'].search(
                                                                [(
                                                                 'move_id', '=',
                                                                 exch[
                                                                     "move_id"]),
                                                                 ('debit', '!=',
                                                                  0)])
                                                            debit_amount = exch[
                                                                "amount"]
                                                            credit_amount = 0

                                                        self.add_row(worksheet,
                                                                     date_format,
                                                                     STYLE_LINE_Data,
                                                                     col,
                                                                     row,
                                                                     line, move_id,
                                                                     db_line,
                                                                     debit_amount,
                                                                     credit_amount,
                                                                     False,
                                                                     False,
                                                                     False,
                                                                     bank_line_id)
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
                                            move_line.mapped('price_total'))
                                        amount = next(
                                            (item['amount'] for item in
                                             s['content']
                                             if item['amount'] and
                                             self.clean_ref(item['ref']) == self.clean_ref(mv.payment_id.name)),
                                            0
                                        )
                                        for ml in move_line:
                                            proportion = ml.price_total / total
                                            line_payment = amount * proportion
                                            if ml.credit != 0:
                                                exchange_rate = abs(
                                                    ml.credit) / abs(
                                                    ml.amount_currency)
                                            else:
                                                exchange_rate = abs(
                                                    ml.debit) / abs(
                                                    ml.amount_currency)
                                            final_amount = self.env.company.currency_id.round(
                                                exchange_rate * line_payment)
                                            col = 0
                                            if bank_line_id.credit:
                                                invoice_amount = line_payment
                                                credit_amount = final_amount
                                            else:
                                                invoice_amount = line_payment
                                                debit_amount = final_amount
                                            self.add_row(worksheet,
                                                         date_format,
                                                         STYLE_LINE_Data,
                                                         col,
                                                         row,
                                                         line, m, ml,
                                                         debit_amount,
                                                         credit_amount,
                                                         False,
                                                         mv.payment_id,
                                                         invoice_amount,
                                                         bank_line_id)
                                            row += 1
                                        if s:
                                            exchange_entries = [item for
                                                                item in
                                                                s["content"]
                                                                if item[
                                                                    'is_exchange']]
                                            if exchange_entries:
                                                for exch in exchange_entries:
                                                    col =0
                                                    move_id = self.env[
                                                        'account.move'].browse(
                                                        exch["move_id"])
                                                    if move_id.id not in exchange_moves:
                                                        exchange_moves.append(
                                                            (move_id.id))
                                                        if bank_line_id.credit:
                                                            db_line = self.env[
                                                                'account.move.line'].search(
                                                                [(
                                                                    'move_id',
                                                                    '=',
                                                                    exch[
                                                                        "move_id"]),
                                                                    ('credit',
                                                                     '!=',
                                                                     0)])
                                                            debit_amount = 0
                                                            credit_amount = \
                                                            exch[
                                                                "amount"]
                                                        else:
                                                            db_line = self.env[
                                                                'account.move.line'].search(
                                                                [(
                                                                 'move_id', '=',
                                                                 exch[
                                                                     "move_id"]),
                                                                 ('debit', '!=',
                                                                  0)])
                                                            debit_amount = exch[
                                                                "amount"]
                                                            credit_amount = 0
                                                        self.add_row(worksheet,
                                                                     date_format,
                                                                     STYLE_LINE_Data,
                                                                     col,
                                                                     row,
                                                                     line, move_id,
                                                                     db_line,
                                                                     debit_amount,
                                                                     credit_amount,
                                                                     False,
                                                                     False,
                                                                     False,
                                                                     bank_line_id)
                                                        row += 1
                            else:
                                credit_amount = 0
                                debit_amount = 0
                                invoice_amount = abs(
                                    reconciled_line_id.amount_currency)
                                amount = abs(
                                        reconciled_line_id.credit) if reconciled_line_id.credit else abs(reconciled_line_id.debit)

                                if bank_line_id.credit:
                                    credit_amount = amount
                                    debit_amount = 0
                                else:
                                    credit_amount = 0
                                    debit_amount = amount

                                self.add_row(worksheet, date_format,
                                             STYLE_LINE_Data, col,
                                             row,
                                             line, False, reconciled_line_id,
                                             debit_amount,
                                             credit_amount, False,
                                             False, invoice_amount,
                                             bank_line_id)
                                row += 1
                        else:
                            if mv.id not in exchange_moves:
                                exchange_moves.append(
                                    (mv.id))
                                credit_amount = 0
                                debit_amount = 0
                                amt = 0
                                lines = mv.line_ids.filtered(lambda x: x.debit != 0)
                                amt = sum(lines.mapped('debit'))

                                if bank_line_id.credit !=0:
                                    credit_amount = amt
                                else:
                                    debit_amount = amt
                                invoice_amount = 0
                                self.add_row(worksheet, date_format,
                                             STYLE_LINE_Data, col, row,
                                             line, mv, lines,
                                             debit_amount,
                                             credit_amount, False, False,
                                             invoice_amount,
                                             bank_line_id)
                                row += 1
                if open_balance_line_ids:
                    for ob in open_balance_line_ids:
                        col = 0
                        amount = ob.credit if ob.credit else ob.debit
                        if ob.credit:
                            credit_amount = 0
                            debit_amount = amount
                            invoice_amount = 0

                            self.add_row(worksheet, date_format,
                                         STYLE_LINE_Data, col, row,
                                         line, False, ob,
                                         debit_amount,
                                         credit_amount, ob, False,
                                         invoice_amount,
                                         bank_line_id)
                        else:
                            credit_amount = amount
                            debit_amount = 0
                            invoice_amount = 0

                            self.add_row(worksheet, date_format,
                                         STYLE_LINE_Data, col, row,
                                         line, False, ob,
                                         debit_amount,
                                         credit_amount, ob, False,
                                         invoice_amount,
                                         bank_line_id)

                        row += 1
            else:
                invoice_amount = 0
                gain_or_loss_line = line.line_ids.filtered(
                    lambda x: x.account_id.account_type != 'asset_cash')
                for l in gain_or_loss_line:
                    col = 0

                    amount = l.credit if l.credit else l.debit
                    if bank_line_id.credit:
                        credit_amount = amount
                        debit_amount = 0
                    else:
                        credit_amount = 0
                        debit_amount = amount

                    self.add_row(worksheet, date_format,
                                 STYLE_LINE_Data, col, row,
                                 line, False, l,
                                 debit_amount,
                                 credit_amount, False, False,
                                 invoice_amount,bank_line_id)
                    row += 1
