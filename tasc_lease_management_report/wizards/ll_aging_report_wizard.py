import base64
import io
import datetime
import xlsxwriter
from odoo import fields, models, _
from odoo.tools.safe_eval import dateutil


class LLAgingReportWizard(models.Model):
    """ Class for LL Aging report xlsx """
    _name = 'll.aging.report.wizard'
    _description = 'LL Aging Report'

    lease_contract_ids = fields.Many2many('leasee.contract',
                                          string="Lease Contract")

    end_date = fields.Date(string="As of Date",
                           default=datetime.datetime.now(), required=True)
    excel_sheet = fields.Binary('Download Report')
    excel_sheet_name = fields.Char(string='Name', size=64)

    def print_report_xlsx(self):
        """ Method for print LL Aging xlsx report"""
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

        self.excel_sheet_name = 'LL Aging Report'
        workbook.close()
        output.seek(0)
        self.excel_sheet = base64.b64encode(output.read())
        self.excel_sheet_name = str(self.excel_sheet_name) + '.xlsx'
        return {
            'type': 'ir.actions.act_url',
            'name': 'LL Aging Report',
            'url': '/web/content/%s/%s/excel_sheet/%s?download=true' % (
                self._name, self.id, self.excel_sheet_name),
            'target': 'self'
        }

    def get_report_data(self):
        data = []
        if self.lease_contract_ids:
            for contract in self.lease_contract_ids:
                liabilities = self.find_liabilities(contract)
                data.append({
                    'leasor_name': contract.name,
                    'external_reference_number': contract.external_reference_number,
                    'project_site': contract.project_site_id.name,
                    'less_than_one_year': liabilities[
                        'tot_liability_amt_less_than_1_year'],
                    'one_to_two_year': liabilities[
                        'tot_liability_amt_one_to_2_year'],
                    'two_to_five_year': liabilities[
                        'tot_liability_amt_2_to_5_year'],
                    'more_than_five_year': liabilities[
                        'tot_liability_amt_more_than_5_year'],
                    'currency': contract.leasee_currency_id.name,
                })
        else:
            lease_contract_ids = self.env['leasee.contract'].search([],
                                                                    order='id ASC')
            for contract in lease_contract_ids:
                liabilities = self.find_liabilities(contract)
                data.append({
                    'leasor_name': contract.name,
                    'external_reference_number': contract.external_reference_number,
                    'project_site': contract.project_site_id.name,
                    'less_than_one_year': liabilities[
                        'tot_liability_amt_less_than_1_year'],
                    'one_to_two_year': liabilities[
                        'tot_liability_amt_one_to_2_year'],
                    'two_to_five_year': liabilities[
                        'tot_liability_amt_2_to_5_year'],
                    'more_than_five_year': liabilities[
                        'tot_liability_amt_more_than_5_year'],
                    'currency': contract.leasee_currency_id.name,
                })
        return data

    def add_xlsx_sheet(self, report_data, workbook, STYLE_LINE_Data,
                       header_format, STYLE_LINE_HEADER):
        """ Method to add datas to the LL Aging xlsx report"""
        self.ensure_one()
        worksheet = workbook.add_worksheet(_('LL Aging Report'))
        lang = self.env.user.lang
        if lang.startswith('ar_'):
            worksheet.right_to_left()

        row = 0
        col = 0
        worksheet.merge_range(row, row, col, col + 7,
                              _('LL Aging Report'),
                              STYLE_LINE_HEADER)
        row += 1
        col = 0
        worksheet.write(row, col, _('Lease Name'), header_format)
        col += 1
        worksheet.write(row, col, _('External Reference Number'), header_format)
        col += 1
        worksheet.write(row, col, _('Project Site'), header_format)
        col += 1
        worksheet.write(row, col, _('Less Than 1 year'), header_format)
        col += 1
        worksheet.write(row, col, _('1.01 - 2 years'), header_format)
        col += 1
        worksheet.write(row, col, _('2.01 - 5 years'), header_format)
        col += 1
        worksheet.write(row, col, _('More than 5 years'), header_format)
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
            worksheet.write(row, col, line['less_than_one_year'],
                            STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['one_to_two_year'],
                            STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['two_to_five_year'],
                            STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['more_than_five_year'],
                            STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['currency'], STYLE_LINE_Data)

    def find_liabilities(self, contract):
        """
        Method to find out the liability amount for less than one year,
        1.01 - 2 years,2.01 - 5 years and more than 5 years.
        """
        total_liability_amt_less_than_1_year = 0.0
        total_liability_amt_one_to_2_year = 0.0
        total_liability_amt_2_to_5_year = 0.0
        total_liability_amt_more_than_5_year = 0.0

        for installment in contract.installment_ids:
            # Computation for Less than 1 year
            next_year_date = self.end_date + dateutil.relativedelta.relativedelta(
                years=1)
            next_year_date = next_year_date - dateutil.relativedelta.relativedelta(
                days=1)
            installments_next_year = self.env[
                'leasee.installment'].search(
                [('id', 'in', contract.installment_ids.ids),
                 ('date', '!=', False),
                 ('date', '<=', next_year_date),
                 ('date', '>=', self.end_date)])
            tot_liability_amt_less_than_1_year = 0.0
            for inst in installments_next_year:
                liability_amt = inst.amount - inst.subsequent_amount
                tot_liability_amt_less_than_1_year = tot_liability_amt_less_than_1_year + liability_amt
            total_liability_amt_less_than_1_year = tot_liability_amt_less_than_1_year

            # Computation for 1.01 -2 years
            one_to_2year_start_date = self.end_date + dateutil.relativedelta.relativedelta(
                years=1)
            one_to_2year_end_date = (self.end_date + dateutil.relativedelta.relativedelta(
                                        years=2)) - dateutil.relativedelta.relativedelta(
                days=1)
            installments_one_to_2_year = self.env[
                'leasee.installment'].search(
                [('id', 'in', contract.installment_ids.ids),
                 ('date', '!=', False),
                 ('date', '<=', one_to_2year_end_date),
                 ('date', '>=', one_to_2year_start_date)])
            tot_liability_amt_one_to_2_year = 0.0
            for inst in installments_one_to_2_year:
                liability_amt = inst.amount - inst.subsequent_amount
                tot_liability_amt_one_to_2_year = tot_liability_amt_one_to_2_year + liability_amt
            total_liability_amt_one_to_2_year = tot_liability_amt_one_to_2_year

            # Computation for 2.01 -5 years
            start_date_2_to_5_year = self.end_date + dateutil.relativedelta.relativedelta(
                years=2)
            end_date_2_to_5_year = (self.end_date + dateutil.relativedelta.relativedelta(
                                       years=5)) - dateutil.relativedelta.relativedelta(
                days=1)
            installments_2_to_5_year = self.env[
                'leasee.installment'].search(
                [('id', 'in', contract.installment_ids.ids),
                 ('date', '!=', False),
                 ('date', '<=', end_date_2_to_5_year),
                 ('date', '>=', start_date_2_to_5_year)])
            tot_liability_amt_2_to_5_year = 0.0

            for inst in installments_2_to_5_year:
                liability_amt = inst.amount - inst.subsequent_amount
                tot_liability_amt_2_to_5_year = tot_liability_amt_2_to_5_year + liability_amt
            total_liability_amt_2_to_5_year = tot_liability_amt_2_to_5_year

            # Computation for more than 5 years
            start_date_5th_year = self.end_date + dateutil.relativedelta.relativedelta(
                years=5)
            installments_more_than_5_year = self.env[
                'leasee.installment'].search(
                [('id', 'in', contract.installment_ids.ids),
                 ('date', '!=', False),
                 ('date', '>=', start_date_5th_year)])
            tot_liability_amt_more_than_5_year = 0.0

            for inst in installments_more_than_5_year:
                liability_amt = inst.amount - inst.subsequent_amount
                tot_liability_amt_more_than_5_year = tot_liability_amt_more_than_5_year + liability_amt
            total_liability_amt_more_than_5_year = tot_liability_amt_more_than_5_year
        return {
            'tot_liability_amt_less_than_1_year': total_liability_amt_less_than_1_year,
            'tot_liability_amt_one_to_2_year': total_liability_amt_one_to_2_year,
            'tot_liability_amt_2_to_5_year': total_liability_amt_2_to_5_year,
            'tot_liability_amt_more_than_5_year': total_liability_amt_more_than_5_year,
        }
