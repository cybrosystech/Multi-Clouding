import io

from odoo import models
from odoo.tools import date_utils
from odoo.tools.safe_eval import datetime, json
import xlsxwriter


class SampleReportXLSX(models.TransientModel):
    _name = "sample.report.xlsx.wizard"

    def generate_xlsx_report(self):
        data = {

        }
        return {
            'type': 'ir.actions.report',
            'data': {'model': 'sample.report.xlsx.wizard',
                     'options': json.dumps(data,
                                           default=date_utils.json_default),
                     'output_format': 'xlsx',
                     'report_name': 'Profitability Report',
                     },
            'report_type': 'xlsx'
        }

    def get_xlsx_report(self, data, response):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet()

        sheet.set_row(3, 70)
        sheet.set_column('B3:B3', 15)

        format1 = workbook.add_format(
            {'font_size': 12, 'align': 'center', 'bg_color': '#34a4eb',
             'font_color': '#f2f7f4'})
        format2 = workbook.add_format(
            {'align': 'center', 'valign': 'vcenter', 'bg_color': '#7434eb',
             'font_color': '#f2f7f4'})
        format3 = workbook.add_format(
            {'font_size': 13, 'align': 'center', 'bg_color': '#34a4eb',
             'font_color': '#f2f7f4'})

        row = 2
        col = 2

        sheet.write('B3', 'Site Number', format1)
        sheet.write('B4', 'Site Number', format2)

        sheet.merge_range('B2:T2', 'JANUARY', format3)

        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()
