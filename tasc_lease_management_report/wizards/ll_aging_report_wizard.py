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
                    'project_site': contract.project_site_id.name if contract.project_site_id else '',
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
                    'project_site': contract.project_site_id.name if contract.project_site_id else '',
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
        # Computation for Less than 1 year
        next_year_date = self.end_date + dateutil.relativedelta.relativedelta(
            years=1)
        less_than_1_year_start_date = self.end_date + dateutil.relativedelta.relativedelta(
            days=1)
        domain_less_than_1_yr = [('move_id.date', '<=', next_year_date),
                                 ('move_id.date', '>=',
                                  less_than_1_year_start_date),
                                 ('move_id.leasee_contract_id', '=',
                                  contract.id),
                                 ('account_id', '=',
                                  contract.interest_expense_account_id.id),
                                 '|', ('move_id.leasee_contract_id', '=',
                                       contract.id),
                                 (
                                     'move_id.asset_id', '=',
                                     contract.asset_id.id)]
        journal_items_less_than_1_yr = self.env['account.move.line'].search(
            domain_less_than_1_yr, order='account_id')
        installments_less_than_1_year = self.env['leasee.installment'].search(
            [('id', 'in', contract.installment_ids.ids),
             ('date', '<=', next_year_date),
             ('date', '>=', less_than_1_year_start_date)]).mapped('amount')
        installmet_amount_less_than_1_year = sum(installments_less_than_1_year)
        total_liability_amt_less_than_1_year = installmet_amount_less_than_1_year - sum(
            journal_items_less_than_1_yr.mapped('amount_currency'))

        # Computation for 1.01 -2 years
        one_to_2year_start_date = self.end_date + dateutil.relativedelta.relativedelta(
            years=1)
        one_to_2year_start_date = one_to_2year_start_date + dateutil.relativedelta.relativedelta(
            days=1)
        one_to_2year_end_date = (
                self.end_date + dateutil.relativedelta.relativedelta(
            years=2))

        domain_one_to_2_year = [('move_id.date', '<=', one_to_2year_end_date),
                                ('move_id.date', '>=', one_to_2year_start_date),
                                (
                                    'move_id.leasee_contract_id', '=',
                                    contract.id),
                                ('account_id', '=',
                                 contract.interest_expense_account_id.id),
                                '|', (
                                    'move_id.leasee_contract_id', '=',
                                    contract.id),
                                ('move_id.asset_id', '=', contract.asset_id.id)]

        journal_items_one_to_2_year = self.env['account.move.line'].search(
            domain_one_to_2_year, order='account_id')

        installments_one_to_2_year = self.env['leasee.installment'].search(
            [('id', 'in', contract.installment_ids.ids),
             ('date', '<=', one_to_2year_end_date),
             ('date', '>=', one_to_2year_start_date)]).mapped('amount')

        installmet_amount_one_to_2_year = sum(installments_one_to_2_year)
        total_liability_amt_one_to_2_year = installmet_amount_one_to_2_year - sum(
            journal_items_one_to_2_year.mapped('amount_currency'))

        # Computation for 2.01 -5 years
        start_date_2_to_5_year = self.end_date + dateutil.relativedelta.relativedelta(
            years=2)
        start_date_2_to_5_year = start_date_2_to_5_year + dateutil.relativedelta.relativedelta(
            days=1)
        end_date_2_to_5_year = (
                self.end_date + dateutil.relativedelta.relativedelta(
            years=5))
        domain_2_to_5_year = [('move_id.date', '<=', end_date_2_to_5_year),
                              ('move_id.date', '>=', start_date_2_to_5_year),
                              ('move_id.leasee_contract_id', '=', contract.id),
                              ('account_id', '=',
                               contract.interest_expense_account_id.id),
                              '|',
                              ('move_id.leasee_contract_id', '=', contract.id),
                              ('move_id.asset_id', '=', contract.asset_id.id)]

        journal_items_2_to_5_year = self.env['account.move.line'].search(
            domain_2_to_5_year, order='account_id')

        installments_2_to_5_year = self.env['leasee.installment'].search(
            [('id', 'in', contract.installment_ids.ids),
             ('date', '<=', end_date_2_to_5_year),
             ('date', '>=', start_date_2_to_5_year)]).mapped('amount')

        installmet_amount_2_to_5_year = sum(installments_2_to_5_year)

        total_liability_amt_2_to_5_year = installmet_amount_2_to_5_year - sum(
            journal_items_2_to_5_year.mapped('amount_currency'))

        # Computation for more than 5 years
        start_date_5th_year = self.end_date + dateutil.relativedelta.relativedelta(
            years=5)
        start_date_5th_year = start_date_5th_year + dateutil.relativedelta.relativedelta(
            days=1)
        domain_more_than_5_year = [
            ('move_id.date', '>=', start_date_5th_year),
            ('move_id.leasee_contract_id', '=', contract.id),
            ('account_id', '=', contract.interest_expense_account_id.id),
            '|', ('move_id.leasee_contract_id', '=', contract.id),
            ('move_id.asset_id', '=', contract.asset_id.id)]

        journal_items_more_than_5_year = self.env['account.move.line'].search(
            domain_more_than_5_year, order='account_id')

        installments_more_than_5_year = self.env['leasee.installment'].search(
            [('id', 'in', contract.installment_ids.ids),
             ('date', '>=', start_date_5th_year)]).mapped('amount')

        installmet_amount_more_than_5_year = sum(installments_more_than_5_year)

        total_liability_amt_more_than_5_year = installmet_amount_more_than_5_year - sum(
            journal_items_more_than_5_year.mapped('amount_currency'))

        return {
            'tot_liability_amt_less_than_1_year': total_liability_amt_less_than_1_year,
            'tot_liability_amt_one_to_2_year': total_liability_amt_one_to_2_year,
            'tot_liability_amt_2_to_5_year': total_liability_amt_2_to_5_year,
            'tot_liability_amt_more_than_5_year': total_liability_amt_more_than_5_year,
        }
