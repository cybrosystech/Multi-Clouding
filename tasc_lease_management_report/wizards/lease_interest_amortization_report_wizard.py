import base64
import datetime
import io
from operator import itemgetter

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

            # computation for the interest and amortization
        amortization_datas = []
        interest_move_line_ids = []
        lease_names = []
        if lease_contract_ids:
            if self.state:
                self._cr.execute(
                    'select coalesce((sum(item.debit) + sum(item.credit)), 0) interest_total,'
                    ' leasee.id as lease_id,leasee.external_reference_number,currency.name as currency_name,'
                    'project_site.name ,leasee.name as lease_name '
                    'from leasee_contract as leasee inner join'
                    ' account_move as journal on '
                    'journal.leasee_contract_id=leasee.id inner join '
                    'account_move_line as item on journal.id= item.move_id '
                    'inner join res_currency as currency on '
                    'currency.id=leasee.leasee_currency_id '
                    'left join account_analytic_account as project_site on'
                    ' project_site.id=leasee.project_site_id  '
                    ' where '
                    'leasee.id in %(contract_ids)s and  '
                    'journal.move_type=%(move_type)s and journal.date >= %(start_date)s and'
                    ' journal.date <= %(end_date)s and journal.state=%(state)s and '
                    'item.account_id = leasee.interest_expense_account_id '
                    'group by lease_id,leasee.external_reference_number,'
                    'currency_name,project_site.name',
                    {'contract_ids': tuple(lease_contract_ids.ids),
                     'move_type': 'entry',
                     'start_date': self.start_date,
                     'end_date': self.end_date,
                     'state': self.state,
                     }
                )
                interest_move_line_ids = self._cr.dictfetchall()
                interest_lease_names = list(
                    map(itemgetter('lease_name'), interest_move_line_ids))
                for contract in lease_contract_ids:
                    amortization_amount = 0
                    dep_move_ids = contract.asset_id.depreciation_move_ids.ids
                    if contract.child_ids:
                        for children in contract.asset_id.children_ids:
                            dep_move_ids = dep_move_ids + children.depreciation_move_ids.ids
                    if contract.asset_id.children_ids:
                        for child in contract.asset_id.children_ids:
                            dep_move_ids = dep_move_ids + child.depreciation_move_ids.ids
                    depreciation_move_line_ids = self.env[
                        'account.move.line'].search(
                        [('move_id', 'in', dep_move_ids),
                         ('move_id.date', '>=', self.start_date),
                         ('move_id.date', '<=', self.end_date),
                         ('account_id', '=',
                          contract.asset_model_id.account_depreciation_expense_id.id),
                         ('move_id.state', '=', self.state)])
                    amortization_amount = sum(
                        depreciation_move_line_ids.mapped('debit')) + sum(
                        depreciation_move_line_ids.mapped('credit'))
                    amortization_datas.append({'lease_id': contract.id,
                                               'lease_name': contract.name,
                                               'amortization_total': amortization_amount,
                                               'external_reference_number': contract.external_reference_number,
                                               'name': contract.project_site_id.name,
                                               'currency_name': contract.leasee_currency_id.name})

                amortization_lease_names = list(
                    map(itemgetter('lease_id'), amortization_datas))
                lease_names = interest_lease_names + amortization_lease_names
                lease_names = list(set(lease_names))
            else:
                self._cr.execute(
                    'select coalesce((sum(item.debit) + sum(item.credit)), 0) interest_total,'
                    ' leasee.id as lease_id ,leasee.external_reference_number,currency.name as currency_name,'
                    'project_site.name,leasee.name as lease_name'
                    ' from leasee_contract as leasee inner join'
                    ' account_move as journal on '
                    'journal.leasee_contract_id=leasee.id inner join '
                    'account_move_line as item on journal.id= item.move_id '
                    'inner join res_currency as currency on '
                    'currency.id=leasee.leasee_currency_id left join '
                    'account_analytic_account as project_site '
                    'on project_site.id=leasee.project_site_id '
                    'where '
                    'leasee.id in %(contract_ids)s and  '
                    'journal.move_type=%(move_type)s and journal.date >= %(start_date)s and'
                    ' journal.date <= %(end_date)s and '
                    'item.account_id = leasee.interest_expense_account_id '
                    'group by lease_id,leasee.external_reference_number,'
                    'currency_name,project_site.name',
                    {'contract_ids': tuple(lease_contract_ids.ids),
                     'move_type': 'entry',
                     'start_date': self.start_date,
                     'end_date': self.end_date,
                     }
                )

                interest_move_line_ids = self._cr.dictfetchall()
                interest_lease_names = list(
                    map(itemgetter('lease_id'), interest_move_line_ids))
                for contract in lease_contract_ids:
                    amortization_amount = 0
                    dep_move_ids = contract.asset_id.depreciation_move_ids.ids
                    if contract.child_ids:
                        for children in contract.asset_id.children_ids:
                            dep_move_ids = dep_move_ids + children.depreciation_move_ids.ids
                    if contract.asset_id.children_ids:
                        for child in contract.asset_id.children_ids:
                            dep_move_ids = dep_move_ids + child.depreciation_move_ids.ids
                    depreciation_move_line_ids = self.env[
                        'account.move.line'].search(
                        [('move_id', 'in', dep_move_ids),
                         ('move_id.date', '>=', self.start_date),
                         ('move_id.date', '<=', self.end_date),
                         ('account_id', '=',
                          contract.asset_model_id.account_depreciation_expense_id.id),
                         ])
                    amortization_amount = sum(
                        depreciation_move_line_ids.mapped('debit')) + sum(
                        depreciation_move_line_ids.mapped('credit'))
                    amortization_datas.append({'lease_id': contract.id,
                                               'lease_name': contract.name,
                                               'amortization_total': amortization_amount,
                                               'external_reference_number': contract.external_reference_number,
                                               'name': contract.project_site_id.name,
                                               'currency_name': contract.leasee_currency_id.name})

                amortization_lease_names = list(
                    map(itemgetter('lease_id'), amortization_datas))
                lease_names = interest_lease_names + amortization_lease_names
                lease_names = list(set(lease_names))
        lease_names.sort()
        for lease in lease_names:
            test = list(filter(lambda x: x['lease_id'] == lease,
                               amortization_datas))
            test1 = list(filter(lambda x: x['lease_id'] == lease,
                                interest_move_line_ids))
            if len(test) >= 1 and len(test1) >= 1:
                data.append({
                    'leasor_name': test[0][
                        "lease_name"],
                    'external_reference_number': test[0][
                        "external_reference_number"],
                    'project_site': test[0]["name"],
                    'interest': test1[0]["interest_total"] if test1[0] else 0.0,
                    'amortization': test[0]["amortization_total"] if test[
                        0] else 0.0,
                    'currency': test[0]["currency_name"],
                })
            elif len(test) >= 1:
                data.append({
                    'leasor_name': test[0][
                        "lease_name"],
                    'external_reference_number': test[0][
                        "external_reference_number"],
                    'project_site': test[0]["name"],
                    'interest': 0.0,
                    'amortization': test[0]["amortization_total"],
                    'currency': test[0]["currency_name"],
                })
            elif len(test1) >= 1:
                data.append({
                    'leasor_name': test1[0][
                        "lease_name"],
                    'external_reference_number': test1[0][
                        "external_reference_number"],
                    'project_site': test1[0]["name"],
                    'interest': test1[0]["interest_total"] if test1[0] else 0.0,
                    'amortization': 0.0,
                    'currency': test1[0]["currency_name"],
                })
            else:
                pass
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
