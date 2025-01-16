import base64
import io
import re
import xlsxwriter
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.safe_eval import datetime


class TascCrossJournalItems(models.TransientModel):
    _name = 'tasc.cross.journal.items'
    _description = 'TASC Cross Journal Items Report'

    start_date = fields.Date(string="From Date",
                             default=datetime.datetime.now(), required=True)
    end_date = fields.Date(string="To Date",
                           default=datetime.datetime.now(), required=True)
    account_ids = fields.Many2many('account.account',
                                   'account_cross_journal_items_rel',
                                   required=True)

    analytic_account_ids = fields.Many2many('account.analytic.account',
                                            'cross_centers_journal_items_rel',
                                            string="Cost center",
                                            )

    project_site_ids = fields.Many2many('account.analytic.account',
                                        'project_sites_journal_items_rel',
                                        )

    company_id = fields.Many2one('res.company', 'Company',
                                 default=lambda self: self.env.company,
                                 required=True)
    state = fields.Selection(
        [('draft', 'Draft'), ('to_approve', 'To Approve'), ('posted', 'Posted'),
         ('cancel', 'Cancelled')], required=True,
        default='posted')
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


        self.add_xlsx_sheet(report_data, workbook, STYLE_LINE_Data,
                            header_format, STYLE_LINE_HEADER, date_format)

        self.excel_sheet_name = 'TASC Cross Journal Items Report'
        workbook.close()
        output.seek(0)
        self.excel_sheet = base64.b64encode(output.read())
        self.excel_sheet_name = str(self.excel_sheet_name) + '.xlsx'
        return {
            'type': 'ir.actions.act_url',
            'name': 'TASC Cross Journal Items Report',
            'url': '/web/content/%s/%s/excel_sheet/%s?download=true' % (
                self._name, self.id, self.excel_sheet_name),
            'target': 'new'
        }

    def get_report_data(self):
        """Method to compute TASC Cross Journal Items Report."""
        domain = [('parent_state', '=', self.state),
             ('date', '>=', self.start_date), ('date', '<=', self.end_date),
             ('company_id', '=', self.company_id.id),
             ('account_id', 'in', self.account_ids.ids)]
        if self.analytic_account_ids:
            domain.append(('analytic_account_id', 'in', self.analytic_account_ids.ids))
        if self.project_site_ids:
            domain.append(('project_site_id', 'in', self.project_site_ids.ids))
        move_ids = self.env['account.move.line'].search(domain,
                                                        order="id asc").mapped(
            'move_id')
        return move_ids

    def add_xlsx_sheet(self, report_data, workbook, STYLE_LINE_Data,
                       header_format, STYLE_LINE_HEADER, date_format):
        """ Method to add datas to the TASC Cross Journal Items Report"""
        self.ensure_one()
        worksheet = workbook.add_worksheet(_('TASC Cross Journal Items Report'))
        lang = self.env.user.lang
        if lang.startswith('ar_'):
            worksheet.right_to_left()

        row = 0
        col = 0
        worksheet.merge_range(row, row, col, col + 11,
                              _('TASC Cross Journal Items Report'),
                              STYLE_LINE_HEADER)
        row += 1
        col = 0
        worksheet.write(row, col, _('Account Code'), header_format)
        col += 1
        worksheet.write(row, col, _('Account'), header_format)
        col += 1
        worksheet.write(row, col, _('Journal Entry Number'), header_format)
        col += 1
        worksheet.write(row, col, _('Date'), header_format)
        col += 1
        worksheet.write(row, col, _('Label'), header_format)
        col += 1
        worksheet.write(row, col, _('Cost Center'), header_format)
        col += 1
        worksheet.write(row, col, _('Project Site'), header_format)
        col += 1
        worksheet.write(row, col, _('Partner'), header_format)
        col += 1
        worksheet.write(row, col, _('Currency'), header_format)
        col += 1
        worksheet.write(row, col, _('Amount in Currency'), header_format)
        col += 1
        worksheet.write(row, col, _('Debit'), header_format)
        col += 1
        worksheet.write(row, col, _('Credit'), header_format)
        col += 1
        row += 1
        for move in report_data:
            if self.analytic_account_ids and self.project_site_ids:
                lines = move.line_ids.filtered(lambda x:x.analytic_account_id.id in self.analytic_account_ids.ids and x.project_site_id.id in self.project_site_ids.ids)
            elif self.analytic_account_ids:
                lines = move.line_ids.filtered(lambda
                                                   x: x.analytic_account_id.id in self.analytic_account_ids.ids)
            elif self.project_site_ids:
                lines = move.line_ids.filtered(lambda
                                                   x: x.project_site_id.id in self.project_site_ids.ids)
            else:
                lines = move.line_ids
            for line in lines:
                col = 0

                worksheet.write(row, col,
                                line.account_id.code if line.account_id.code else False,
                                STYLE_LINE_Data)
                col += 1
                if line.account_id.name and line.account_id.code:
                    worksheet.write(row, col,
                                    line.account_id.code + "-" + line.account_id.name,
                                    STYLE_LINE_Data)
                elif line.account_id.name:
                    worksheet.write(row, col,
                                    line.account_id.name,
                                    STYLE_LINE_Data)
                else:
                    worksheet.write(row, col,
                                    '',
                                    STYLE_LINE_Data)
                col += 1
                worksheet.write(row, col,
                                line.move_id.name if line.move_id else '',
                                STYLE_LINE_Data)
                col += 1
                worksheet.write(row, col,
                                line.move_id.date if line.move_id.date else '',
                                date_format)
                col += 1
                worksheet.write(row, col, line.name if line.name else '',
                                STYLE_LINE_Data)
                col += 1
                if line.analytic_account_id.name and line.analytic_account_id.code:
                    worksheet.write(row, col,
                                    line.analytic_account_id.code + "-" + line.analytic_account_id.name,
                                    STYLE_LINE_Data)
                elif line.analytic_account_id.name:
                    worksheet.write(row, col, line.analytic_account_id.name,
                                    STYLE_LINE_Data)
                else:
                    worksheet.write(row, col, '',
                                    STYLE_LINE_Data)
                col += 1
                if line.project_site_id.name and line.project_site_id.code:
                    worksheet.write(row, col,
                                    line.project_site_id.code + "-" + line.project_site_id.name,
                                    STYLE_LINE_Data)
                elif line.project_site_id.name:
                    worksheet.write(row, col, line.project_site_id.name,
                                    STYLE_LINE_Data)
                else:
                    worksheet.write(row, col, '',
                                    STYLE_LINE_Data)
                col += 1
                worksheet.write(row, col,
                                line.move_id.partner_id.name if line.move_id.partner_id.name else '',
                                STYLE_LINE_Data)
                col += 1
                worksheet.write(row, col,
                                line.currency_id.name if line.currency_id else '',
                                STYLE_LINE_Data)
                col += 1
                worksheet.write(row, col, line.amount_currency,
                                STYLE_LINE_Data)
                col += 1
                worksheet.write(row, col, line.debit,
                                STYLE_LINE_Data)
                col += 1
                worksheet.write(row, col, line.credit,
                                STYLE_LINE_Data)
                row += 1
        worksheet2 = workbook.add_worksheet(_('Parameters'))
        lang = self.env.user.lang
        if lang.startswith('ar_'):
            worksheet2.right_to_left()

        r = 2
        c = 2
        worksheet2.write(r, c, _('Company'), header_format)
        c += 1
        worksheet2.write(r, c, self.company_id.name, STYLE_LINE_Data)
        r += 1
        c = 2
        worksheet2.write(r, c, _('From Date'), header_format)
        c += 1
        worksheet2.write(r, c, self.start_date, date_format)
        r += 1
        c = 2
        worksheet2.write(r, c, _('To Date'), header_format)
        c += 1
        worksheet2.write(r, c, self.end_date, date_format)
        r += 1
        c = 2
        worksheet2.write(r, c, _('Status'), header_format)
        c += 1
        worksheet2.write(r, c, self.state, STYLE_LINE_Data)
        r += 1
        c = 2
        worksheet2.write(r, c, _('Accounts'), header_format)
        c += 1
        worksheet2.write(r, c,
                         ', '.join(self.account_ids.mapped('display_name')),
                         STYLE_LINE_Data)
        r += 1
        c = 2
        worksheet2.write(r, c, _('Cost Centers'), header_format)
        c += 1
        worksheet2.write(r, c,', '.join(self.analytic_account_ids.mapped('display_name')) if self.project_site_ids else '', STYLE_LINE_Data)
        r += 1
        c = 2
        worksheet2.write(r, c, _('Project Sites'), header_format)
        c += 1
        worksheet2.write(r, c,
                         ', '.join(self.project_site_ids.mapped('display_name')) if self.project_site_ids else '',
                         STYLE_LINE_Data)
