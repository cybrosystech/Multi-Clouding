import io
import xlsxwriter
from odoo import fields, models, _
from odoo.tools.safe_eval import dateutil
from odoo.tools import get_lang
from odoo import http
from odoo.http import request

class TASCIncorrectEntryReport(http.Controller):

    @http.route('/tasc_incorrect_entry_report/tasc_incorrect_entry_xlsx_report', type='http', auth='user')
    def generate_xlsx_report(self, **kwargs):
        """Generate and return an XLSX report directly from a menu item"""
        # Create an in-memory output file for the new workbook.
        output = io.BytesIO()
        # Create a new workbook and add a worksheet.
        cids = request.httprequest.cookies.get('cids', str(request.env.user.company_id.id))
        s=[int(cid) for cid in cids.split(',')]
        current_company = request.env['res.company'].browse(s[0])
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        qry=f'''
                SELECT 
                mv.name AS journal_entry_name,
                mv.state AS journal_entry_status,
                COALESCE(aj.name ->> 'en_US', '') AS journal_name,
                COALESCE(ac.name ->> 'en_US', '') AS account_name,
                ac.code as account_code,
                COALESCE(cc.name ->> 'en_US', '') AS cc_name,
                cc.code as cc_code,
                COALESCE(ps.name ->> 'en_US', '') AS ps_name,
                ps.code as ps_code,
                CASE 
                WHEN mv.company_id != cc.company_id AND mv.company_id != ps.company_id 
                    THEN 'CC and Project Site of Other Entity' 
                WHEN mv.company_id != cc.company_id 
                    THEN 'CC of Other Entity' 
                WHEN mv.company_id != ps.company_id 
                    THEN 'Project Site of Other Entity' 
                ELSE 'CC and Project Site of Same Entity' 
                END AS message 
                FROM account_move_line ml 
                LEFT JOIN account_move mv ON ml.move_id=mv.id
                LEFT JOIN account_journal aj ON mv.journal_id=aj.id 
                LEFT JOIN account_account ac ON ml.account_id=ac.id 
                LEFT  JOIN account_analytic_account cc ON ml.analytic_account_id=cc.id
                LEFT JOIN account_analytic_account ps ON ml.project_site_id=ps.id
                WHERE ml.company_id = {current_company.id}
                AND (mv.company_id != ps.company_id 
                OR mv.company_id != cc.company_id)'''
        request.env.cr.execute(qry)
        res = request.env.cr.dictfetchall()
        batch_size = 10000
        total_records = len(res)
        num_sheets = (total_records // batch_size) + (1 if total_records % batch_size > 0 else 0)
        if num_sheets == 0:
            sheet_name = f"Sheet 1"
            worksheet = workbook.add_worksheet(sheet_name)

            # Add bold format for headers
            bold = workbook.add_format({'bold': True})
            STYLE_LINE_HEADER = workbook.add_format({
                'bold': 1,
                'font_name': 'Aharoni',
                'font_size': 14,
                'border': 0,
                'align': 'center',
                'valign': 'vcenter',
                'bg_color': '#7f8eb8',
            })
            worksheet.merge_range(0, 0, 0, 6,
                                  _('Incorrect Entry Report' + " - " + current_company.name),
                                  STYLE_LINE_HEADER)
            headers = ['Journal', 'Journal Entry', 'Account', 'Cost Center', 'Project Site', 'Journal Entry Status',
                       'Message']
            for col, header in enumerate(headers):
                worksheet.write(1, col, header, bold)
        else:
            for sheet_index in range(num_sheets):
                sheet_name = f"Sheet {sheet_index + 1}"
                worksheet = workbook.add_worksheet(sheet_name)

                # Add bold format for headers
                bold = workbook.add_format({'bold': True})
                STYLE_LINE_HEADER = workbook.add_format({
                    'bold': 1,
                    'font_name': 'Aharoni',
                    'font_size': 14,
                    'border': 0,
                    'align': 'center',
                    'valign': 'vcenter',
                    'bg_color': '#7f8eb8',
                })
                worksheet.merge_range(0, 0, 0, 6,
                                      _('Incorrect Entry Report'+" - "+ current_company.name),
                                      STYLE_LINE_HEADER)
                headers = ['Journal', 'Journal Entry', 'Account', 'Cost Center', 'Project Site','Journal Entry Status', 'Message']
                for col, header in enumerate(headers):
                    worksheet.write(1, col, header, bold)

                # Get subset of data for this sheet
                start_index = sheet_index * batch_size
                end_index = min(start_index + batch_size, total_records)
                data_chunk = res[start_index:end_index]
                row = 2
                for line in data_chunk:
                    col = 0
                    worksheet.write(row, col, line["journal_name"] or '')
                    col += 1
                    worksheet.write(row, col, line["journal_entry_name"] or '')
                    col += 1

                    # Account Name + Code
                    if line["account_name"] and line["account_code"]:
                        worksheet.write(row, col, line["account_name"] + "-" + line["account_code"])
                    elif line["account_name"]:
                        worksheet.write(row, col, line["account_name"])
                    elif line["account_code"]:
                        worksheet.write(row, col, line["account_code"])
                    else:
                        worksheet.write(row, col, '')
                    col += 1

                    # Cost Center Name + Code
                    if line["cc_name"] and line["cc_code"]:
                        worksheet.write(row, col, line["cc_name"] + "-" + line["cc_code"])
                    elif line["cc_name"]:
                        worksheet.write(row, col, line["cc_name"])
                    elif line["cc_code"]:
                        worksheet.write(row, col, line["cc_code"])
                    else:
                        worksheet.write(row, col, '')
                    col += 1

                    # Project Site Name + Code
                    if line["ps_name"] and line["ps_code"]:
                        worksheet.write(row, col, line["ps_name"] + "-" + line["ps_code"])
                    elif line["ps_name"]:
                        worksheet.write(row, col, line["ps_name"])
                    elif line["ps_code"]:
                        worksheet.write(row, col, line["ps_code"])
                    else:
                        worksheet.write(row, col, '')
                    col += 1
                    if line["journal_entry_status"]:
                        worksheet.write(row, col, line["journal_entry_status"])
                    col += 1
                    # Message
                    worksheet.write(row, col, line["message"])
                    row += 1

        # Close the workbook
        workbook.close()

        # Set the file content for response
        output.seek(0)
        response = request.make_response(
            output.read(),
            headers=[
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition', 'attachment; filename="incorrect_entry_report.xlsx"')
            ]
        )
        return response

