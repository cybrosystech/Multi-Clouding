import re
import base64
import io
import datetime
import xlsxwriter
from html2text import element_style

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class BudgetAnalysisSummaryReportWizard(models.Model):
    """ Class for Budget Analysis Summary Report Wizard """
    _name = 'budget.analysis.summary'
    _description = 'Budget Analysis Summary'

    start_date = fields.Date(string="From Date",
                             default=datetime.datetime.now(), required=True)
    end_date = fields.Date(string="To Date",
                           default=datetime.datetime.now(), required=True)
    company_id = fields.Many2one('res.company', 'Company',
                                 default=lambda self: self.env.company,
                                 required=True)
    budget_ids = fields.Many2many('crossovered.budget')
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

        self.excel_sheet_name = 'Tasc Budget Analysis Summary Report'
        workbook.close()
        output.seek(0)
        self.excel_sheet = base64.b64encode(output.read())
        self.excel_sheet_name = str(self.excel_sheet_name) + '.xlsx'
        return {
            'type': 'ir.actions.act_url',
            'name': 'Tasc Budget Analysis Summary Report',
            'url': '/web/content/%s/%s/excel_sheet/%s?download=true' % (
                self._name, self.id, self.excel_sheet_name),
            'target': 'new'
        }

    def get_report_data(self):
        """Method to computeTasc Budget Analysis Summary Report."""
        domain = [
            ('date_from', '>=', self.start_date),
            ('date_to', '<=', self.end_date),
            ('company_id', '=', self.company_id.id),
        ]
        # Define the fields to group by and aggregate
        fields = [
            'project_site_id',  # To group by project site
            'analytic_account_id',  # To group by analytic account
            'planned_amount:sum',  # Sum of planned_amount
            'practical_demo:sum',  # Sum of practical_demo
            'crossovered_budget_id',  # To group by budget id
            'general_budget_id',  # To group by budgetary position (budget post)
            'analytic_account_id',  # To group by cost center
            'project_site_id',  # To group by project site
            'crossovered_budget_id',  # To group by budget name
            'company_id',  # To group by company currency
        ]

        # Define the groupby fields
        groupby = [
            'crossovered_budget_id',  # Budget id
            'general_budget_id',  # Budgetary position
            'analytic_account_id',  # Cost center
            'project_site_id',  # Project site
            'company_id',  # Company currency
        ]

        # Perform the read_group operation
        records = self.env['crossovered.budget.lines'].read_group(
            domain=domain,
            fields=fields,
            groupby=groupby,
            orderby='crossovered_budget_id,general_budget_id',
            lazy=False
        )
        return records

    def add_xlsx_sheet(self, report_data, workbook, STYLE_LINE_Data,
                       header_format, STYLE_LINE_HEADER, date_format):
        """ Method to add datas to the Tasc Budget Analysis Summary  report"""
        self.ensure_one()
        worksheet = workbook.add_worksheet(
            _('Tasc Budget Analysis Summary Report'))
        lang = self.env.user.lang
        if lang.startswith('ar_'):
            worksheet.right_to_left()

        row = 0
        col = 0
        worksheet.merge_range(row, row, col, col + 6,
                              _('Tasc Budget Analysis Summary Report ( From: '+str(self.start_date) +" To: "+str(self.end_date)+" )"),
                              STYLE_LINE_HEADER)
        row += 1
        col = 0
        worksheet.write(row, col, _('Budget'), header_format)
        col += 1
        worksheet.write(row, col, _('Budgetory Position'), header_format)
        col += 1
        worksheet.write(row, col, _('Cost Center'), header_format)
        col += 1
        worksheet.write(row, col, _('Project Site'), header_format)
        col += 1
        worksheet.write(row, col, _('Planned Amount'), header_format)
        col += 1
        worksheet.write(row, col, _('Practical Amount'), header_format)
        col += 1
        worksheet.write(row, col, _('Remaining Amount'), header_format)
        row += 1

        for line in report_data:
            col = 0
            if line.get('crossovered_budget_id'):
                worksheet.write(row, col,
                                line.get('crossovered_budget_id', False)[1],
                                STYLE_LINE_Data)
            else:
                worksheet.write(row, col,
                                '',
                                STYLE_LINE_Data)
            col += 1
            if  line.get('general_budget_id', False):
                worksheet.write(row, col,
                                line.get('general_budget_id', False)[1],
                                STYLE_LINE_Data)
            else:
                worksheet.write(row, col,
                                '',
                                STYLE_LINE_Data)

            col += 1
            if line.get('analytic_account_id', False):
                worksheet.write(row, col,
                                line.get('analytic_account_id', False)[1],
                                STYLE_LINE_Data)
            else:
                worksheet.write(row, col,
                                '',
                                STYLE_LINE_Data)
            col += 1
            if line.get('project_site_id', False):
                worksheet.write(row, col,
                                line.get('project_site_id', False)[1],
                                STYLE_LINE_Data)
            else:
                worksheet.write(row, col,
                                '',
                                STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col,
                            line.get('planned_amount', 0),
                            STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col,
                            line.get('practical_demo', 0),
                            STYLE_LINE_Data)
            col += 1
            remaining_amount = line.get('planned_amount', 0) - line.get('practical_demo', 0)
            worksheet.write(row, col,
                           remaining_amount,
                            STYLE_LINE_Data)

            row += 1
