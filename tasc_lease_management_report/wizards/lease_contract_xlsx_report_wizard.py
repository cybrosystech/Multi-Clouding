import base64
import io
import datetime
from operator import itemgetter

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
        if self.lease_contract_ids:
            lease_contracts = self.lease_contract_ids
        else:
            lease_contracts = self.env['leasee.contract'].search(
                [('company_id', '=', self.env.company.id)])

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
        if lease_contracts:
            # Less than 1 year

            self._cr.execute(
                'select sum(journal.amount_total) total, leasee.id as lease_id,'
                'leasee.name as lease_name,'
                'leasee.external_reference_number,currency.name as currency_name,'
                'project_site.name from leasee_contract as leasee inner'
                ' join account_move  as journal on '
                'journal.leasee_contract_id=leasee.id inner join '
                'res_currency as currency on '
                'currency.id=leasee.leasee_currency_id left join '
                'account_analytic_account as project_site on '
                'project_site.id=leasee.project_site_id where '
                'leasee.id in %(contract)s and '
                'journal.invoice_date_due <= %(end_date)s and ' \
                'journal.invoice_date_due >=  %(start_date)s group by ' \
                'lease_id,leasee.external_reference_number,' \
                'currency_name,project_site.name ',
                {'contract': tuple(lease_contracts.ids),
                 'end_date': next_year_date,
                 'start_date': self.end_date})

            move_ids_next_year_qry = self._cr.dictfetchall()
            less_than_1_year_lease_names = list(
                map(itemgetter('lease_name'), move_ids_next_year_qry))

            # 1.01 -  2years
            self._cr.execute(
                'select sum(journal.amount_total) total, leasee.id as lease_id,'
                'leasee.name as lease_name,'
                'leasee.external_reference_number,currency.name as currency_name,'
                'project_site.name from leasee_contract as leasee inner'
                ' join account_move  as journal on '
                'journal.leasee_contract_id=leasee.id inner join '
                'res_currency as currency on '
                'currency.id=leasee.leasee_currency_id left join '
                'account_analytic_account as project_site on '
                'project_site.id=leasee.project_site_id where '
                'leasee.id in %(contract)s and '
                'journal.invoice_date_due <= %(end_date)s and ' \
                'journal.invoice_date_due >=  %(start_date)s group by ' \
                'lease_id,leasee.external_reference_number,' \
                'currency_name,project_site.name ',
                {'contract': tuple(lease_contracts.ids),
                 'end_date': next_2year_end_date,
                 'start_date': next_2year_start_date})

            move_ids_next_two_years_qry = self._cr.dictfetchall()
            one_to_2_year_lease_names = list(
                map(itemgetter('lease_name'), move_ids_next_two_years_qry))

            # 2.01 - 5 years
            self._cr.execute(
                'select sum(journal.amount_total) total, leasee.id as lease_id,'
                'leasee.name as lease_name,'
                'leasee.external_reference_number,currency.name as currency_name,'
                'project_site.name from leasee_contract as leasee inner'
                ' join account_move  as journal on '
                'journal.leasee_contract_id=leasee.id inner join '
                'res_currency as currency on '
                'currency.id=leasee.leasee_currency_id left join '
                'account_analytic_account as project_site on '
                'project_site.id=leasee.project_site_id where '
                'leasee.id in %(contract)s and '
                'journal.invoice_date_due <= %(end_date)s and ' \
                'journal.invoice_date_due >=  %(start_date)s group by ' \
                'lease_id,leasee.external_reference_number,' \
                'currency_name,project_site.name ',
                {
                    'contract': tuple(lease_contracts.ids),
                    'end_date': end_date_5th_year,
                    'start_date': start_date_2nd_year})

            move_ids_next_5_years_qry = self._cr.dictfetchall()
            two_to_5_year_lease_names = list(
                map(itemgetter('lease_name'), move_ids_next_5_years_qry))

            # More than 5 years
            self._cr.execute(
                'select sum(journal.amount_total) total, leasee.id as lease_id,'
                'leasee.name as lease_name,'
                'leasee.external_reference_number,currency.name as currency_name,'
                'project_site.name from leasee_contract as leasee inner'
                ' join account_move  as journal on '
                'journal.leasee_contract_id=leasee.id inner join '
                'res_currency as currency on '
                'currency.id=leasee.leasee_currency_id left join '
                'account_analytic_account as project_site on '
                'project_site.id=leasee.project_site_id where '
                'leasee.id in %(contract)s and '
                'journal.invoice_date_due >=  %(start_date)s group by ' \
                'lease_id,leasee.external_reference_number,' \
                'currency_name,project_site.name ',
                {
                    'contract': tuple(lease_contracts.ids),
                    'start_date': start_date_5th_year})
            move_ids_more_than_5_years_qry = self._cr.dictfetchall()
            more_than__5_year_lease_names = list(
                map(itemgetter('lease_name'), move_ids_more_than_5_years_qry))
            lease_names = list(
                set(less_than_1_year_lease_names + one_to_2_year_lease_names + two_to_5_year_lease_names + more_than__5_year_lease_names))
            lease_names.sort()

            amount_lists = []
            for lease in lease_names:
                amount_less_than_1_year = list(
                    filter(lambda x: x['lease_name'] == lease,
                           move_ids_next_year_qry))
                amount_1_to_2_year = list(
                    filter(lambda x: x['lease_name'] == lease,
                           move_ids_next_two_years_qry))
                amount_2_to_5_year = list(
                    filter(lambda x: x['lease_name'] == lease,
                           move_ids_next_5_years_qry))
                amount_more_than_5_years = list(
                    filter(lambda x: x['lease_name'] == lease,
                           move_ids_more_than_5_years_qry))

                amount_lists = amount_less_than_1_year + amount_1_to_2_year + amount_2_to_5_year + amount_more_than_5_years
                if len(amount_less_than_1_year) >= 1 and len(
                        amount_1_to_2_year) >= 1 and len(
                    amount_2_to_5_year) >= 1 and len(
                    amount_more_than_5_years) >= 1:
                    data.append({
                        'leasor_name': lease,
                        'external_reference_number': amount_less_than_1_year[0][
                            "external_reference_number"],
                        'project_site': amount_less_than_1_year[0]["name"],
                        'total_amount_next_year': amount_less_than_1_year[0][
                            "total"],
                        'total_amount_next_2years': amount_1_to_2_year[0][
                            "total"],
                        'total_amount_next_5years': amount_2_to_5_year[0][
                            "total"],
                        'total_amount_more_than_5_years':
                            amount_more_than_5_years[0]["total"],
                        'currency': amount_less_than_1_year[0]["currency_name"],
                    })
                else:
                    data.append({
                        'leasor_name': lease,
                        'external_reference_number': amount_lists[0][
                            "external_reference_number"],
                        'project_site': amount_lists[0]["name"],
                        'total_amount_next_year': amount_less_than_1_year[0][
                            "total"] if len(
                            amount_less_than_1_year) >= 1 else 0.0,
                        'total_amount_next_2years': amount_1_to_2_year[0][
                            "total"] if len(amount_1_to_2_year) >= 1 else 0.0,
                        'total_amount_next_5years': amount_2_to_5_year[0][
                            "total"] if len(amount_2_to_5_year) >= 1 else 0.0,
                        'total_amount_more_than_5_years':
                            amount_more_than_5_years[0]["total"] if len(
                                amount_more_than_5_years) >= 1 else 0.0,
                        'currency': amount_lists[0]["currency_name"],
                    })
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
            worksheet.write(row, col,
                            line['total_amount_next_2years'],
                            STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col,
                            line['total_amount_next_5years'],
                            STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col,
                            line['total_amount_more_than_5_years'],
                            STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['currency'], STYLE_LINE_Data)
