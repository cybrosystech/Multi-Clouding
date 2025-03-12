# -*- coding: utf-8 -*-
""" init object """
import base64
import io
from odoo import fields, models, _
from datetime import datetime , date
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DTF
from odoo.tools.misc import get_lang
from odoo.fields import Datetime as fieldsDatetime
import calendar

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
        date_format = get_lang(self.env).date_format
        # data = []
        # domain = [('move_id.date', '<=', self.date_to),('move_id.date', '>=', self.date_from),]
        # if self.is_posted:
        #     domain.append(('move_id.state', '=', 'posted'))
        # if self.account_ids:
        #     domain.append(('account_id', 'in', self.account_ids.ids))
        # if self.analytic_account_ids:
        #     domain.append(('analytic_account_id', 'in', self.analytic_account_ids.ids))
        # if self.leasee_contract_ids:
        #     domain += ['|', ('move_id.leasee_contract_id', 'child_of', self.leasee_contract_ids.ids)]
        #     assets = self.leasee_contract_ids.mapped('asset_id')
        #     domain += [('move_id.asset_id', 'child_of', assets.ids)]
        #
        # journal_items = self.env['account.move.line'].search(domain,order='account_id')

        ############################################3

        params = {
            'date_from': self.date_from,
            'date_to': self.date_to,
            'company_id': self.env.company.id,
        }

        query = """
            SELECT 
                am.posting_date,
                am.date AS acc_date,
                COALESCE(am.invoice_date, am.date) AS inv_date,
                am.name AS document_no,
                a.code AS account_number,
                COALESCE(a.name ->> 'en_US', '') AS account_name,
                COALESCE(SPLIT_PART(aml.name, ':', 1), p.name::TEXT, '') AS description,
                aml.amount_currency AS amount,
                COALESCE(lc.name, SPLIT_PART(aml.name, ':', 1), '') AS lease_no,
                lc.state AS lease_state,
                am.state AS move_state,
                COALESCE(aa.name ->> 'en_US', '') AS dimension_1,
                COALESCE(ps.name ->> 'en_US', '') AS dimension_2,
                '' AS dimension_3,
                '' AS dimension_4,
                c.name AS company_name,
                %(download_datetime)s AS download_datetime,
                aml.debit,
                aml.credit,
                cur.name AS Currency
            FROM account_move_line aml
            JOIN account_move am ON aml.move_id = am.id
            LEFT JOIN account_account a ON aml.account_id = a.id
            LEFT JOIN product_template p ON aml.product_id = p.id
            LEFT JOIN leasee_contract lc ON am.leasee_contract_id = lc.id
            LEFT JOIN account_analytic_account aa ON aml.analytic_account_id = aa.id
            LEFT JOIN account_analytic_account ps ON aml.project_site_id = ps.id
            LEFT JOIN res_company c ON am.company_id = c.id
            LEFT JOIN res_currency cur ON aml.currency_id = cur.id
            WHERE am.date BETWEEN %(date_from)s AND %(date_to)s AND (lc.company_id = %(company_id)s  OR lc.company_id IS NULL)
            """

        params['download_datetime'] = fieldsDatetime.now().strftime(DTF)

        # Filter for posted journal entries
        if self.is_posted:
            query += " AND am.state = 'posted'"

        # Filter for specific account_ids
        if self.account_ids:
            query += " AND aml.account_id = ANY(%(account_ids)s)"
            params['account_ids'] = self.account_ids.ids  # Direct list, PostgreSQL supports `ANY()`

        # Filter for analytic accounts
        if self.analytic_account_ids:
            query += " AND aml.analytic_account_id = ANY(%(analytic_ids)s)"
            params['analytic_ids'] = self.analytic_account_ids.ids

        # Efficiently fetch child leasee contracts and asset IDs via subqueries
        if self.leasee_contract_ids:
            leasee_contract_ids = self.env['leasee.contract'].search([
                ('id', 'child_of', self.leasee_contract_ids.ids)
            ]).ids

            asset_ids = self.env['account.asset'].search([
                ('id', 'child_of', self.leasee_contract_ids.mapped('asset_id').ids)
            ]).ids

            if leasee_contract_ids or asset_ids:
                query += " AND ("

                if leasee_contract_ids:
                    query += " am.leasee_contract_id = ANY(%(leasee_contract_ids)s)"
                    params['leasee_contract_ids'] = leasee_contract_ids

                if leasee_contract_ids and asset_ids:
                    query += " OR "

                if asset_ids:
                    query += " am.asset_id = ANY(%(asset_ids)s)"
                    params['asset_ids'] = asset_ids

                query += ")"

        # Sorting for better performance
        query += " ORDER BY aml.account_id"

        # Execute the query
        self.env.cr.execute(query, params)

        res = self.env.cr.dictfetchall()
        ############################################333
        #
        # for line in journal_items:
        #     data.append({
        #         'posting_date': line.move_id.posting_date.strftime(date_format) if line.move_id.posting_date else '',
        #         'acc_date': line.move_id.date.strftime(date_format) if line.move_id.date else '',
        #         'inv_date': line.move_id.invoice_date.strftime(date_format) if line.move_id.invoice_date else line.move_id.date.strftime(date_format),
        #         'document_no': line.move_id.name,
        #         'account_number': line.account_id.code,
        #         'account_name': line.account_id.name,
        #         'description': line.name.split(':', 1)[0] if line.name else line.product_id.name,
        #         'amount': line.amount_currency,
        #         'lease_no': line.move_id.leasee_contract_id.name if line.move_id.leasee_contract_id.name else line.name.split(':', 1)[0] if line.name else '',
        #         'lease_state': line.move_id.leasee_contract_id.state or '',
        #         'move_state': line.move_id.state or '',
        #         'dimension_1': line.analytic_account_id.name or '',
        #         'dimension_2': line.project_site_id.name or '',
        #         'dimension_3': '',
        #         'dimension_4': '',
        #         'company_name': line.company_id.name,
        #         'download_datetime': fieldsDatetime.now().strftime(DTF),
        #         'debit': line.debit,
        #         'credit': line.credit,
        #         'Currency': line.currency_id.name,
        #     })
        return res

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
        date_format = workbook.add_format({
            'border': 0,
            'align': 'left',
            'valign': 'vcenter',
            'num_format': 'dd/mm/yyyy'})

        # if report_data:
        self.add_xlsx_sheet(report_data, workbook, STYLE_LINE_Data, header_format,date_format)

        self.excel_sheet_name = 'General Ledger Posting'
        workbook.close()
        output.seek(0)
        self.excel_sheet = base64.b64encode(output.read())
        self.excel_sheet_name = str(self.excel_sheet_name) + '.xlsx'
        return {
            'type': 'ir.actions.act_url',
            'name': 'General Ledger Posting',
            'url': '/web/content/%s/%s/excel_sheet/%s?download=true' % (self._name, self.id, self.excel_sheet_name),
            'target': 'new'
        }

    def add_xlsx_sheet(self, report_data, workbook, STYLE_LINE_Data, header_format,date_format):
        self.ensure_one()
        sheet_name = f"IFRS16 GL Output file"
        worksheet = workbook.add_worksheet(sheet_name)
        lang = self.env.user.lang
        if lang.startswith('ar_'):
            worksheet.right_to_left()
        row = 0
        col = 0
        worksheet.write(row, col, _('Posting Date'), header_format)
        col += 1
        worksheet.write(row, col, _('Accounting Date'), header_format)
        col += 1
        worksheet.write(row, col, _('Invoice Date'), header_format)
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
        worksheet.write(row, col, _('Lease Status'), header_format)
        col += 1
        worksheet.write(row, col, _('Journal Status'), header_format)
        col += 1
        worksheet.write(row, col, _('Dimension 1'), header_format)
        col += 1
        worksheet.write(row, col, _('Dimension 2'), header_format)
        col += 1
        worksheet.write(row, col, _('Company Name'), header_format)
        col += 1
        worksheet.write(row, col, _('Debit'), header_format)
        col += 1
        worksheet.write(row, col, _('Credit'), header_format)
        col += 1
        worksheet.write(row, col, _('Functional Amount'), header_format)
        col += 1
        worksheet.write(row, col, _('Lease Currency'), header_format)
        for line in report_data:
            col = 0
            row += 1
            if  line['posting_date'] is not None:
                worksheet.write(row, col, line['posting_date'], date_format)
            else:
                worksheet.write(row, col, '', date_format)

            col += 1
            if  line['acc_date'] is not None:
                worksheet.write(row, col, line['acc_date'], date_format)
            else:
                worksheet.write(row, col, '', date_format)
            col += 1
            if  line['inv_date'] is not None:
                worksheet.write(row, col, line['inv_date'], date_format)
            else:
                worksheet.write(row, col, '', date_format)
            col += 1
            if line['document_no'] is not None:
                worksheet.write(row, col, line['document_no'], STYLE_LINE_Data)
            else:
                worksheet.write(row, col, '', STYLE_LINE_Data)
            col += 1
            if  line['account_number'] is not None:
                worksheet.write(row, col, line['account_number'], STYLE_LINE_Data)
            else:
                worksheet.write(row, col, '', STYLE_LINE_Data)
            col += 1
            if line['account_name'] is not None:
                worksheet.write(row, col, line['account_name'], STYLE_LINE_Data)
            else:
                worksheet.write(row, col, '', STYLE_LINE_Data)
            col += 1
            if line['description'] is not None:
                worksheet.write(row, col, line['description'], STYLE_LINE_Data)
            else:
                worksheet.write(row, col, '', STYLE_LINE_Data)
            col += 1
            if line['amount'] is not None:
                worksheet.write(row, col, line['amount'], STYLE_LINE_Data)
            else:
                worksheet.write(row, col, '', STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['lease_no'] if line['lease_no'] is not None else '', STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['lease_state'] if line['lease_state'] is not None else '', STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['move_state'] if line['move_state'] is not None else '', STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['dimension_1'] if line['dimension_1'] is not None else '', STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['dimension_2'] if line['dimension_2'] is not None else '', STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['company_name'] if line['company_name'] is not None else '', STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['debit'] if line['debit'] is not None else '', STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['credit'] if line['credit'] is not None else '', STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col,
                            line['debit'] if line['debit'] != 0 else -line[
                                'credit'], STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['currency'] if line['currency'] is not None else '', STYLE_LINE_Data)

