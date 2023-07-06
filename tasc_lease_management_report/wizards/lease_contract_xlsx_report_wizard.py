import base64
import io
import datetime
import xlsxwriter
from odoo import fields, models, _
from odoo.tools.safe_eval import dateutil


class LeaseContractXlsxWizard(models.TransientModel):
    """ Class for Payment Aging Report Xlsx"""
    _name = "lease.contract.xlsx.report.wizard"
    _description = "Payment Aging xlsx report"

    lease_contract_ids = fields.Many2many('leasee.contract',
                                          string="Lease Contract")
    end_date = fields.Date(string="As of Date",
                           default=datetime.datetime.now(), required=True)
    excel_sheet = fields.Binary('Download Report')
    excel_sheet_name = fields.Char(string='Name', size=64)

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

        self.excel_sheet_name = 'Payment Aging'
        workbook.close()
        output.seek(0)
        self.excel_sheet = base64.b64encode(output.read())
        self.excel_sheet_name = str(self.excel_sheet_name) + '.xlsx'
        return {
            'type': 'ir.actions.act_url',
            'name': 'Payment Aging',
            'url': '/web/content/%s/%s/excel_sheet/%s?download=true' % (
                self._name, self.id, self.excel_sheet_name),
            'target': 'self'
        }

    def get_report_data(self):
        data = []
        domain = [('move_type', '=', 'in_invoice'),
                  ('leasee_contract_id', '!=', False),
                  ('company_id', '=', self.env.company.id)]
        if self.lease_contract_ids:
            domain += [
                ('leasee_contract_id', 'in', self.lease_contract_ids.ids)]
            vendor_bills = self.env['account.move'].search(domain)
            lease_contracts = self.lease_contract_ids
            # Less than 1 year
            next_year_date = self.end_date + dateutil.relativedelta.relativedelta(
                years=1)
            next_year_date = next_year_date - dateutil.relativedelta.relativedelta(
                days=1)

            # 1.01 -  2years
            next_2year_start_date = self.end_date + dateutil.relativedelta.relativedelta(
                years=1)
            next_2year_end_date = (
                                          self.end_date + dateutil.relativedelta.relativedelta(
                                      years=2)) - dateutil.relativedelta.relativedelta(
                days=1)

            # 2.01 - 5 years
            start_date_2nd_year = self.end_date + dateutil.relativedelta.relativedelta(
                years=2)
            end_date_5th_year = (
                                        self.end_date + dateutil.relativedelta.relativedelta(
                                    years=5)) - dateutil.relativedelta.relativedelta(
                days=1)
            # More than 5 years
            start_date_5th_year = self.end_date + dateutil.relativedelta.relativedelta(
                years=5)

            for contract in lease_contracts:
                # Bills less than 1year
                move_ids_next_year = self.env['account.move'].search(
                    [('id', 'in', contract.account_move_ids.ids),
                     ('invoice_date_due', '!=', False),
                     ('invoice_date_due', '<=', next_year_date),
                     ('invoice_date_due', '>=', self.end_date)])
                # Bills from 1.01 - 2 years

                move_ids_next_two_years = self.env['account.move'].search(
                    [('id', 'in', contract.account_move_ids.ids),
                     ('invoice_date_due', '!=', False),
                     ('invoice_date_due', '<=', next_2year_end_date),
                     ('invoice_date_due', '>=', next_2year_start_date)])
                # Bills from 2.01 - 5 years

                move_ids_next_5_years = self.env['account.move'].search(
                    [('id', 'in', contract.account_move_ids.ids),
                     ('invoice_date_due', '!=', False),
                     ('invoice_date_due', '<=', end_date_5th_year),
                     ('invoice_date_due', '>=', start_date_2nd_year)])

                # Bills more than 5 years
                move_ids_more_than_5_years = self.env['account.move'].search(
                    [('id', 'in', contract.account_move_ids.ids),
                     ('invoice_date_due', '!=', False),
                     ('invoice_date_due', '>=', start_date_5th_year)])

                total_amount_next_year = sum(
                    move_ids_next_year.mapped('amount_total'))
                total_amount_next_2years = sum(
                    move_ids_next_two_years.mapped('amount_total'))
                total_amount_next_5years = sum(
                    move_ids_next_5_years.mapped('amount_total'))
                total_amount_more_than_5_years = sum(
                    move_ids_more_than_5_years.mapped('amount_total'))

                data.append({
                    'leasor_name': contract.name,
                    'external_reference_number': contract.external_reference_number,
                    'project_site': contract.project_site_id.name if contract.project_site_id else '',
                    'total_amount_next_year': total_amount_next_year,
                    'total_amount_next_2years': total_amount_next_2years,
                    'total_amount_next_5years': total_amount_next_5years,
                    'total_amount_more_than_5_years': total_amount_more_than_5_years,
                    'currency': contract.leasee_currency_id.name,
                })
        else:
            lease_contracts = self.env['leasee.contract'].search([])
            # Less than 1 year
            next_year_date = self.end_date + dateutil.relativedelta.relativedelta(
                years=1)
            next_year_date = next_year_date - dateutil.relativedelta.relativedelta(
                days=1)

            # 1.01 -  2years
            next_2year_start_date = self.end_date + dateutil.relativedelta.relativedelta(
                years=1)
            next_2year_end_date = (
                                          self.end_date + dateutil.relativedelta.relativedelta(
                                      years=2)) - dateutil.relativedelta.relativedelta(
                days=1)

            # 2.01 - 5 years
            start_date_2nd_year = self.end_date + dateutil.relativedelta.relativedelta(
                years=2)
            end_date_5th_year = (
                                        self.end_date + dateutil.relativedelta.relativedelta(
                                    years=5)) - dateutil.relativedelta.relativedelta(
                days=1)
            # More than 5 years
            start_date_5th_year = self.end_date + dateutil.relativedelta.relativedelta(
                years=5)

            for contract in lease_contracts:
                # Bills less than 1year
                move_ids_next_year = self.env['account.move'].search(
                    [('id', 'in', contract.account_move_ids.ids),
                     ('invoice_date_due', '!=', False),
                     ('invoice_date_due', '<=', next_year_date),
                     ('invoice_date_due', '>=', self.end_date)])
                # Bills from 1.01 - 2 years

                move_ids_next_two_years = self.env['account.move'].search(
                    [('id', 'in', contract.account_move_ids.ids),
                     ('invoice_date_due', '!=', False),
                     ('invoice_date_due', '<=', next_2year_end_date),
                     ('invoice_date_due', '>=', next_2year_start_date)])
                # Bills from 2.01 - 5 years

                move_ids_next_5_years = self.env['account.move'].search(
                    [('id', 'in', contract.account_move_ids.ids),
                     ('invoice_date_due', '!=', False),
                     ('invoice_date_due', '<=', end_date_5th_year),
                     ('invoice_date_due', '>=', start_date_2nd_year)])

                # Bills more than 5 years
                move_ids_more_than_5_years = self.env['account.move'].search(
                    [('id', 'in', contract.account_move_ids.ids),
                     ('invoice_date_due', '!=', False),
                     ('invoice_date_due', '>=', start_date_5th_year)])

                total_amount_next_year = sum(
                    move_ids_next_year.mapped('amount_total'))
                total_amount_next_2years = sum(
                    move_ids_next_two_years.mapped('amount_total'))
                total_amount_next_5years = sum(
                    move_ids_next_5_years.mapped('amount_total'))
                total_amount_more_than_5_years = sum(
                    move_ids_more_than_5_years.mapped('amount_total'))

                data.append({
                    'leasor_name': contract.name,
                    'external_reference_number': contract.external_reference_number,
                    'project_site': contract.project_site_id.name if contract.project_site_id else '',
                    'total_amount_next_year': total_amount_next_year,
                    'total_amount_next_2years': total_amount_next_2years,
                    'total_amount_next_5years': total_amount_next_5years,
                    'total_amount_more_than_5_years': total_amount_more_than_5_years,
                    'currency': contract.leasee_currency_id.name,
                })

        # domain += [('invoice_date_due', '<=', self.end_date),
        #            ('invoice_date_due', '!=', False)]
        # vendor_bills = self.env['account.move'].search(domain)
        # lease_contracts = vendor_bills.mapped('leasee_contract_id').search(
        #     [('company_id', '=', self.env.company.id)],
        #     order='id ASC')
        #
        # # Less than 1 year
        # next_year_date = self.end_date + dateutil.relativedelta.relativedelta(
        #     years=1)
        # next_year_date = next_year_date - dateutil.relativedelta.relativedelta(
        #     days=1)
        #
        # # 1.01 -  2years
        # next_2year_start_date = self.end_date + dateutil.relativedelta.relativedelta(
        #     years=1)
        # next_2year_end_date = (
        #                                   self.end_date + dateutil.relativedelta.relativedelta(
        #                               years=2)) - dateutil.relativedelta.relativedelta(
        #     days=1)
        #
        # # 2.01 - 5 years
        # start_date_2nd_year = self.end_date + dateutil.relativedelta.relativedelta(
        #     years=2)
        # end_date_5th_year = (
        #                                 self.end_date + dateutil.relativedelta.relativedelta(
        #                             years=5)) - dateutil.relativedelta.relativedelta(
        #     days=1)
        # # More than 5 years
        # start_date_5th_year = self.end_date + dateutil.relativedelta.relativedelta(
        #     years=5)
        #
        # for contract in lease_contracts:
        #     # Bills less than 1year
        #     move_ids_next_year = self.env['account.move'].search(
        #         [('id', 'in', contract.account_move_ids.ids),
        #          ('invoice_date_due', '!=', False),
        #          ('invoice_date_due', '<=', next_year_date),
        #          ('invoice_date_due', '>=', self.end_date)])
        #     # Bills from 1.01 - 2 years
        #
        #     move_ids_next_two_years = self.env['account.move'].search(
        #         [('id', 'in', contract.account_move_ids.ids),
        #          ('invoice_date_due', '!=', False),
        #          ('invoice_date_due', '<=', next_2year_end_date),
        #          ('invoice_date_due', '>=', next_2year_start_date)])
        #     # Bills from 2.01 - 5 years
        #
        #     move_ids_next_5_years = self.env['account.move'].search(
        #         [('id', 'in', contract.account_move_ids.ids),
        #          ('invoice_date_due', '!=', False),
        #          ('invoice_date_due', '<=', end_date_5th_year),
        #          ('invoice_date_due', '>=', start_date_2nd_year)])
        #
        #     # Bills more than 5 years
        #     move_ids_more_than_5_years = self.env['account.move'].search(
        #         [('id', 'in', contract.account_move_ids.ids),
        #          ('invoice_date_due', '!=', False),
        #          ('invoice_date_due', '>=', start_date_5th_year)])
        #
        #     total_amount_next_year = sum(
        #         move_ids_next_year.mapped('amount_total'))
        #     total_amount_next_2years = sum(
        #         move_ids_next_two_years.mapped('amount_total'))
        #     total_amount_next_5years = sum(
        #         move_ids_next_5_years.mapped('amount_total'))
        #     total_amount_more_than_5_years = sum(
        #         move_ids_more_than_5_years.mapped('amount_total'))
        #
        #     data.append({
        #         'leasor_name': contract.name,
        #         'external_reference_number': contract.external_reference_number,
        #         'project_site': contract.project_site_id.name if contract.project_site_id else '',
        #         'total_amount_next_year': total_amount_next_year,
        #         'total_amount_next_2years': total_amount_next_2years,
        #         'total_amount_next_5years': total_amount_next_5years,
        #         'total_amount_more_than_5_years': total_amount_more_than_5_years,
        #         'currency': contract.leasee_currency_id.name,
        #     })
        return data

    def add_xlsx_sheet(self, report_data, workbook, STYLE_LINE_Data,
                       header_format, STYLE_LINE_HEADER):
        self.ensure_one()
        worksheet = workbook.add_worksheet(_('Payment Aging Report'))
        lang = self.env.user.lang
        if lang.startswith('ar_'):
            worksheet.right_to_left()

        row = 0
        col = 0
        worksheet.merge_range(row, row, col, col + 7, _('Payment Aging Report'),
                              STYLE_LINE_HEADER)
        row += 1
        col = 0
        worksheet.write(row, col, _('Lease Name'), header_format)
        col += 1
        worksheet.write(row, col, _('External Reference Number'), header_format)
        col += 1
        worksheet.write(row, col, _('Project Site'), header_format)
        col += 1
        worksheet.write(row, col, _('Less than 1 year'), header_format)
        col += 1
        worksheet.write(row, col, _('1.01 - 2 years'), header_format)
        col += 1
        worksheet.write(row, col, _('2.01  - 5 years'), header_format)
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
            worksheet.write(row, col, line['total_amount_next_year'],
                            STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['total_amount_next_2years'],
                            STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['total_amount_next_5years'],
                            STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['total_amount_more_than_5_years'],
                            STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['currency'], STYLE_LINE_Data)
