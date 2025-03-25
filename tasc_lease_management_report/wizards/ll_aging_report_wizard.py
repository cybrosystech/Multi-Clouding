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
            'target': 'new'
        }

    def get_report_data(self):
        """Method to compute LL Aging Report data."""
        data = []
        if self.lease_contract_ids:
            lease_contract_ids = self.env['leasee.contract'].search(
                [('id', 'in', self.lease_contract_ids.ids),
                 ('parent_id', '=', False)
                 ])
        else:
            lease_contract_ids = self.env['leasee.contract'].search(
                [('company_id', '=', self.env.company.id),
                 ('account_move_ids', '!=', False), ('parent_id', '=', False)],
                order='id ASC')

        if lease_contract_ids:
            for contract in lease_contract_ids:
                next_year_date = self.end_date + dateutil.relativedelta.relativedelta(
                    years=1)
                less_than_1_year_start_date = self.end_date + dateutil.relativedelta.relativedelta(
                    days=1)

                one_to_2year_start_date = self.end_date + dateutil.relativedelta.relativedelta(
                    years=1)
                one_to_2year_start_date = one_to_2year_start_date + dateutil.relativedelta.relativedelta(
                    days=1)
                one_to_2year_end_date = (
                        self.end_date + dateutil.relativedelta.relativedelta(
                    years=2))

                start_date_2_to_5_year = self.end_date + dateutil.relativedelta.relativedelta(
                    years=2)
                start_date_2_to_5_year = start_date_2_to_5_year + dateutil.relativedelta.relativedelta(
                    days=1)
                end_date_2_to_5_year = (
                        self.end_date + dateutil.relativedelta.relativedelta(
                    years=5))
                start_date_5th_year = self.end_date + dateutil.relativedelta.relativedelta(
                    years=5)
                start_date_5th_year = start_date_5th_year + dateutil.relativedelta.relativedelta(
                    days=1)
                dep_move_ids = contract.asset_id.depreciation_move_ids.ids
                if contract.child_ids:
                    for children in contract.asset_id.children_ids:
                        dep_move_ids = dep_move_ids + children.depreciation_move_ids.ids
                    move_ids = self.env['account.move'].search(
                        [('leasee_contract_id', '=', contract.id)])
                    interest_move_lines = self.env['account.move.line'].search(
                        ['|', ('move_id', 'in', dep_move_ids),
                         ('move_id', 'in', move_ids.ids),
                         ('move_id.date', '>=', less_than_1_year_start_date),
                         ('move_id.date', '<=', next_year_date), (
                             'account_id', '=',
                             contract.interest_expense_account_id.id)])
                    interest_move_lines_amount = sum(
                        interest_move_lines.mapped('amount_currency'))

                    journal_items_less_than_1_yr_qry = [
                        {'total': interest_move_lines_amount,
                         'leasee_id': contract.id, 'leasee_name': contract.name,
                         'external_reference_number': contract.external_reference_number,
                         'currency_name': contract.leasee_currency_id.name,
                         'name': contract.project_site_id.name}]

                    # Computation for Less than 1 year

                    self._cr.execute('select sum(installment.amount) as total, '
                                     'leasee.id as leasee_id,'
                                     'leasee.name as leasee_name from '
                                     'leasee_contract as'
                                     ' leasee inner join leasee_installment as '
                                     'installment on '
                                     'installment.leasee_contract_id=leasee.id where  '
                                     'leasee.id = %(contract)s and '
                                     'leasee.company_id=%(company)s and '
                                     'installment.date <= %(end_date)s'
                                     ' and installment.date >= %(start_date)s '
                                     'group by leasee_id',
                                     {
                                         'contract': contract.id,
                                         'end_date': next_year_date,
                                         'start_date': less_than_1_year_start_date,
                                         'company': self.env.company.id,
                                     })
                    installments_less_than_1_year_qry = self._cr.dictfetchall()

                    # Computation for 1.01 -2 years

                    interest_move_lines_1_to_2_year = self.env['account.move.line'].search(
                        ['|', ('move_id', 'in', dep_move_ids),
                         ('move_id', 'in', move_ids.ids),
                         ('move_id.date', '>=', one_to_2year_start_date),
                         ('move_id.date', '<=', one_to_2year_end_date), (
                             'account_id', '=',
                             contract.interest_expense_account_id.id)])
                    interest_move_lines_1_to_2_year_amount = sum(
                        interest_move_lines_1_to_2_year.mapped('amount_currency'))

                    journal_items_one_to_2_year_qry = [
                        {'total': interest_move_lines_1_to_2_year_amount,
                         'leasee_id': contract.id, 'leasee_name': contract.name,
                         'external_reference_number': contract.external_reference_number,
                         'currency_name': contract.leasee_currency_id.name,
                         'name': contract.project_site_id.name}]

                    self._cr.execute('select sum(installment.amount) as total, '
                                     'leasee.id as leasee_id,'
                                     'leasee.name as leasee_name from leasee_contract as'
                                     ' leasee inner join leasee_installment as '
                                     'installment on '
                                     'installment.leasee_contract_id=leasee.id where  '
                                     'leasee.id = %(contract)s and '
                                     'leasee.company_id=%(company)s and '
                                     'installment.date <= %(end_date)s'
                                     ' and installment.date >= %(start_date)s '
                                     'group by leasee_id',
                                     {
                                         'contract': contract.id,
                                         'end_date': one_to_2year_end_date,
                                         'start_date': one_to_2year_start_date,
                                         'company': self.env.company.id,
                                     })
                    installments_one_to_2_year_qry = self._cr.dictfetchall()

                    # Computation for 2.01 -5 years
                    interest_move_lines_2_to_5_year = self.env['account.move.line'].search(
                        ['|', ('move_id', 'in', dep_move_ids),
                         ('move_id', 'in', move_ids.ids),
                         ('move_id.date', '>=', start_date_2_to_5_year),
                         ('move_id.date', '<=', end_date_2_to_5_year), (
                             'account_id', '=',
                             contract.interest_expense_account_id.id)])
                    interest_move_lines_2_to_5_year_amount = sum(
                        interest_move_lines_2_to_5_year.mapped('amount_currency'))

                    journal_items_2_to_5_year_qry = [
                        {'total': interest_move_lines_2_to_5_year_amount,
                         'leasee_id': contract.id, 'leasee_name': contract.name,
                         'external_reference_number': contract.external_reference_number,
                         'currency_name': contract.leasee_currency_id.name,
                         'name': contract.project_site_id.name}]


                    self._cr.execute('select sum(installment.amount) as total, '
                                     'leasee.id as leasee_id,'
                                     'leasee.name as leasee_name from leasee_contract as'
                                     ' leasee inner join leasee_installment as '
                                     'installment on '
                                     'installment.leasee_contract_id=leasee.id where  '
                                     'leasee.id = %(contract)s and '
                                     'leasee.company_id=%(company)s and '
                                     'installment.date <= %(end_date)s'
                                     ' and installment.date >= %(start_date)s '
                                     'group by leasee_id',
                                     {
                                         'contract': contract.id,
                                         'end_date': end_date_2_to_5_year,
                                         'start_date': start_date_2_to_5_year,
                                         'company': self.env.company.id,
                                     })
                    installments_2_to_5_year_qry = self._cr.dictfetchall()

                    # Computation for more than 5 years

                    interest_move_lines_more_than_5_year = self.env['account.move.line'].search(
                        ['|', ('move_id', 'in', dep_move_ids),
                         ('move_id', 'in', move_ids.ids),
                         ('move_id.date', '>=', start_date_5th_year),
                        (
                             'account_id', '=',
                             contract.interest_expense_account_id.id)])
                    interest_move_lines_more_than_5_year_amount = sum(
                        interest_move_lines_more_than_5_year.mapped('amount_currency'))

                    journal_items_more_than_5_year_qry = [
                        {'total': interest_move_lines_more_than_5_year_amount,
                         'leasee_id': contract.id, 'leasee_name': contract.name,
                         'external_reference_number': contract.external_reference_number,
                         'currency_name': contract.leasee_currency_id.name,
                         'name': contract.project_site_id.name}]

                    self._cr.execute('select sum(installment.amount) as total, '
                                     'leasee.id as leasee_id,'
                                     'leasee.name as leasee_name from '
                                     'leasee_contract as'
                                     ' leasee inner join leasee_installment as '
                                     'installment on '
                                     'installment.leasee_contract_id=leasee.id where  '
                                     'leasee.id = %(contract)s and '
                                     'leasee.company_id=%(company)s and '
                                     ' installment.date >= %(start_date)s '
                                     'group by leasee_id',
                                     {
                                         'contract': contract.id,
                                         'start_date': start_date_5th_year,
                                         'company': self.env.company.id,
                                     })
                    installments_more_than_5_year_qry = self._cr.dictfetchall()

                    if len(installments_less_than_1_year_qry) >= 1 and len(
                            journal_items_less_than_1_yr_qry) >= 1:
                        tot_less_than_1_year = \
                            installments_less_than_1_year_qry[0]["total"] - \
                            journal_items_less_than_1_yr_qry[0]["total"]
                    elif len(installments_less_than_1_year_qry) >= 1:
                        tot_less_than_1_year = \
                            installments_less_than_1_year_qry[0]["total"]
                    elif len(journal_items_less_than_1_yr_qry) >= 1:
                        tot_less_than_1_year = 0 - \
                                               journal_items_less_than_1_yr_qry[
                                                   0]["total"]
                    else:
                        tot_less_than_1_year = 0

                    if len(installments_one_to_2_year_qry) >= 1 and len(
                            journal_items_one_to_2_year_qry) >= 1:
                        total_one_to_two_year = \
                            installments_one_to_2_year_qry[0]["total"] - \
                            journal_items_one_to_2_year_qry[0]["total"]
                    elif len(installments_one_to_2_year_qry) >= 1:
                        total_one_to_two_year = \
                            installments_one_to_2_year_qry[0]["total"]
                    elif len(journal_items_one_to_2_year_qry) >= 1:
                        total_one_to_two_year = 0 - \
                                                journal_items_one_to_2_year_qry[
                                                    0]["total"]
                    else:
                        total_one_to_two_year = 0

                    if len(installments_2_to_5_year_qry) >= 1 and len(
                            journal_items_2_to_5_year_qry) >= 1:
                        total_two_to_five_year = \
                            installments_2_to_5_year_qry[0]["total"] - \
                            journal_items_2_to_5_year_qry[0]["total"]
                    elif len(installments_2_to_5_year_qry) >= 1:
                        total_two_to_five_year = \
                            installments_2_to_5_year_qry[0]["total"]
                    elif len(journal_items_2_to_5_year_qry) >= 1:
                        total_two_to_five_year = 0 - \
                                                 journal_items_2_to_5_year_qry[
                                                     0]["total"]
                    else:
                        total_two_to_five_year = 0

                    if len(installments_more_than_5_year_qry) >= 1 and len(
                            journal_items_more_than_5_year_qry) >= 1:
                        total_more_than_five_year = \
                            installments_more_than_5_year_qry[0]["total"] - \
                            journal_items_more_than_5_year_qry[0]["total"]
                    elif len(installments_more_than_5_year_qry) >= 1:
                        total_more_than_five_year = \
                            installments_more_than_5_year_qry[0]["total"]
                    elif len(journal_items_more_than_5_year_qry) >= 1:
                        total_more_than_five_year = 0 - \
                                                    journal_items_more_than_5_year_qry[
                                                        0]["total"]
                    else:
                        total_more_than_five_year = 0

                    if tot_less_than_1_year > 0 or total_one_to_two_year > 0 or total_two_to_five_year > 0 or total_more_than_five_year > 0:
                        data.append({
                            'leasor_name': contract.name,
                            'external_reference_number': contract.external_reference_number,
                            'project_site': contract.project_site_id.name,
                            'less_than_one_year': tot_less_than_1_year,
                            'one_to_two_year': total_one_to_two_year,
                            'two_to_five_year': total_two_to_five_year,
                            'more_than_five_year': total_more_than_five_year,
                            'currency': contract.leasee_currency_id.name,
                        })
                else:
                    # Computation for Less than 1 year
                    self._cr.execute(
                        'select sum(item.amount_currency) as total, '
                        'leasee.id as leasee_id,'
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
                        'leasee.id = %(contract)s and '
                        'leasee.company_id=%(company)s and '
                        'journal.date <= %(end_date)s and '
                        'journal.date >= %(start_date)s and '
                        'item.account_id=leasee.interest_expense_account_id'
                        ' group by leasee_id,'
                        'leasee.external_reference_number,'
                        'currency_name,project_site.name',
                        {
                            'contract': contract.id,
                            'end_date': next_year_date,
                            'start_date': less_than_1_year_start_date,
                            'company': self.env.company.id,
                        })
                    journal_items_less_than_1_yr_qry = self._cr.dictfetchall()

                    self._cr.execute('select sum(installment.amount) as total, '
                                     'leasee.id as leasee_id,'
                                     'leasee.name as leasee_name from '
                                     'leasee_contract as'
                                     ' leasee inner join leasee_installment as '
                                     'installment on '
                                     'installment.leasee_contract_id=leasee.id where  '
                                     'leasee.id = %(contract)s and '
                                     'leasee.company_id=%(company)s and '
                                     'installment.date <= %(end_date)s'
                                     ' and installment.date >= %(start_date)s '
                                     'group by leasee_id',
                                     {
                                         'contract': contract.id,
                                         'end_date': next_year_date,
                                         'start_date': less_than_1_year_start_date,
                                         'company': self.env.company.id,
                                     })
                    installments_less_than_1_year_qry = self._cr.dictfetchall()

                    # Computation for 1.01 -2 years

                    self._cr.execute(
                        'select sum(item.amount_currency) as total, '
                        'leasee.id as leasee_id,'
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
                        'leasee.id = %(contract)s and '
                        'leasee.company_id=%(company)s and '
                        'journal.date <= %(end_date)s and '
                        'journal.date >= %(start_date)s and '
                        'item.account_id=leasee.interest_expense_account_id'
                        ' group by leasee_id,'
                        'leasee.external_reference_number,'
                        'currency_name,project_site.name',
                        {
                            'contract': contract.id,
                            'end_date': one_to_2year_end_date,
                            'start_date': one_to_2year_start_date,
                            'company': self.env.company.id,
                        })
                    journal_items_one_to_2_year_qry = self._cr.dictfetchall()
                    self._cr.execute('select sum(installment.amount) as total, '
                                     'leasee.id as leasee_id,'
                                     'leasee.name as leasee_name from leasee_contract as'
                                     ' leasee inner join leasee_installment as '
                                     'installment on '
                                     'installment.leasee_contract_id=leasee.id where  '
                                     'leasee.id = %(contract)s and '
                                     'leasee.company_id=%(company)s and '
                                     'installment.date <= %(end_date)s'
                                     ' and installment.date >= %(start_date)s '
                                     'group by leasee_id',
                                     {
                                         'contract': contract.id,
                                         'end_date': one_to_2year_end_date,
                                         'start_date': one_to_2year_start_date,
                                         'company': self.env.company.id,
                                     })
                    installments_one_to_2_year_qry = self._cr.dictfetchall()

                    # Computation for 2.01 -5 years

                    self._cr.execute(
                        'select sum(item.amount_currency) as total, '
                        'leasee.id as leasee_id,'

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
                        'leasee.id = %(contract)s and '
                        'leasee.company_id=%(company)s and '
                        'journal.date <= %(end_date)s and '
                        'journal.date >= %(start_date)s and '
                        'item.account_id=leasee.interest_expense_account_id'
                        ' group by leasee_id,'
                        'leasee.external_reference_number,'
                        'currency_name,project_site.name',
                        {
                            'contract': contract.id,
                            'end_date': end_date_2_to_5_year,
                            'start_date': start_date_2_to_5_year,
                            'company': self.env.company.id,
                        })
                    journal_items_2_to_5_year_qry = self._cr.dictfetchall()

                    self._cr.execute('select sum(installment.amount) as total, '
                                     'leasee.id as leasee_id,'
                                     'leasee.name as leasee_name from leasee_contract as'
                                     ' leasee inner join leasee_installment as '
                                     'installment on '
                                     'installment.leasee_contract_id=leasee.id where  '
                                     'leasee.id = %(contract)s and '
                                     'leasee.company_id=%(company)s and '
                                     'installment.date <= %(end_date)s'
                                     ' and installment.date >= %(start_date)s '
                                     'group by leasee_id',
                                     {
                                         'contract': contract.id,
                                         'end_date': end_date_2_to_5_year,
                                         'start_date': start_date_2_to_5_year,
                                         'company': self.env.company.id,
                                     })
                    installments_2_to_5_year_qry = self._cr.dictfetchall()

                    # Computation for more than 5 years

                    self._cr.execute(
                        'select sum(item.amount_currency) as total, '
                        'leasee.id as leasee_id,'
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
                        'leasee.id = %(contract)s and '
                        'leasee.company_id=%(company)s and '
                        'journal.date >= %(start_date)s and '
                        'item.account_id=leasee.interest_expense_account_id'
                        ' group by leasee_id,'
                        'leasee.external_reference_number,'
                        'currency_name,project_site.name',
                        {
                            'contract': contract.id,
                            'start_date': start_date_5th_year,
                            'company': self.env.company.id,
                        })
                    journal_items_more_than_5_year_qry = self._cr.dictfetchall()

                    self._cr.execute('select sum(installment.amount) as total, '
                                     'leasee.id as leasee_id,'
                                     'leasee.name as leasee_name from '
                                     'leasee_contract as'
                                     ' leasee inner join leasee_installment as '
                                     'installment on '
                                     'installment.leasee_contract_id=leasee.id where  '
                                     'leasee.id = %(contract)s and '
                                     'leasee.company_id=%(company)s and '
                                     ' installment.date >= %(start_date)s '
                                     'group by leasee_id',
                                     {
                                         'contract': contract.id,
                                         'start_date': start_date_5th_year,
                                         'company': self.env.company.id,
                                     })
                    installments_more_than_5_year_qry = self._cr.dictfetchall()

                    if len(installments_less_than_1_year_qry) >= 1 and len(
                            journal_items_less_than_1_yr_qry) >= 1:
                        tot_less_than_1_year = \
                            installments_less_than_1_year_qry[0]["total"] - \
                            journal_items_less_than_1_yr_qry[0]["total"]
                    elif len(installments_less_than_1_year_qry) >= 1:
                        tot_less_than_1_year = \
                            installments_less_than_1_year_qry[0]["total"]
                    elif len(journal_items_less_than_1_yr_qry) >= 1:
                        tot_less_than_1_year = 0 - \
                                               journal_items_less_than_1_yr_qry[
                                                   0]["total"]
                    else:
                        tot_less_than_1_year = 0

                    if len(installments_one_to_2_year_qry) >= 1 and len(
                            journal_items_one_to_2_year_qry) >= 1:
                        total_one_to_two_year = \
                            installments_one_to_2_year_qry[0]["total"] - \
                            journal_items_one_to_2_year_qry[0]["total"]
                    elif len(installments_one_to_2_year_qry) >= 1:
                        total_one_to_two_year = \
                            installments_one_to_2_year_qry[0]["total"]
                    elif len(journal_items_one_to_2_year_qry) >= 1:
                        total_one_to_two_year = 0 - \
                                                journal_items_one_to_2_year_qry[
                                                    0]["total"]
                    else:
                        total_one_to_two_year = 0

                    if len(installments_2_to_5_year_qry) >= 1 and len(
                            journal_items_2_to_5_year_qry) >= 1:
                        total_two_to_five_year = \
                            installments_2_to_5_year_qry[0]["total"] - \
                            journal_items_2_to_5_year_qry[0]["total"]
                    elif len(installments_2_to_5_year_qry) >= 1:
                        total_two_to_five_year = \
                            installments_2_to_5_year_qry[0]["total"]
                    elif len(journal_items_2_to_5_year_qry) >= 1:
                        total_two_to_five_year = 0 - \
                                                 journal_items_2_to_5_year_qry[
                                                     0]["total"]
                    else:
                        total_two_to_five_year = 0

                    if len(installments_more_than_5_year_qry) >= 1 and len(
                            journal_items_more_than_5_year_qry) >= 1:
                        total_more_than_five_year = \
                            installments_more_than_5_year_qry[0]["total"] - \
                            journal_items_more_than_5_year_qry[0]["total"]
                    elif len(installments_more_than_5_year_qry) >= 1:
                        total_more_than_five_year = \
                            installments_more_than_5_year_qry[0]["total"]
                    elif len(journal_items_more_than_5_year_qry) >= 1:
                        total_more_than_five_year = 0 - \
                                                    journal_items_more_than_5_year_qry[
                                                        0]["total"]
                    else:
                        total_more_than_five_year = 0

                    if tot_less_than_1_year > 0 or total_one_to_two_year > 0 or total_two_to_five_year > 0 or total_more_than_five_year > 0:
                        data.append({
                            'leasor_name': contract.name,
                            'external_reference_number': contract.external_reference_number,
                            'project_site': contract.project_site_id.name,
                            'less_than_one_year': tot_less_than_1_year,
                            'one_to_two_year': total_one_to_two_year,
                            'two_to_five_year': total_two_to_five_year,
                            'more_than_five_year': total_more_than_five_year,
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
            if not line['project_site']:
                worksheet.write(row, col, '', STYLE_LINE_Data)
                col += 1
            else:
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
