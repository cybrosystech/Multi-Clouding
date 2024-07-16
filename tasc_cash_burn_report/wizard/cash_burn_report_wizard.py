import base64
import io
import datetime
import xlsxwriter
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
            'align': 'center',
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
        move_ids = self.env['account.move'].search(
            [('journal_id.type', '=', 'bank'),
             ('company_id', '=', self.company_id.id),
             ('date', '>=', self.start_date), ('date', '<=', self.end_date)])
        return move_ids

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
        worksheet.merge_range(row, row, col, col + 12,
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
        worksheet.write(row, col, _('Partner'), header_format)
        col += 1
        worksheet.write(row, col, _('Invoice lines/Credit'), header_format)
        col += 1
        worksheet.write(row, col, _('Invoice lines/Debit'), header_format)
        col += 1
        worksheet.write(row, col, _('Net'), header_format)
        col += 1
        for line in report_data:
            col = 0
            row += 1
            debit_lines = line.line_ids.filtered(lambda x: x.debit != 0)
            if len(debit_lines.ids) == 1:
                reconcile_items = line.open_reconcile_view()
                move = self.env['account.move.line'].search(
                    reconcile_items['domain']).filtered(
                    lambda x: x.move_id.journal_id.type in ['sale', 'purchase'])
                move_ids = move.mapped('move_id')
                if move_ids:
                    if len(move_ids.ids) == 1:
                        move_lines = move_ids.invoice_line_ids
                        if len(move_lines.ids) == 1:
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
                            if debit_lines.name:
                                worksheet.write(row, col, debit_lines.name,
                                                STYLE_LINE_Data)
                            else:
                                worksheet.write(row, col, '', STYLE_LINE_Data)
                            col += 1
                            worksheet.write(row, col, move_ids.name,
                                            STYLE_LINE_Data)
                            col += 1
                            worksheet.write(row, col, line.journal_id.name,
                                            STYLE_LINE_Data)
                            col += 1

                            if move_lines.analytic_account_id:
                                worksheet.write(row, col,
                                                move_lines.analytic_account_id.name,
                                                STYLE_LINE_Data)
                            else:
                                worksheet.write(row, col, '', STYLE_LINE_Data)
                            col += 1
                            if move_lines.project_site_id:
                                worksheet.write(row, col,
                                                move_lines.project_site_id.name,
                                                STYLE_LINE_Data)
                            else:
                                worksheet.write(row, col, '', STYLE_LINE_Data)
                            col += 1
                            if move_lines.account_id:
                                worksheet.write(row, col,
                                                str(move_lines.account_id.code) + " " + move_lines.account_id.name,
                                                STYLE_LINE_Data)
                            else:
                                worksheet.write(row, col, '', STYLE_LINE_Data)
                            col += 1
                            if move_ids.partner_id:
                                worksheet.write(row, col,
                                                move_ids.partner_id.name,
                                                STYLE_LINE_Data)
                            else:
                                worksheet.write(row, col, '', STYLE_LINE_Data)
                            col+=1
                            worksheet.write(row, col, debit_lines.credit,
                                            STYLE_LINE_Data)
                            col += 1
                            worksheet.write(row, col, debit_lines.debit,
                                            STYLE_LINE_Data)
                            col += 1
                            worksheet.write(row, col, abs(debit_lines.debit) + abs(
                                debit_lines.credit),
                                            STYLE_LINE_Data)
                        else:
                            for mv_line in move_lines:
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
                                    worksheet.write(row, col, '',
                                                    STYLE_LINE_Data)
                                col += 1
                                if line.ref:
                                    worksheet.write(row, col, line.ref,
                                                    STYLE_LINE_Data)
                                else:
                                    worksheet.write(row, col, '',
                                                    STYLE_LINE_Data)
                                col += 1
                                if debit_lines.name:
                                    worksheet.write(row, col, debit_lines.name,
                                                    STYLE_LINE_Data)
                                else:
                                    worksheet.write(row, col, '',
                                                    STYLE_LINE_Data)
                                col += 1
                                worksheet.write(row, col, move_ids.name,
                                                STYLE_LINE_Data)
                                col += 1
                                worksheet.write(row, col, line.journal_id.name,
                                                STYLE_LINE_Data)
                                col += 1

                                if mv_line.analytic_account_id:
                                    worksheet.write(row, col,
                                                    mv_line.analytic_account_id.name,
                                                    STYLE_LINE_Data)
                                else:
                                    worksheet.write(row, col, '',
                                                    STYLE_LINE_Data)
                                col += 1
                                if mv_line.project_site_id:
                                    worksheet.write(row, col,
                                                    mv_line.project_site_id.name,
                                                    STYLE_LINE_Data)
                                else:
                                    worksheet.write(row, col, '',
                                                    STYLE_LINE_Data)
                                col += 1
                                if mv_line.account_id:
                                    worksheet.write(row, col,
                                                    str(mv_line.account_id.code) + " " + mv_line.account_id.name,
                                                    STYLE_LINE_Data)
                                else:
                                    worksheet.write(row, col, '',
                                                    STYLE_LINE_Data)
                                col += 1
                                if move_ids.partner_id:
                                    worksheet.write(row, col,
                                                    move_ids.partner_id.name,
                                                    STYLE_LINE_Data)
                                else:
                                    worksheet.write(row, col, '',
                                                    STYLE_LINE_Data)
                                col += 1
                                worksheet.write(row, col, debit_lines.credit,
                                                STYLE_LINE_Data)
                                col += 1
                                worksheet.write(row, col, debit_lines.debit,
                                                STYLE_LINE_Data)
                                col += 1
                                worksheet.write(row, col,
                                                abs(debit_lines.debit) + abs(
                                                    debit_lines.credit),
                                                STYLE_LINE_Data)

                    else:
                        for move in move_ids:
                            col = 0

                            move_lines = move.invoice_line_ids
                            if len(move_lines.ids) ==1:
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
                                    worksheet.write(row, col, '',
                                                    STYLE_LINE_Data)
                                col += 1
                                if line.ref:
                                    worksheet.write(row, col, line.ref,
                                                    STYLE_LINE_Data)
                                else:
                                    worksheet.write(row, col, '',
                                                    STYLE_LINE_Data)
                                col += 1
                                if debit_lines.name:
                                    worksheet.write(row, col, debit_lines.name,
                                                    STYLE_LINE_Data)
                                else:
                                    worksheet.write(row, col, '',
                                                    STYLE_LINE_Data)
                                col += 1
                                worksheet.write(row, col, move.name,
                                                STYLE_LINE_Data)
                                col += 1
                                worksheet.write(row, col, line.journal_id.name,
                                                STYLE_LINE_Data)
                                col += 1
                                if move_lines.analytic_account_id:
                                    worksheet.write(row, col,
                                                    move_lines.analytic_account_id.name,
                                                    STYLE_LINE_Data)
                                else:
                                    worksheet.write(row, col, '', STYLE_LINE_Data)
                                col += 1
                                if move_lines.project_site_id:
                                    worksheet.write(row, col,
                                                    move_lines.project_site_id.name,
                                                    STYLE_LINE_Data)
                                else:
                                    worksheet.write(row, col, '', STYLE_LINE_Data)
                                col += 1
                                if move_lines.account_id:
                                    worksheet.write(row, col,
                                                    str(move_lines.account_id.code) + " " + move_lines.account_id.name,
                                                    STYLE_LINE_Data)
                                else:
                                    worksheet.write(row, col, '', STYLE_LINE_Data)
                                col += 1
                                if move.partner_id:
                                    worksheet.write(row, col,
                                                    move.partner_id.name,
                                                    STYLE_LINE_Data)
                                else:
                                    worksheet.write(row, col, '', STYLE_LINE_Data)
                                col+=1
                                worksheet.write(row, col, debit_lines.credit,
                                                STYLE_LINE_Data)
                                col += 1
                                worksheet.write(row, col, debit_lines.debit,
                                                STYLE_LINE_Data)
                                col += 1
                                worksheet.write(row, col,
                                                abs(debit_lines.debit) + abs(
                                                    debit_lines.credit),
                                                STYLE_LINE_Data)
                            else:
                                for mv_line in move_lines:
                                    if line.date:
                                        worksheet.write(row, col, line.date,
                                                        date_format)
                                    else:
                                        worksheet.write(row, col, '',
                                                        date_format)
                                    col += 1
                                    if line.name:
                                        worksheet.write(row, col, line.name,
                                                        STYLE_LINE_Data)
                                    else:
                                        worksheet.write(row, col, '',
                                                        STYLE_LINE_Data)
                                    col += 1
                                    if line.ref:
                                        worksheet.write(row, col, line.ref,
                                                        STYLE_LINE_Data)
                                    else:
                                        worksheet.write(row, col, '',
                                                        STYLE_LINE_Data)
                                    col += 1
                                    if debit_lines.name:
                                        worksheet.write(row, col,
                                                        debit_lines.name,
                                                        STYLE_LINE_Data)
                                    else:
                                        worksheet.write(row, col, '',
                                                        STYLE_LINE_Data)
                                    col += 1
                                    worksheet.write(row, col, move.name,
                                                    STYLE_LINE_Data)
                                    col += 1
                                    worksheet.write(row, col,
                                                    line.journal_id.name,
                                                    STYLE_LINE_Data)
                                    col += 1
                                    if mv_line.analytic_account_id:
                                        worksheet.write(row, col,
                                                        mv_line.analytic_account_id.name,
                                                        STYLE_LINE_Data)
                                    else:
                                        worksheet.write(row, col, '',
                                                        STYLE_LINE_Data)
                                    col += 1
                                    if mv_line.project_site_id:
                                        worksheet.write(row, col,
                                                        mv_line.project_site_id.name,
                                                        STYLE_LINE_Data)
                                    else:
                                        worksheet.write(row, col, '',
                                                        STYLE_LINE_Data)
                                    col += 1
                                    if mv_line.account_id:
                                        worksheet.write(row, col,
                                                        str(mv_line.account_id.code) + " " + mv_line.account_id.name,
                                                        STYLE_LINE_Data)
                                    else:
                                        worksheet.write(row, col, '',
                                                        STYLE_LINE_Data)
                                    col += 1
                                    if move.partner_id:
                                        worksheet.write(row, col,
                                                        move.partner_id.name,
                                                        STYLE_LINE_Data)
                                    else:
                                        worksheet.write(row, col, '',
                                                        STYLE_LINE_Data)
                                    col += 1
                                    worksheet.write(row, col,
                                                    debit_lines.credit,
                                                    STYLE_LINE_Data)
                                    col += 1
                                    worksheet.write(row, col, debit_lines.debit,
                                                    STYLE_LINE_Data)
                                    col += 1
                                    worksheet.write(row, col,
                                                    abs(debit_lines.debit) + abs(
                                                        debit_lines.credit),
                                                    STYLE_LINE_Data)

                else:
                    if line.date:
                        worksheet.write(row, col, line.date, date_format)
                    else:
                        worksheet.write(row, col, '', date_format)
                    col += 1
                    if line.name:
                        worksheet.write(row, col, line.name, STYLE_LINE_Data)
                    else:
                        worksheet.write(row, col, '', STYLE_LINE_Data)
                    col += 1
                    if line.ref:
                        worksheet.write(row, col, line.ref, STYLE_LINE_Data)
                    else:
                        worksheet.write(row, col, '', STYLE_LINE_Data)
                    col += 1
                    if debit_lines.name:
                        worksheet.write(row, col, debit_lines.name,
                                        STYLE_LINE_Data)
                    else:
                        worksheet.write(row, col, '', STYLE_LINE_Data)
                    col += 1
                    worksheet.write(row, col, '',
                                    STYLE_LINE_Data)
                    col += 1
                    worksheet.write(row, col, line.journal_id.name,
                                    STYLE_LINE_Data)
                    col += 1
                    if debit_lines.analytic_account_id:
                        worksheet.write(row, col, debit_lines.analytic_account_id.name,
                                        STYLE_LINE_Data)
                    else:
                        worksheet.write(row, col, '',
                                        STYLE_LINE_Data)

                    col += 1
                    if debit_lines.project_site_id:
                        worksheet.write(row, col, debit_lines.project_site_id.name,
                                        STYLE_LINE_Data)
                    else:
                        worksheet.write(row, col, '',
                                        STYLE_LINE_Data)
                    col += 1
                    if debit_lines.account_id:
                        worksheet.write(row, col,
                                        str(debit_lines.code) + " " + debit_lines.account_id.name,
                                        STYLE_LINE_Data)
                    else:
                        worksheet.write(row, col, '',
                                        STYLE_LINE_Data)

                    col += 1
                    if debit_lines.move_id.partner_id:
                        worksheet.write(row, col,
                                       debit_lines.move_id.partner_id.name,
                                        STYLE_LINE_Data)
                    else:
                        worksheet.write(row, col, '',
                                        STYLE_LINE_Data)

                    col += 1
                    worksheet.write(row, col, debit_lines.credit,
                                    STYLE_LINE_Data)
                    col += 1
                    worksheet.write(row, col, debit_lines.debit,
                                    STYLE_LINE_Data)
                    col += 1
                    worksheet.write(row, col, abs(debit_lines.debit) + abs(
                        debit_lines.credit),
                                    STYLE_LINE_Data)

            else:
                for debit_ln in debit_lines:
                    reconcile_items = line.open_reconcile_view()
                    move = self.env['account.move.line'].search(
                        reconcile_items['domain']).filtered(
                        lambda x: x.move_id.journal_id.type in ['sale',
                                                                'purchase'])
                    move_ids = move.mapped('move_id')
                    if move_ids:
                        if len(move_ids.ids) == 1:
                            move_lines = move_ids.invoice_line_ids
                            if len(move_lines.ids) == 1:
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
                                    worksheet.write(row, col, '',
                                                    STYLE_LINE_Data)
                                col += 1
                                if line.ref:
                                    worksheet.write(row, col, line.ref,
                                                    STYLE_LINE_Data)
                                else:
                                    worksheet.write(row, col, '',
                                                    STYLE_LINE_Data)
                                col += 1
                                if debit_ln.name:
                                    worksheet.write(row, col, debit_ln.name,
                                                    STYLE_LINE_Data)
                                else:
                                    worksheet.write(row, col, '',
                                                    STYLE_LINE_Data)
                                col += 1
                                worksheet.write(row, col, move_ids.name,
                                                STYLE_LINE_Data)
                                col += 1
                                worksheet.write(row, col, line.journal_id.name,
                                                STYLE_LINE_Data)
                                col += 1

                                if move_lines.analytic_account_id:
                                    worksheet.write(row, col,
                                                    move_lines.analytic_account_id.name,
                                                    STYLE_LINE_Data)
                                else:
                                    worksheet.write(row, col, '',
                                                    STYLE_LINE_Data)
                                col += 1
                                if move_lines.project_site_id:
                                    worksheet.write(row, col,
                                                    move_lines.project_site_id.name,
                                                    STYLE_LINE_Data)
                                else:
                                    worksheet.write(row, col, '',
                                                    STYLE_LINE_Data)
                                col += 1
                                if move_lines.account_id:
                                    worksheet.write(row, col,
                                                    str(move_lines.account_id.code) + " " + move_lines.account_id.name,
                                                    STYLE_LINE_Data)
                                else:
                                    worksheet.write(row, col, '',
                                                    STYLE_LINE_Data)
                                col += 1
                                if move_ids.partner_id:
                                    worksheet.write(row, col,
                                                    move_ids.partner_id.name,
                                                    STYLE_LINE_Data)
                                else:
                                    worksheet.write(row, col, '',
                                                    STYLE_LINE_Data)
                                col += 1
                                worksheet.write(row, col, debit_ln.credit,
                                                STYLE_LINE_Data)
                                col += 1
                                worksheet.write(row, col, debit_ln.debit,
                                                STYLE_LINE_Data)
                                col += 1
                                worksheet.write(row, col,
                                                abs(debit_ln.debit) + abs(
                                                    debit_ln.credit),
                                                STYLE_LINE_Data)
                            else:
                                for mv_line in move_lines:
                                    if line.date:
                                        worksheet.write(row, col, line.date,
                                                        date_format)
                                    else:
                                        worksheet.write(row, col, '',
                                                        date_format)
                                    col += 1
                                    if line.name:
                                        worksheet.write(row, col, line.name,
                                                        STYLE_LINE_Data)
                                    else:
                                        worksheet.write(row, col, '',
                                                        STYLE_LINE_Data)
                                    col += 1
                                    if line.ref:
                                        worksheet.write(row, col, line.ref,
                                                        STYLE_LINE_Data)
                                    else:
                                        worksheet.write(row, col, '',
                                                        STYLE_LINE_Data)
                                    col += 1
                                    if debit_ln.name:
                                        worksheet.write(row, col,
                                                        debit_ln.name,
                                                        STYLE_LINE_Data)
                                    else:
                                        worksheet.write(row, col, '',
                                                        STYLE_LINE_Data)
                                    col += 1
                                    worksheet.write(row, col, move_ids.name,
                                                    STYLE_LINE_Data)
                                    col += 1
                                    worksheet.write(row, col,
                                                    line.journal_id.name,
                                                    STYLE_LINE_Data)
                                    col += 1

                                    if mv_line.analytic_account_id:
                                        worksheet.write(row, col,
                                                        mv_line.analytic_account_id.name,
                                                        STYLE_LINE_Data)
                                    else:
                                        worksheet.write(row, col, '',
                                                        STYLE_LINE_Data)
                                    col += 1
                                    if mv_line.project_site_id:
                                        worksheet.write(row, col,
                                                        mv_line.project_site_id.name,
                                                        STYLE_LINE_Data)
                                    else:
                                        worksheet.write(row, col, '',
                                                        STYLE_LINE_Data)
                                    col += 1
                                    if mv_line.account_id:
                                        worksheet.write(row, col,
                                                        str(mv_line.account_id.code) + " " + mv_line.account_id.name,
                                                        STYLE_LINE_Data)
                                    else:
                                        worksheet.write(row, col, '',
                                                        STYLE_LINE_Data)
                                    col += 1
                                    if move_ids.partner_id:
                                        worksheet.write(row, col,
                                                        move_ids.partner_id.name,
                                                        STYLE_LINE_Data)
                                    else:
                                        worksheet.write(row, col, '',
                                                        STYLE_LINE_Data)
                                    col += 1
                                    worksheet.write(row, col,
                                                    debit_ln.credit,
                                                    STYLE_LINE_Data)
                                    col += 1
                                    worksheet.write(row, col, debit_ln.debit,
                                                    STYLE_LINE_Data)
                                    col += 1
                                    worksheet.write(row, col,
                                                    abs(debit_ln.debit) + abs(
                                                        debit_ln.credit),
                                                    STYLE_LINE_Data)

                        else:
                            for move in move_ids:
                                col = 0

                                move_lines = move.invoice_line_ids
                                if len(move_lines.ids) == 1:
                                    if line.date:
                                        worksheet.write(row, col, line.date,
                                                        date_format)
                                    else:
                                        worksheet.write(row, col, '',
                                                        date_format)
                                    col += 1
                                    if line.name:
                                        worksheet.write(row, col, line.name,
                                                        STYLE_LINE_Data)
                                    else:
                                        worksheet.write(row, col, '',
                                                        STYLE_LINE_Data)
                                    col += 1
                                    if line.ref:
                                        worksheet.write(row, col, line.ref,
                                                        STYLE_LINE_Data)
                                    else:
                                        worksheet.write(row, col, '',
                                                        STYLE_LINE_Data)
                                    col += 1
                                    if debit_ln.name:
                                        worksheet.write(row, col,
                                                        debit_ln.name,
                                                        STYLE_LINE_Data)
                                    else:
                                        worksheet.write(row, col, '',
                                                        STYLE_LINE_Data)
                                    col += 1
                                    worksheet.write(row, col, move.name,
                                                    STYLE_LINE_Data)
                                    col += 1
                                    worksheet.write(row, col,
                                                    line.journal_id.name,
                                                    STYLE_LINE_Data)
                                    col += 1
                                    if move_lines.analytic_account_id:
                                        worksheet.write(row, col,
                                                        move_lines.analytic_account_id.name,
                                                        STYLE_LINE_Data)
                                    else:
                                        worksheet.write(row, col, '',
                                                        STYLE_LINE_Data)
                                    col += 1
                                    if move_lines.project_site_id:
                                        worksheet.write(row, col,
                                                        move_lines.project_site_id.name,
                                                        STYLE_LINE_Data)
                                    else:
                                        worksheet.write(row, col, '',
                                                        STYLE_LINE_Data)
                                    col += 1
                                    if move_lines.account_id:
                                        worksheet.write(row, col,
                                                        str(move_lines.account_id.code) + " " + move_lines.account_id.name,
                                                        STYLE_LINE_Data)
                                    else:
                                        worksheet.write(row, col, '',
                                                        STYLE_LINE_Data)
                                    col += 1
                                    if move.partner_id:
                                        worksheet.write(row, col,
                                                        move.partner_id.name,
                                                        STYLE_LINE_Data)
                                    else:
                                        worksheet.write(row, col, '',
                                                        STYLE_LINE_Data)
                                    col += 1
                                    worksheet.write(row, col,
                                                    debit_ln.credit,
                                                    STYLE_LINE_Data)
                                    col += 1
                                    worksheet.write(row, col, debit_ln.debit,
                                                    STYLE_LINE_Data)
                                    col += 1
                                    worksheet.write(row, col,
                                                    abs(debit_ln.debit) + abs(
                                                        debit_ln.credit),
                                                    STYLE_LINE_Data)
                                else:
                                    for mv_line in move_lines:
                                        if line.date:
                                            worksheet.write(row, col, line.date,
                                                            date_format)
                                        else:
                                            worksheet.write(row, col, '',
                                                            date_format)
                                        col += 1
                                        if line.name:
                                            worksheet.write(row, col, line.name,
                                                            STYLE_LINE_Data)
                                        else:
                                            worksheet.write(row, col, '',
                                                            STYLE_LINE_Data)
                                        col += 1
                                        if line.ref:
                                            worksheet.write(row, col, line.ref,
                                                            STYLE_LINE_Data)
                                        else:
                                            worksheet.write(row, col, '',
                                                            STYLE_LINE_Data)
                                        col += 1
                                        if debit_ln.name:
                                            worksheet.write(row, col,
                                                            debit_ln.name,
                                                            STYLE_LINE_Data)
                                        else:
                                            worksheet.write(row, col, '',
                                                            STYLE_LINE_Data)
                                        col += 1
                                        worksheet.write(row, col, move.name,
                                                        STYLE_LINE_Data)
                                        col += 1
                                        worksheet.write(row, col,
                                                        line.journal_id.name,
                                                        STYLE_LINE_Data)
                                        col += 1
                                        if mv_line.analytic_account_id:
                                            worksheet.write(row, col,
                                                            mv_line.analytic_account_id.name,
                                                            STYLE_LINE_Data)
                                        else:
                                            worksheet.write(row, col, '',
                                                            STYLE_LINE_Data)
                                        col += 1
                                        if mv_line.project_site_id:
                                            worksheet.write(row, col,
                                                            mv_line.project_site_id.name,
                                                            STYLE_LINE_Data)
                                        else:
                                            worksheet.write(row, col, '',
                                                            STYLE_LINE_Data)
                                        col += 1
                                        if mv_line.account_id:
                                            worksheet.write(row, col,
                                                            str(mv_line.account_id.code) + " " + mv_line.account_id.name,
                                                            STYLE_LINE_Data)
                                        else:
                                            worksheet.write(row, col, '',
                                                            STYLE_LINE_Data)
                                        col += 1
                                        if move.partner_id:
                                            worksheet.write(row, col,
                                                            move.partner_id.name,
                                                            STYLE_LINE_Data)
                                        else:
                                            worksheet.write(row, col, '',
                                                            STYLE_LINE_Data)
                                        col += 1
                                        worksheet.write(row, col,
                                                        debit_ln.credit,
                                                        STYLE_LINE_Data)
                                        col += 1
                                        worksheet.write(row, col,
                                                        debit_ln.debit,
                                                        STYLE_LINE_Data)
                                        col += 1
                                        worksheet.write(row, col,
                                                        abs(debit_ln.debit) + abs(
                                                            debit_ln.credit),
                                                        STYLE_LINE_Data)

                    else:
                        if line.date:
                            worksheet.write(row, col, line.date, date_format)
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
                            worksheet.write(row, col, line.ref, STYLE_LINE_Data)
                        else:
                            worksheet.write(row, col, '', STYLE_LINE_Data)
                        col += 1
                        if debit_ln.name:
                            worksheet.write(row, col, debit_ln.name,
                                            STYLE_LINE_Data)
                        else:
                            worksheet.write(row, col, '', STYLE_LINE_Data)
                        col += 1
                        worksheet.write(row, col, '',
                                        STYLE_LINE_Data)
                        col += 1
                        worksheet.write(row, col, line.journal_id.name,
                                        STYLE_LINE_Data)
                        col += 1
                        if debit_ln.analytic_account_id:
                            worksheet.write(row, col,
                                            line.analytic_account_id.name,
                                            STYLE_LINE_Data)
                        else:
                            worksheet.write(row, col, '',
                                            STYLE_LINE_Data)

                        col += 1
                        if debit_ln.project_site_id:
                            worksheet.write(row, col, line.project_site_id.name,
                                            STYLE_LINE_Data)
                        else:
                            worksheet.write(row, col, '',
                                            STYLE_LINE_Data)
                        col += 1
                        if debit_ln.account_id:
                            worksheet.write(row, col,
                                            str(debit_ln.code) + " " + debit_ln.account_id.name,
                                            STYLE_LINE_Data)
                        else:
                            worksheet.write(row, col, '',
                                            STYLE_LINE_Data)

                        col += 1
                        if debit_ln.move_id.partner_id:
                            worksheet.write(row, col,
                                            debit_ln.move_id.partner_id.name,
                                            STYLE_LINE_Data)
                        else:
                            worksheet.write(row, col, '',
                                            STYLE_LINE_Data)

                        col += 1
                        worksheet.write(row, col, debit_ln.credit,
                                        STYLE_LINE_Data)
                        col += 1
                        worksheet.write(row, col, debit_ln.debit,
                                        STYLE_LINE_Data)
                        col += 1
                        worksheet.write(row, col, abs(debit_ln.debit) + abs(
                            debit_ln.credit),
                                        STYLE_LINE_Data)
