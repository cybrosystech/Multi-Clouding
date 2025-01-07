import base64
import io
import datetime
import xlsxwriter
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class DefeExpWizard(models.Model):
    """ Class for TASC Prepayments Report xlsx """
    _name = 'def.exp.wizard'
    _description = 'TASC Prepayments Report'

    start_date = fields.Date(string="From Date",
                             default=datetime.datetime.now(), required=True)
    end_date = fields.Date(string="As of Date",
                           default=datetime.datetime.now(), required=True)
    company_id = fields.Many2one('res.company', 'Company',
                                 default=lambda self: self.env.company,
                                 readonly=True)
    excel_sheet = fields.Binary('Download Report')
    excel_sheet_name = fields.Char(string='Name', size=64)

    # @api.constrains('end_date')
    # def onsave_end_date(self):
    #     if self.end_date < self.start_date:
    #         raise UserError(
    #             "The end date should be greater than or equal to start date.")

    def print_report_xlsx(self):
        """ Method for print Cash Burn xlsx report"""
        journal = self.env['account.journal'].search(
            [('name', 'ilike', 'Deferred Expense')]
        )
        report_data = self.get_report_data(journal)
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
        header_format_1 = workbook.add_format({
            'bold': 0,
            'font_name': 'Aharoni',
            'border': 1,
            'font_size': 13,
            'align': 'center',
            'valign': 'vcenter',
            'font_color': 'black',
            'bg_color': '#c3c6c5',
        })
        header_format_2 = workbook.add_format({
            'bold': 1,
            'font_name': 'Aharoni',
            'border': 0,
            'font_size': 13,
            'align': 'center',
            'valign': 'vcenter',
            'font_color': '#2e4053',
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
            'align': 'center',
            'valign': 'vcenter',
            'num_format': 'dd/mm/yyyy'})

        TABLE_data_tolal_line.num_format_str = '#,##0.00'
        STYLE_LINE_Data = STYLE_LINE
        STYLE_LINE_Data.num_format_str = '#,##0.00_);(#,##0.00)'

        if report_data:
            self.add_xlsx_sheet(report_data, workbook, STYLE_LINE_Data,
                                header_format, STYLE_LINE_HEADER, journal,
                                date_format)

        self.excel_sheet_name = 'TASC Prepayments Report'
        workbook.close()
        output.seek(0)
        self.excel_sheet = base64.b64encode(output.read())
        self.excel_sheet_name = str(self.excel_sheet_name) + '.xlsx'
        return {
            'type': 'ir.actions.act_url',
            'name': 'TASC Prepayments Report',
            'url': '/web/content/%s/%s/excel_sheet/%s?download=true' % (
                self._name, self.id, self.excel_sheet_name),
            'target': 'new'
        }

    def get_report_data(self, journal):
        """Method to compute Tasc Cash Burn Report."""
        # qry = """
        # SELECT
        #     ac.name AS account_name,
        #     ac.code AS account_code,
        #     l.name AS line_name,
        #     SUM(CASE WHEN l.parent_state = 'posted' THEN l.credit ELSE 0 END) AS sum_posted_credits,
        #     SUM(CASE WHEN l.parent_state not in ('posted','cancel') THEN l.credit ELSE 0 END) AS sum_unposted_credits,
        #     SUM(CASE WHEN l.parent_state not in ('cancel') THEN l.credit ELSE 0 END)  AS total_credits,
        #     COUNT(CASE WHEN l.parent_state = 'posted' THEN 1 END) AS count_posted,
        #     COUNT(CASE WHEN l.parent_state not in ('posted','cancel') THEN 1 END) AS count_unposted,
        #     COUNT(CASE WHEN l.parent_state not in ('cancel') THEN 1 END) AS total_count,
        #     debit_ac.name AS debit_account_name,
        #     debit_ac.code AS debit_account_code,
        #     r.name AS partner_name,
        #     cc.name AS cost_center_name,
        #     cc.code AS cost_center_code,
        #     ps.name AS project_site_name,
        #     ps.code AS project_site_code,
        #     MIN(l.date) AS first_date,
        #     MAX(l.date) AS last_date
        # FROM
        #     account_move_line l
        #     INNER JOIN account_account ac ON ac.id = l.account_id
        #     LEFT JOIN account_move_line debit_l ON debit_l.move_id = l.move_id AND debit_l.debit != 0
        #     LEFT JOIN account_account debit_ac ON debit_ac.id = debit_l.account_id
        #     LEFT JOIN res_partner r ON r.id = l.partner_id
        #     LEFT JOIN account_analytic_account cc ON cc.id = l.analytic_account_id
        #     LEFT JOIN account_analytic_account ps ON ps.id = l.project_site_id
        # WHERE
        #     l.journal_id in  %(journal_id)s
        #     AND l.credit != 0
        #     AND ac.code LIKE %(ac_code_pattern)s
        #     AND  l.date<= %(end_date)s  and l.date >= %(start_date)s and l.company_id = %(company_id)s
        # GROUP BY
        #     ac.id, l.name, debit_ac.name, debit_ac.code, r.name, cc.id,ps.id
        # order by ac.id,l.name
        # """
        qry = f"""SELECT 
            ac.name AS account_name,
            ac.code AS account_code,
            l.name AS line_name,
            (SUM(
                CASE WHEN l.parent_state not in ('cancel') AND l.date<= %(end_date)s 
                THEN abs(l.debit) 
                ELSE 0 END)-SUM(
                CASE WHEN l.parent_state not in ('cancel') AND l.date<= %(end_date)s 
                THEN abs(l.credit)
                 ELSE 0 END) ) AS sum_posted_credits,
            (SUM(
                CASE WHEN l.parent_state not in ('cancel') AND l.date > %(end_date)s 
                THEN abs(l.debit) 
                ELSE 0 END)-SUM(
                CASE WHEN l.parent_state not in ('cancel') AND l.date > %(end_date)s 
                THEN abs(l.credit) 
                ELSE 0 END) ) AS sum_unposted_credits,
            (SUM(
                CASE WHEN l.parent_state not in ('cancel') 
                THEN abs(l.debit) 
                ELSE 0 END)-SUM(
                CASE WHEN l.parent_state not in ('cancel') 
                THEN abs(l.credit) 
                ELSE 0 END))  AS total_credits,
            COUNT(CASE WHEN l.parent_state not in ('cancel') AND l.date<= %(end_date)s THEN 1 END) AS count_posted,
            COUNT(CASE WHEN l.parent_state not in ('cancel') AND l.date > %(end_date)s THEN 1 END)AS count_unposted,
            COUNT(CASE WHEN l.parent_state not in ('cancel') THEN 1 END) AS total_count,
            debit_ac.name AS debit_account_name,
            debit_ac.code AS debit_account_code,
            r.name AS partner_name,
            cc.name AS cost_center_name,
            cc.code AS cost_center_code,
            ps.name AS project_site_name,
            ps.code AS project_site_code,
            MIN(l.date) AS first_date,
            MAX(l.date) AS last_date
        FROM 
            account_move_line l
            INNER JOIN account_account ac ON ac.id = l.account_id
            LEFT JOIN account_move_line debit_l ON debit_l.move_id = l.move_id 
            LEFT JOIN account_account debit_ac ON debit_ac.id = debit_l.account_id
            LEFT JOIN res_partner r ON r.id = l.partner_id
            LEFT JOIN account_analytic_account cc ON cc.id = l.analytic_account_id
            LEFT JOIN account_analytic_account ps ON ps.id = l.project_site_id
        WHERE 
            ac.code LIKE %(ac_code_pattern)s
            and l.company_id =  %(company_id)s
            and ac.id != debit_ac.id
            AND l.tax_line_id IS NULL
        GROUP BY 
            ac.id, l.name, debit_ac.name, debit_ac.code, r.name, cc.id,ps.id
        order by ac.id,l.name"""

        self._cr.execute(qry, {'start_date': self.start_date,
                               'end_date': self.end_date,
                               'journal_id': tuple(journal.ids),
                               'company_id': self.company_id.id,
                               'ac_code_pattern': '1132%',
                               })
        results = self._cr.dictfetchall()
        return results

    def add_xlsx_sheet(self, report_data, workbook, STYLE_LINE_Data,
                       header_format,
                       STYLE_LINE_HEADER, journal, date_format):
        """ Method to add datas to the Tasc Cash Burn xlsx report"""
        self.ensure_one()

        worksheet_summary = workbook.add_worksheet(_('Summary'))

        # qry = """
        #     SELECT
        #         ac.name AS account_name,
        #         ac.code AS account_code,
        #         SUM(CASE WHEN l.parent_state = 'posted' THEN l.credit ELSE 0 END) AS sum_posted_credits,
        #         SUM(CASE WHEN l.parent_state not in ('posted','cancel') THEN l.credit ELSE 0 END) AS sum_unposted_credits,
        #         SUM(CASE WHEN l.parent_state not in ('cancel') THEN l.credit ELSE 0 END)  AS total_credits
        #     FROM
        #         account_move_line l
        #         INNER JOIN account_account ac ON ac.id = l.account_id
        #     WHERE
        #          l.journal_id in  %(journal_id)s
        #          AND l.credit != 0
        #          AND ac.code LIKE %(ac_code_pattern)s
        #          AND  l.date<= %(end_date)s  and l.date >= %(start_date)s and l.company_id = %(company_id)s
        #     GROUP BY
        #         ac.id
        #     order by ac.id
        # """

        qry = f"""
                SELECT 
                ac.name AS account_name,
                ac.code AS account_code,
                (SUM(
                    CASE WHEN l.parent_state not in ('cancel') 
                    THEN abs(l.debit) 
                    ELSE 0 END)-SUM(
                    CASE WHEN l.parent_state not in ('cancel') 
                    THEN abs(l.credit) 
                    ELSE 0 END))  AS total_credits,
                (SUM(
                    CASE WHEN l.parent_state not in ('cancel') AND 
                    l.date<= %(end_date)s 
                    THEN abs(l.debit) 
                    ELSE 0 END) -SUM(
                    CASE WHEN l.parent_state not in ('cancel') AND 
                    l.date<= %(end_date)s 
                    THEN abs(l.credit) 
                    ELSE 0 END) ) AS sum_posted_credits,
                (SUM(
                    CASE WHEN l.parent_state not in ('cancel') AND 
                    l.date> %(end_date)s 
                    THEN abs(l.debit) 
                    ELSE 0 END)-SUM(
                    CASE WHEN l.parent_state not in ('cancel') AND 
                    l.date> %(end_date)s 
                    THEN abs(l.credit) 
                    ELSE 0 END))  AS sum_unposted_credits
                FROM 
                account_move_line l
                INNER JOIN account_account ac ON ac.id = l.account_id
            WHERE 
                 ac.code LIKE %(ac_code_pattern)s
                  and l.company_id =  %(company_id)s
                  	AND l.tax_line_id IS NULL
            GROUP BY 
                ac.id
            order by ac.id
        """
        self._cr.execute(qry, {'start_date': self.start_date,
                               'end_date': self.end_date,
                               'journal_id': tuple(journal.ids),
                               'company_id': self.company_id.id,
                               'ac_code_pattern': '1132%',
                               })
        res = self._cr.dictfetchall()
        row = 0
        col = 0
        worksheet_summary.merge_range(row, row, col, col + 3,
                                      _('TASC Prepayments Report - Summary'),
                                      STYLE_LINE_HEADER)
        row += 1
        col = 0
        worksheet_summary.write(row, col, _('Deferred Account'), header_format)
        col += 1
        worksheet_summary.write(row, col, _('Total Amount'), header_format)
        col += 1
        worksheet_summary.write(row, col, _('Consumed Amount Till Date'),
                                header_format)
        col += 1
        worksheet_summary.write(row, col, _('Remaining Amount'), header_format)
        row += 1

        for data in res:
            col = 0
            if data["account_name"]:
                if data["account_code"]:
                    worksheet_summary.write(row, col,
                                            data["account_code"] + "-" +
                                            data["account_name"][
                                                "en_US"], STYLE_LINE_Data)
                else:
                    worksheet_summary.write(row, col,
                                            data["account_name"][
                                                "en_US"], STYLE_LINE_Data)
            else:
                worksheet_summary.write(row, col,
                                        "", STYLE_LINE_Data)
            col += 1
            worksheet_summary.write(row, col,
                                    data["total_credits"], STYLE_LINE_Data)
            col += 1
            worksheet_summary.write(row, col,
                                    data["sum_posted_credits"], STYLE_LINE_Data)
            col += 1
            worksheet_summary.write(row, col,
                                    data["sum_unposted_credits"],
                                    STYLE_LINE_Data)
            row += 1

        worksheet = workbook.add_worksheet(_('Details'))
        lang = self.env.user.lang
        if lang.startswith('ar_'):
            worksheet.right_to_left()

        row = 0
        col = 0
        worksheet.merge_range(row, row, col, col + 13,
                              _('TASC Prepayments Report'),
                              STYLE_LINE_HEADER)
        row += 1
        col = 0
        worksheet.write(row, col, _('Deferred Account'), header_format)
        col += 1
        worksheet.write(row, col, _('Label'), header_format)
        col += 1
        worksheet.write(row, col, _('Partner'), header_format)
        col += 1
        worksheet.write(row, col, _('Cost Center'), header_format)
        col += 1
        worksheet.write(row, col, _('Project Site'), header_format)
        col += 1
        worksheet.write(row, col, _('Expense Account'), header_format)
        col += 1
        worksheet.write(row, col, _('Start Date'), header_format)
        col += 1
        worksheet.write(row, col, _('End Date'), header_format)
        col += 1
        worksheet.write(row, col, _('Total Amount' + "(" + str(
            self.company_id.currency_id.symbol) + ")"), header_format)
        col += 1
        worksheet.write(row, col, _('Consumed Amount Till Date' + "(" + str(
            self.company_id.currency_id.symbol) + ")"), header_format)
        col += 1
        worksheet.write(row, col, _('Remaining Amount' + "(" + str(
            self.company_id.currency_id.symbol) + ")"), header_format)
        col += 1
        worksheet.write(row, col, _('Total Count'), header_format)
        col += 1
        worksheet.write(row, col, _('Consumed Amount Till Date Count'),
                        header_format)
        col += 1
        worksheet.write(row, col, _('Remaining Count'), header_format)
        row += 1
        for line in report_data:
            col = 0
            if line["account_name"]:
                if line["account_code"]:
                    worksheet.write(row, col,
                                    line["account_code"] + "-" +
                                    line["account_name"][
                                        "en_US"], STYLE_LINE_Data)
                else:
                    worksheet.write(row, col,
                                    line["account_name"][
                                        "en_US"], STYLE_LINE_Data)
            else:
                worksheet.write(row, col,
                                "", STYLE_LINE_Data)
            col += 1
            if line["line_name"]:
                worksheet.write(row, col,
                                line["line_name"], STYLE_LINE_Data)
            else:
                worksheet.write(row, col,
                                "", STYLE_LINE_Data)

            col += 1
            if line["partner_name"]:
                worksheet.write(row, col,
                                line["partner_name"], STYLE_LINE_Data)
            else:
                worksheet.write(row, col,
                                " ", STYLE_LINE_Data)

            col += 1
            if line["cost_center_name"]:
                if line["cost_center_code"]:
                    worksheet.write(row, col,
                                    line["cost_center_code"] + "-" +
                                    line["cost_center_name"][
                                        "en_US"], STYLE_LINE_Data)
                else:
                    worksheet.write(row, col,
                                    line["cost_center_name"][
                                        "en_US"], STYLE_LINE_Data)
            else:
                worksheet.write(row, col,
                                "", STYLE_LINE_Data)

            col += 1
            if line["project_site_name"]:
                if line["project_site_code"]:
                    worksheet.write(row, col,
                                    line["project_site_code"] + "-" +
                                    line["project_site_name"][
                                        "en_US"], STYLE_LINE_Data)
                else:
                    worksheet.write(row, col,
                                    line["project_site_name"][
                                        "en_US"], STYLE_LINE_Data)
            else:
                worksheet.write(row, col,
                                "", STYLE_LINE_Data)

            col += 1
            if line["debit_account_name"]:
                if line["debit_account_code"]:
                    worksheet.write(row, col,
                                    line["debit_account_code"] + "-" +
                                    line["debit_account_name"][
                                        "en_US"], STYLE_LINE_Data)
                else:
                    worksheet.write(row, col,
                                    line["debit_account_name"][
                                        "en_US"], STYLE_LINE_Data)
            else:
                worksheet.write(row, col,
                                "", STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col,
                            line["first_date"], date_format)
            col += 1
            worksheet.write(row, col,
                            line["last_date"], date_format)
            col += 1
            worksheet.write(row, col,
                            line["total_credits"], STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col,
                            line["sum_posted_credits"], STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col,
                            line["sum_unposted_credits"], STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col,
                            line["total_count"], STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col,
                            line["count_posted"], STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col,
                            line["count_unposted"], )

            row += 1
