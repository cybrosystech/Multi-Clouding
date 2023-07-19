import base64
import io
import datetime
from operator import itemgetter

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
            lease_contract_ids = self.lease_contract_ids
        else:
            lease_contract_ids = self.env['leasee.contract'].search([],
                                                                    order='id ASC')
        if lease_contract_ids:

            # Computation for Less than 1 year
            next_year_date = self.end_date + dateutil.relativedelta.relativedelta(
                years=1)
            less_than_1_year_start_date = self.end_date + dateutil.relativedelta.relativedelta(
                days=1)

            self._cr.execute('select sum(item.amount_currency) as total, '
                             'leasee.name as leasee_name,'
                             'leasee.external_reference_number,'
                             'currency.name as '
                             'currency_name,project_site.name from '
                             'leasee_contract as leasee inner '
                             'join account_move '
                             'as journal on '
                             'journal.leasee_contract_id= leasee.id or '
                             'journal.asset_id = leasee.asset_id inner join '
                             'account_move_line as item on '
                             'item.move_id = journal.id inner join '
                             'res_currency as currency on'
                             ' currency.id=leasee.leasee_currency_id left join '
                             'account_analytic_account as project_site on '
                             'project_site.id=leasee.project_site_id where '
                             'leasee.id in %(contract)s and '
                             'leasee.company_id=%(company)s and '
                             'journal.date <= %(end_date)s and '
                             'journal.date >= %(start_date)s and '
                             'item.account_id=leasee.interest_expense_account_id'
                             ' group by leasee_name,'
                             'leasee.external_reference_number,'
                             'currency_name,project_site.name',
                             {
                                 'contract': tuple(lease_contract_ids.ids),
                                 'end_date': next_year_date,
                                 'start_date': less_than_1_year_start_date,
                                 'company': self.env.company.id,
                             })
            journal_items_less_than_1_yr_qry = self._cr.dictfetchall()
            journal_items_less_than_1_year_lease_names = list(
                map(itemgetter('leasee_name'),
                    journal_items_less_than_1_yr_qry))
            self._cr.execute('select sum(installment.amount) as total, '
                             'leasee.name as leasee_name from '
                             'leasee_contract as'
                             ' leasee inner join leasee_installment as '
                             'installment on '
                             'installment.leasee_contract_id=leasee.id where  '
                             'leasee.id in %(contract)s and '
                             'leasee.company_id=%(company)s and '
                             'installment.date <= %(end_date)s'
                             ' and installment.date >= %(start_date)s '
                             'group by leasee_name',
                             {
                                 'contract': tuple(lease_contract_ids.ids),
                                 'end_date': next_year_date,
                                 'start_date': less_than_1_year_start_date,
                                 'company': self.env.company.id,
                             })
            installments_less_than_1_year_qry = self._cr.dictfetchall()

            installments_less_than_1_year_lease_names = list(
                map(itemgetter('leasee_name'),
                    installments_less_than_1_year_qry))

            # Computation for 1.01 -2 years
            one_to_2year_start_date = self.end_date + dateutil.relativedelta.relativedelta(
                years=1)
            one_to_2year_start_date = one_to_2year_start_date + dateutil.relativedelta.relativedelta(
                days=1)
            one_to_2year_end_date = (
                    self.end_date + dateutil.relativedelta.relativedelta(
                years=2))

            self._cr.execute('select sum(item.amount_currency) as total, '
                             'leasee.name as leasee_name,'
                             'leasee.external_reference_number,'
                             'currency.name as '
                             'currency_name,project_site.name from '
                             'leasee_contract as leasee inner '
                             'join account_move '
                             'as journal on '
                             'journal.leasee_contract_id= leasee.id or '
                             'journal.asset_id = leasee.asset_id inner join '
                             'account_move_line as item on '
                             'item.move_id = journal.id inner join '
                             'res_currency as currency on'
                             ' currency.id=leasee.leasee_currency_id left join '
                             'account_analytic_account as project_site on '
                             'project_site.id=leasee.project_site_id where '
                             'leasee.id in %(contract)s and '
                             'leasee.company_id=%(company)s and '
                             'journal.date <= %(end_date)s and '
                             'journal.date >= %(start_date)s and '
                             'item.account_id=leasee.interest_expense_account_id'
                             ' group by leasee_name,'
                             'leasee.external_reference_number,'
                             'currency_name,project_site.name',
                             {
                                 'contract': tuple(lease_contract_ids.ids),
                                 'end_date': one_to_2year_end_date,
                                 'start_date': one_to_2year_start_date,
                                 'company': self.env.company.id,
                             })
            journal_items_one_to_2_year_qry = self._cr.dictfetchall()

            journal_items_one_to_2_year_lease_names = list(
                map(itemgetter('leasee_name'), journal_items_one_to_2_year_qry))

            self._cr.execute('select sum(installment.amount) as total, '
                             'leasee.name as leasee_name from leasee_contract as'
                             ' leasee inner join leasee_installment as '
                             'installment on '
                             'installment.leasee_contract_id=leasee.id where  '
                             'leasee.id in %(contract)s and '
                             'leasee.company_id=%(company)s and '
                             'installment.date <= %(end_date)s'
                             ' and installment.date >= %(start_date)s '
                             'group by leasee_name',
                             {
                                 'contract': tuple(lease_contract_ids.ids),
                                 'end_date': one_to_2year_end_date,
                                 'start_date': one_to_2year_start_date,
                                 'company': self.env.company.id,
                             })
            installments_one_to_2_year_qry = self._cr.dictfetchall()

            installments_one_to_2_year_lease_names = list(
                map(itemgetter('leasee_name'), installments_one_to_2_year_qry))

            # Computation for 2.01 -5 years
            start_date_2_to_5_year = self.end_date + dateutil.relativedelta.relativedelta(
                years=2)
            start_date_2_to_5_year = start_date_2_to_5_year + dateutil.relativedelta.relativedelta(
                days=1)
            end_date_2_to_5_year = (
                    self.end_date + dateutil.relativedelta.relativedelta(
                years=5))

            self._cr.execute('select sum(item.amount_currency) as total, '
                             'leasee.name as leasee_name,'
                             'leasee.external_reference_number,'
                             'currency.name as '
                             'currency_name,project_site.name from '
                             'leasee_contract as leasee inner '
                             'join account_move '
                             'as journal on '
                             'journal.leasee_contract_id= leasee.id or '
                             'journal.asset_id = leasee.asset_id inner join '
                             'account_move_line as item on '
                             'item.move_id = journal.id inner join '
                             'res_currency as currency on'
                             ' currency.id=leasee.leasee_currency_id left join '
                             'account_analytic_account as project_site on '
                             'project_site.id=leasee.project_site_id where '
                             'leasee.id in %(contract)s and '
                             'leasee.company_id=%(company)s and '
                             'journal.date <= %(end_date)s and '
                             'journal.date >= %(start_date)s and '
                             'item.account_id=leasee.interest_expense_account_id'
                             ' group by leasee_name,'
                             'leasee.external_reference_number,'
                             'currency_name,project_site.name',
                             {
                                 'contract': tuple(lease_contract_ids.ids),
                                 'end_date': end_date_2_to_5_year,
                                 'start_date': start_date_2_to_5_year,
                                 'company': self.env.company.id,
                             })
            journal_items_2_to_5_year_qry = self._cr.dictfetchall()

            journal_items_2_to_5_year_lease_names = list(
                map(itemgetter('leasee_name'), journal_items_2_to_5_year_qry))

            self._cr.execute('select sum(installment.amount) as total, '
                             'leasee.name as leasee_name from leasee_contract as'
                             ' leasee inner join leasee_installment as '
                             'installment on '
                             'installment.leasee_contract_id=leasee.id where  '
                             'leasee.id in %(contract)s and '
                             'leasee.company_id=%(company)s and '
                             'installment.date <= %(end_date)s'
                             ' and installment.date >= %(start_date)s '
                             'group by leasee_name',
                             {
                                 'contract': tuple(lease_contract_ids.ids),
                                 'end_date': end_date_2_to_5_year,
                                 'start_date': start_date_2_to_5_year,
                                 'company': self.env.company.id,
                             })
            installments_2_to_5_year_qry = self._cr.dictfetchall()

            installments_2_to_5_year_lease_names = list(
                map(itemgetter('leasee_name'), installments_2_to_5_year_qry))

            # Computation for more than 5 years
            start_date_5th_year = self.end_date + dateutil.relativedelta.relativedelta(
                years=5)
            start_date_5th_year = start_date_5th_year + dateutil.relativedelta.relativedelta(
                days=1)

            self._cr.execute('select sum(item.amount_currency) as total, '
                             'leasee.name as leasee_name,'
                             'leasee.external_reference_number,'
                             'currency.name as '
                             'currency_name,project_site.name from '
                             'leasee_contract as leasee inner '
                             'join account_move '
                             'as journal on '
                             'journal.leasee_contract_id= leasee.id or '
                             'journal.asset_id = leasee.asset_id inner join '
                             'account_move_line as item on '
                             'item.move_id = journal.id inner join '
                             'res_currency as currency on'
                             ' currency.id=leasee.leasee_currency_id left join '
                             'account_analytic_account as project_site on '
                             'project_site.id=leasee.project_site_id where '
                             'leasee.id in %(contract)s and '
                             'leasee.company_id=%(company)s and '
                             'journal.date >= %(start_date)s and '
                             'item.account_id=leasee.interest_expense_account_id'
                             ' group by leasee_name,'
                             'leasee.external_reference_number,'
                             'currency_name,project_site.name',
                             {
                                 'contract': tuple(lease_contract_ids.ids),
                                 'start_date': start_date_5th_year,
                                 'company': self.env.company.id,
                             })
            journal_items_more_than_5_year_qry = self._cr.dictfetchall()

            journal_items_more_than_5_year_lease_names = list(
                map(itemgetter('leasee_name'),
                    journal_items_more_than_5_year_qry))

            self._cr.execute('select sum(installment.amount) as total, '
                             'leasee.name as leasee_name from '
                             'leasee_contract as'
                             ' leasee inner join leasee_installment as '
                             'installment on '
                             'installment.leasee_contract_id=leasee.id where  '
                             'leasee.id in %(contract)s and '
                             'leasee.company_id=%(company)s and '
                             ' installment.date >= %(start_date)s '
                             'group by leasee_name',
                             {
                                 'contract': tuple(lease_contract_ids.ids),
                                 'start_date': start_date_5th_year,
                                 'company': self.env.company.id,
                             })
            installments_more_than_5_year_qry = self._cr.dictfetchall()
            installments_more_than_5_year_lease_names = list(
                map(itemgetter('leasee_name'),
                    installments_more_than_5_year_qry))

            lease_names = list(
                set(journal_items_less_than_1_year_lease_names + installments_less_than_1_year_lease_names + journal_items_one_to_2_year_lease_names + installments_one_to_2_year_lease_names + journal_items_2_to_5_year_lease_names + installments_2_to_5_year_lease_names + journal_items_more_than_5_year_lease_names + installments_more_than_5_year_lease_names))
            lease_names.sort()
            for lease in lease_names:
                liability_less_than_1_year = list(
                    filter(lambda x: x['leasee_name'] == lease,
                           journal_items_less_than_1_yr_qry))
                installment_less_than_1_year = list(
                    filter(lambda x: x['leasee_name'] == lease,
                           installments_less_than_1_year_qry))
                if len(liability_less_than_1_year) >= 1 and len(
                        installment_less_than_1_year) >= 1:
                    tot_amt_less_1_yr = installment_less_than_1_year[0][
                                            "total"] - \
                                        liability_less_than_1_year[0]["total"]
                elif len(installment_less_than_1_year) >= 1:
                    tot_amt_less_1_yr = installment_less_than_1_year[0][
                        "total"]
                elif len(liability_less_than_1_year) >= 1:
                    tot_amt_less_1_yr = - liability_less_than_1_year[0]["total"]
                else:
                    tot_amt_less_1_yr = 0.0

                liability_1_to_2_yr = list(
                    filter(lambda x: x['leasee_name'] == lease,
                           journal_items_one_to_2_year_qry))
                installment_1_to_2_yr = list(
                    filter(lambda x: x['leasee_name'] == lease,
                           installments_one_to_2_year_qry))

                if len(liability_1_to_2_yr) >= 1 and len(
                        installment_1_to_2_yr) >= 1:
                    tot_amt_1_to_2_yr = installment_1_to_2_yr[0][
                                            "total"] - \
                                        liability_1_to_2_yr[0]["total"]
                elif len(installment_1_to_2_yr) >= 1:
                    tot_amt_1_to_2_yr = installment_1_to_2_yr[0][
                        "total"]
                elif len(liability_1_to_2_yr) >= 1:
                    tot_amt_1_to_2_yr = - liability_1_to_2_yr[0]["total"]
                else:
                    tot_amt_1_to_2_yr = 0.0

                liability_2_to_5_yr = list(
                    filter(lambda x: x['leasee_name'] == lease,
                           journal_items_2_to_5_year_qry))
                installment_2_to_5_yr = list(
                    filter(lambda x: x['leasee_name'] == lease,
                           installments_2_to_5_year_qry))

                if len(liability_2_to_5_yr) >= 1 and len(
                        installment_2_to_5_yr) >= 1:
                    tot_amt_2_to_5_yr = installment_2_to_5_yr[0][
                                            "total"] - \
                                        liability_2_to_5_yr[0]["total"]
                elif len(installment_2_to_5_yr) >= 1:
                    tot_amt_2_to_5_yr = installment_2_to_5_yr[0][
                        "total"]
                elif len(liability_2_to_5_yr) >= 1:
                    tot_amt_2_to_5_yr = - liability_2_to_5_yr[0]["total"]
                else:
                    tot_amt_2_to_5_yr = 0.0

                liability_more_5_yr = list(
                    filter(lambda x: x['leasee_name'] == lease,
                           journal_items_more_than_5_year_qry))
                installment_more_5_yr = list(
                    filter(lambda x: x['leasee_name'] == lease,
                           installments_more_than_5_year_qry))

                if len(liability_more_5_yr) >= 1 and len(
                        installment_more_5_yr) >= 1:
                    tot_amt_more_5_yr = installment_more_5_yr[0][
                                            "total"] - \
                                        liability_more_5_yr[0]["total"]
                elif len(installment_more_5_yr) >= 1:
                    tot_amt_more_5_yr = installment_more_5_yr[0][
                        "total"]
                elif len(liability_more_5_yr) >= 1:
                    tot_amt_more_5_yr = - liability_more_5_yr[0]["total"]
                else:
                    tot_amt_more_5_yr = 0.0

                liabilities = liability_less_than_1_year + liability_1_to_2_yr + liability_2_to_5_yr + liability_2_to_5_yr + liability_more_5_yr
                data.append({
                    'leasor_name': lease,
                    'external_reference_number': liabilities[0][
                        'external_reference_number'] if len(
                        liabilities) >= 1 else '',
                    'project_site': liabilities[0]['name'] if len(
                        liabilities) >= 1 else '',
                    'less_than_one_year': tot_amt_less_1_yr,
                    'one_to_two_year': tot_amt_1_to_2_yr,
                    'two_to_five_year': tot_amt_2_to_5_yr,
                    'more_than_five_year': tot_amt_more_5_yr,
                    'currency': liabilities[0]['currency_name'] if len(
                        liabilities) >= 1 else '',
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
