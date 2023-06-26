import base64
import io
import xlsxwriter
import datetime
from odoo import fields, models, _


class LeaseLlAndRouReportWizard(models.TransientModel):
    """
    Class for Lease LL and ROU report xlsx.
    """
    _name = 'lease.ll.rou.report.wizard'
    _description = "Lease LL and ROU Report"

    lease_contract_ids = fields.Many2many('leasee.contract',
                                          string="Lease Contract")

    end_date = fields.Date(string="As of Date",
                           default=datetime.datetime.now(), required=True)
    excel_sheet = fields.Binary('Download Report')
    excel_sheet_name = fields.Char(string='Name', size=64)
    state = fields.Selection(string="Status",
                             selection=[('draft', 'Draft'),
                                        ('posted', 'Posted'),
                                        ('cancel', 'Cancelled')])

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
        TABLE_data_o = workbook.add_format({
            'bold': 1,
            'font_name': 'Aharoni',
            'border': 0,
            'font_size': 12,
            'align': 'center',
            'valign': 'vcenter',
            'font_color': 'black',
        })
        STYLE_LINE_Data = STYLE_LINE
        STYLE_LINE_Data.num_format_str = '#,##0.00_);(#,##0.00)'

        if report_data:
            self.add_xlsx_sheet(report_data, workbook, STYLE_LINE_Data,
                                header_format, STYLE_LINE_HEADER)

        self.excel_sheet_name = 'Lease LL and ROU Report'
        workbook.close()
        output.seek(0)
        self.excel_sheet = base64.b64encode(output.read())
        self.excel_sheet_name = str(self.excel_sheet_name) + '.xlsx'
        return {
            'type': 'ir.actions.act_url',
            'name': 'Lease LL and ROU Report',
            'url': '/web/content/%s/%s/excel_sheet/%s?download=true' % (
                self._name, self.id, self.excel_sheet_name),
            'target': 'self'
        }

    def get_report_data(self):
        data = []
        if self.lease_contract_ids:
            for contract in self.lease_contract_ids:
                if self.state:
                    move_ids = self.env['account.move'].search(
                        [('id', 'in', contract.account_move_ids.ids),
                         ('move_type', '=', 'entry'),
                         ('date', '<=', self.end_date),
                         ('state', '=', self.state),
                         ('company_id', '=', self.env.company.id)])

                    # computation for STLL

                    stll_move_line_ids = self.find_stll_move_lines(move_ids,
                                                                   contract)
                    # computation for LTLL

                    ltll_move_line_ids = self.find_ltll_move_lines(move_ids,
                                                                   contract)

                    # computation for Net ROU
                    fixed_asset_account_move_line_ids = self.find_fixed_asset_account_move_lines(
                        move_ids, contract)

                    depreciation_account_move_line_ids = self.find_depreciation_account_move_lines(
                        move_ids, contract)

                else:
                    move_ids = self.env['account.move'].search(
                        [('id', 'in', contract.account_move_ids.ids),
                         ('move_type', '=', 'entry'),
                         ('date', '<=', self.end_date),
                         ('company_id', '=', self.env.company.id)
                         ])
                    # computation for STLL

                    stll_move_line_ids = self.find_stll_move_lines(move_ids,
                                                                   contract)

                    # computation for LTLL

                    ltll_move_line_ids = self.find_ltll_move_lines(move_ids,
                                                                   contract)

                    # computation for Net ROU
                    fixed_asset_account_move_line_ids = self.find_fixed_asset_account_move_lines(
                        move_ids, contract)
                    depreciation_account_move_line_ids = self.find_depreciation_account_move_lines(
                        move_ids, contract)

                stll_credit_amt = stll_move_line_ids.mapped('credit')
                stll_debit_amt = stll_move_line_ids.mapped('debit')
                stll_amount = sum(stll_credit_amt) + sum(stll_debit_amt)

                ltll_credit_amt = ltll_move_line_ids.mapped('credit')
                ltll_debit_amt = ltll_move_line_ids.mapped('debit')
                ltll_amount = sum(ltll_credit_amt) + sum(ltll_debit_amt)
                asset_credit_amt = fixed_asset_account_move_line_ids.mapped(
                    'credit')
                asset_debit_amt = fixed_asset_account_move_line_ids.mapped(
                    'debit')

                asset_tot_amt = sum(asset_credit_amt) + sum(asset_debit_amt)
                depreciation_credit_amt = depreciation_account_move_line_ids.mapped(
                    'credit')
                depreciation_debit_amt = depreciation_account_move_line_ids.mapped(
                    'debit')

                depreciation_tot_amt = sum(depreciation_credit_amt) + sum(
                    depreciation_debit_amt)

                net_rou = asset_tot_amt - depreciation_tot_amt

                data.append({
                    'leasor_name': contract.name,
                    'external_reference_number': contract.external_reference_number,
                    'project_site': contract.project_site_id.name,
                    'stll': stll_amount,
                    'ltll': ltll_amount,
                    'net_rou': net_rou,
                    'currency': contract.leasee_currency_id.name,
                })
        else:
            lease_contract_ids = self.env['leasee.contract'].search([],
                                                                    order='id ASC')
            for contract in lease_contract_ids:
                if self.state:
                    move_ids = self.env['account.move'].search(
                        [('id', 'in', contract.account_move_ids.ids),
                         ('move_type', '=', 'entry'),
                         ('date', '<=', self.end_date),
                         ('state', '=', self.state),
                         ('company_id', '=', self.env.company.id)])

                    # computation for STLL
                    stll_move_line_ids = self.find_stll_move_lines(move_ids,
                                                                   contract)

                    # computation for LTLL

                    ltll_move_line_ids = self.find_ltll_move_lines(move_ids,
                                                                   contract)

                    # computation for Net ROU
                    fixed_asset_account_move_line_ids = self.find_fixed_asset_account_move_lines(
                        move_ids, contract)

                    depreciation_account_move_line_ids = self.find_depreciation_account_move_lines(
                        move_ids, contract)

                else:
                    move_ids = self.env['account.move'].search(
                        [('id', 'in', contract.account_move_ids.ids),
                         ('move_type', '=', 'entry'),
                         ('date', '<=', self.end_date),
                         ('company_id', '=', self.env.company.id)
                         ])
                    # computation for STLL

                    stll_move_line_ids = self.find_stll_move_lines(move_ids,
                                                                   contract)

                    # computation for LTLL

                    ltll_move_line_ids = self.find_ltll_move_lines(move_ids,
                                                                   contract)

                    # computation for Net ROU
                    fixed_asset_account_move_line_ids = self.find_fixed_asset_account_move_lines(
                        move_ids, contract)

                    depreciation_account_move_line_ids = self.find_depreciation_account_move_lines(
                        move_ids, contract)

                stll_credit_amt = stll_move_line_ids.mapped('credit')
                stll_debit_amt = stll_move_line_ids.mapped('debit')
                stll_amount = sum(stll_credit_amt) + sum(stll_debit_amt)

                ltll_credit_amt = ltll_move_line_ids.mapped('credit')
                ltll_debit_amt = ltll_move_line_ids.mapped('debit')
                ltll_amount = sum(ltll_credit_amt) + sum(ltll_debit_amt)
                asset_credit_amt = fixed_asset_account_move_line_ids.mapped(
                    'credit')
                asset_debit_amt = fixed_asset_account_move_line_ids.mapped(
                    'debit')
                asset_tot_amt = sum(asset_credit_amt) + sum(asset_debit_amt)
                depreciation_credit_amt = depreciation_account_move_line_ids.mapped(
                    'credit')
                depreciation_debit_amt = depreciation_account_move_line_ids.mapped(
                    'debit')
                depreciation_tot_amt = sum(depreciation_credit_amt) + sum(
                    depreciation_debit_amt)
                net_rou = asset_tot_amt - depreciation_tot_amt
                data.append({
                    'leasor_name': contract.name,
                    'external_reference_number': contract.external_reference_number,
                    'project_site': contract.project_site_id.name,
                    'stll': stll_amount,
                    'ltll': ltll_amount,
                    'net_rou': net_rou,
                    'currency': contract.leasee_currency_id.name,
                })

        return data

    def add_xlsx_sheet(self, report_data, workbook, STYLE_LINE_Data,
                       header_format, STYLE_LINE_HEADER):
        self.ensure_one()
        worksheet = workbook.add_worksheet(_('Lease LL & ROU Report'))
        lang = self.env.user.lang
        if lang.startswith('ar_'):
            worksheet.right_to_left()

        row = 0
        col = 0
        worksheet.merge_range(row, row, col, col + 6,
                              _('Lease LL & ROU Report'),
                              STYLE_LINE_HEADER)
        row += 1
        col = 0
        worksheet.write(row, col, _('Lease Name'), header_format)
        col += 1
        worksheet.write(row, col, _('External Reference Number'), header_format)
        col += 1
        worksheet.write(row, col, _('Project Site'), header_format)
        col += 1
        worksheet.write(row, col, _('STLL'), header_format)
        col += 1
        worksheet.write(row, col, _('LTLL'), header_format)
        col += 1
        worksheet.write(row, col, _('Net ROU'), header_format)
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
            worksheet.write(row, col, line['stll'],
                            STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['ltll'],
                            STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['net_rou'],
                            STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['currency'], STYLE_LINE_Data)

    def find_stll_move_lines(self, move_ids, contract):
        stll_move_line_ids = self.env['account.move.line'].search(
            [('move_id', 'in', move_ids.ids), ('account_id', '=',
                                               contract.lease_liability_account_id.id),
             ('company_id', '=', self.env.company.id)])
        return stll_move_line_ids

    def find_ltll_move_lines(self, move_ids, contract):
        ltll_move_line_ids = self.env['account.move.line'].search(
            [('move_id', 'in', move_ids.ids), ('account_id', '=',
                                               contract.long_lease_liability_account_id.id),
             ('company_id', '=', self.env.company.id)])
        return ltll_move_line_ids

    def find_fixed_asset_account_move_lines(self, move_ids, contract):
        fixed_asset_account_move_line_ids = self.env[
            'account.move.line'].search(
            [('move_id', 'in', move_ids.ids), ('account_id', '=',
                                               contract.asset_model_id.account_asset_id.id),
             ('company_id', '=', self.env.company.id)])
        return fixed_asset_account_move_line_ids

    def find_depreciation_account_move_lines(self, move_ids, contract):
        depreciation_account_move_line_ids = self.env[
            'account.move.line'].search(
            [('move_id', 'in', move_ids.ids), ('account_id', '=',
                                               contract.asset_model_id.account_depreciation_id.id),
             ('company_id', '=', self.env.company.id)])
        return depreciation_account_move_line_ids
