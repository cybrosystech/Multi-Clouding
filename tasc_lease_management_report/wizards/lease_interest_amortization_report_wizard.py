import base64
import datetime
import io
import xlsxwriter

from odoo import fields, models, _


class LeaseInterestAndAmortizationReportWizard(models.TransientModel):
    """
    Class for lease interest and amortization report xlsx.
    """
    _name = 'lease.interest.amortization.report.wizard'
    _description = "Lease Interest and Amortization Report"

    lease_contract_ids = fields.Many2many('leasee.contract',
                                          string="Lease Contract")
    start_date = fields.Date(string="Date From",
                             required=True)
    end_date = fields.Date(string="Date To",
                           default=datetime.datetime.now(), required=True)
    excel_sheet = fields.Binary('Download Report')
    excel_sheet_name = fields.Char(string='Name', size=64)
    state = fields.Selection(string="Status",
                             selection=[('draft', 'Draft'),
                                        ('posted', 'Posted'),
                                        ('cancel', 'Cancelled')])

    def print_report_xlsx(self):
        """Method to print xlsx report based on the selected parameters."""
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

        TABLE_data_tolal_line.num_format_str = '#,##0.00'
        STYLE_LINE_Data = STYLE_LINE
        STYLE_LINE_Data.num_format_str = '#,##0.00_);(#,##0.00)'

        if report_data:
            self.add_xlsx_sheet(report_data, workbook, STYLE_LINE_Data,
                                header_format, STYLE_LINE_HEADER)

        self.excel_sheet_name = 'Lease interest and amortization report'
        workbook.close()
        output.seek(0)
        self.excel_sheet = base64.b64encode(output.read())
        self.excel_sheet_name = str(self.excel_sheet_name) + '.xlsx'
        return {
            'type': 'ir.actions.act_url',
            'name': 'Lease Interest and Amortization Report',
            'url': '/web/content/%s/%s/excel_sheet/%s?download=true' % (
                self._name, self.id, self.excel_sheet_name),
            'target': 'self'
        }

    def get_report_data(self):
        data = []
        # move_line = self.env['account.move.line']
        if self.lease_contract_ids:
            lease_contract_ids = self.lease_contract_ids
        else:
            lease_contract_ids = self.env['leasee.contract'].search(
                [('company_id', '=', self.env.company.id),
                 ('account_move_ids', '!=', False)], order='id ASC')

        for contract in lease_contract_ids:
            amortization_amount = 0.0
            interest_amount = 0.0
            amortization_move_line_ids = []
            # computation for the interest and amortization
            if self.state:
                self._cr.execute(
                    'SELECT sum(credit) as credit,sum(debit) as debit FROM '
                    'account_move_line WHERE move_id IN  %(move_ids)s and '
                    'move_id in (select id from account_move where '
                    'move_type=%(move_type)s and date >= %(start_date)s and '
                    'date <= %(end_date)s and state=%(state)s) and '
                    'account_id=%(account)s',
                    {'move_ids': tuple(contract.account_move_ids.ids),
                     'move_type': 'entry',
                     'start_date': self.start_date,
                     'end_date': self.end_date,
                     'state': self.state,
                     'account': contract.interest_expense_account_id.id})
                move_line_ids = self._cr.dictfetchall()
                if contract.asset_id.depreciation_move_ids:
                    self._cr.execute(
                        'SELECT sum(credit) as credit,sum(debit) as debit FROM '
                        'account_move_line WHERE move_id IN  %(move_ids)s and '
                        'move_id in (select id from account_move where '
                        'date >= %(start_date)s and date <= %(end_date)s and '
                        'state=%(state)s) and account_id=%(account)s',
                        {'move_ids': tuple(
                            contract.asset_id.depreciation_move_ids.ids),
                            'start_date': self.start_date,
                            'end_date': self.end_date,
                            'state': self.state,
                            'account': contract.asset_id.account_depreciation_expense_id.id})
                    amortization_move_line_ids = self._cr.dictfetchall()

            else:
                self._cr.execute(
                    'SELECT sum(credit) as credit,sum(debit) as debit FROM '
                    'account_move_line WHERE move_id IN  %(move_ids)s and '
                    'move_id in (select id from account_move where '
                    'move_type=%(move_type)s and date >= %(start_date)s and '
                    'date <= %(end_date)s) and account_id=%(account)s',
                    {'move_ids': tuple(contract.account_move_ids.ids),
                     'move_type': 'entry',
                     'start_date': self.start_date,
                     'end_date': self.end_date,
                     'account': contract.interest_expense_account_id.id})
                move_line_ids = self._cr.dictfetchall()

                if contract.asset_id.depreciation_move_ids:
                    self._cr.execute(
                        'SELECT sum(credit) as credit,sum(debit) as debit FROM '
                        'account_move_line WHERE move_id IN  %(move_ids)s and '
                        'move_id in (select id from account_move where '
                        'date >= %(start_date)s and date <= %(end_date)s) and '
                        'account_id=%(account)s',
                        {'move_ids': tuple(
                            contract.asset_id.depreciation_move_ids.ids),
                            'start_date': self.start_date,
                            'end_date': self.end_date,
                            'account': contract.asset_id.account_depreciation_expense_id.id})
                    amortization_move_line_ids = self._cr.dictfetchall()

            if move_line_ids[0]["credit"] and move_line_ids[0]["debit"]:
                interest_amount = move_line_ids[0]["credit"] + \
                                  move_line_ids[0]["debit"]
            elif move_line_ids[0]["credit"]:
                interest_amount = move_line_ids[0]["credit"]
            elif move_line_ids[0]["debit"]:
                interest_amount = move_line_ids[0]["debit"]
            else:
                interest_amount = 0.0

            if len(amortization_move_line_ids) >0:
                if amortization_move_line_ids[0]["credit"] and \
                        amortization_move_line_ids[0]["debit"]:
                    amortization_amount = amortization_move_line_ids[0][
                                              "credit"] + \
                                          amortization_move_line_ids[0]["debit"]
                elif amortization_move_line_ids[0]["credit"]:
                    amortization_amount = amortization_move_line_ids[0][
                        "credit"]
                elif amortization_move_line_ids[0]["debit"]:
                    amortization_amount = amortization_move_line_ids[0]["debit"]
                else:
                    amortization_amount = 0.0
            else:
                amortization_amount = 0.0

            data.append({
                'leasor_name': contract.name,
                'external_reference_number': contract.external_reference_number,
                'project_site': contract.project_site_id.name if contract.project_site_id else '',
                'interest': interest_amount,
                'amortization': amortization_amount,
                'currency': contract.leasee_currency_id.name,
            })
        return data

    def add_xlsx_sheet(self, report_data, workbook, STYLE_LINE_Data,
                       header_format, STYLE_LINE_HEADER):
        self.ensure_one()
        worksheet = workbook.add_worksheet(
            _('Lease Interest and Amortization Report'))
        lang = self.env.user.lang
        if lang.startswith('ar_'):
            worksheet.right_to_left()

        row = 0
        col = 0
        worksheet.merge_range(row, row, col, col + 5,
                              _('Lease Interest and Amortization Report'),
                              STYLE_LINE_HEADER)
        row += 1
        col = 0
        worksheet.write(row, col, _('Lease Name'), header_format)
        col += 1
        worksheet.write(row, col, _('External Reference Number'), header_format)
        col += 1
        worksheet.write(row, col, _('Project Site'), header_format)
        col += 1
        worksheet.write(row, col, _('Interest'), header_format)
        col += 1
        worksheet.write(row, col, _('Amortization'), header_format)
        col += 1
        worksheet.write(row, col, _('Currency'), header_format)
        col += 1
        for line in report_data:
            col = 0
            row += 1
            worksheet.write(row, col, line['leasor_name'], STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['external_reference_number'],
                            STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['project_site'], STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['interest'],
                            STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['amortization'],
                            STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['currency'], STYLE_LINE_Data)
