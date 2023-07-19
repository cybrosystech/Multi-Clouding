import base64
import datetime
import io
from operator import itemgetter
import xlsxwriter
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
            lease_contract_ids = self.lease_contract_ids
        else:
            lease_contract_ids = self.env['leasee.contract'].search(
                [('company_id', '=', self.env.company.id)],
                order='id ASC')
        lease_names = []
        stll_move_line_ids_qry = []
        ltll_move_line_ids_qry = []
        fixed_asset_account_move_line_ids_qry = []
        depreciation_account_move_line_ids_qry = []
        if lease_contract_ids:
            if self.state:
                # computation for STLL
                self._cr.execute(
                    'select coalesce((sum(item.debit) - sum(item.credit)), 0) '
                    'total,leasee.name as lease_name,leasee.external_reference_number,currency.name as currency_name,'
                    'project_site.name from leasee_contract '
                    'as leasee inner join account_move as journal on '
                    'journal.leasee_contract_id=leasee.id inner join '
                    'account_move_line as item on item.move_id = journal.id '
                    'inner join res_currency as currency on '
                    'currency.id=leasee.leasee_currency_id left join '
                    'account_analytic_account as project_site on '
                    'project_site.id=leasee.project_site_id '
                    'where leasee.id in %(contract)s and '
                    'journal.date <= %(end_date)s'
                    ' and journal.state=%(state)s and ' \
                    'journal.company_id=%(company)s and '
                    'item.account_id=leasee.lease_liability_account_id ' \
                    'group by lease_name,leasee.external_reference_number,' \
                    'currency_name,project_site.name', {
                        'contract': tuple(lease_contract_ids.ids),
                        'end_date': self.end_date,
                        'state': self.state,
                        'company': self.env.company.id,
                    })
                stll_move_line_ids_qry = self._cr.dictfetchall()
                lease_names_stll = list(
                    map(itemgetter('lease_name'), stll_move_line_ids_qry))

                # computation for LTLL

                self._cr.execute(
                    'select coalesce((sum(item.debit) - sum(item.credit)), 0) total,'
                    'leasee.name as lease_name,'
                    'leasee.external_reference_number,'
                    'currency.name as currency_name,'
                    'project_site.name from leasee_contract as '
                    'leasee inner join account_move'
                    ' as journal on '
                    'journal.leasee_contract_id=leasee.id  inner join '
                    'account_move_line as item on '
                    'item.move_id = journal.id inner join '
                    'res_currency as currency on '
                    'currency.id=leasee.leasee_currency_id left join '
                    'account_analytic_account as project_site on '
                    'project_site.id=leasee.project_site_id where '
                    'leasee.id in %(contract)s and '
                    'journal.date <= %(end_date)s and ' \
                    'journal.state=%(state)s and '
                    'journal.company_id=%(company)s and '
                    'item.account_id=leasee.long_lease_liability_account_id '
                    'group by lease_name,leasee.external_reference_number,'
                    'currency_name,project_site.name', {
                        'contract': tuple(lease_contract_ids.ids),
                        'end_date': self.end_date,
                        'state': self.state,
                        'company': self.env.company.id, })
                ltll_move_line_ids_qry = self._cr.dictfetchall()
                lease_names_ltll = list(
                    map(itemgetter('lease_name'), ltll_move_line_ids_qry))

                # computation for Net ROU

                self._cr.execute(
                    'select coalesce((sum(item.debit) - sum(item.credit)), 0) total,'
                    'leasee.name as lease_name,'
                    'leasee.external_reference_number,'
                    'currency.name as currency_name,'
                    'project_site.name from leasee_contract as '
                    'leasee inner join account_asset as asset on '
                    'asset.id = leasee.asset_id '
                    'inner join account_move'
                    ' as journal on journal.asset_id=asset.id or '
                    'journal.leasee_contract_id=leasee.id  inner join '
                    'account_move_line as item on item.move_id=journal.id inner'
                    ' join res_currency as currency on '
                    'currency.id=leasee.leasee_currency_id left join '
                    'account_analytic_account as project_site on '
                    'project_site.id=leasee.project_site_id '
                    'where '
                    'leasee.id in %(contract)s and '
                    'journal.date <= %(end_date)s and '
                    'journal.state=%(state)s and '
                    'journal.company_id=%(company)s and '
                    'item.account_id=asset.account_asset_id group by '
                    'lease_name,leasee.external_reference_number,'
                    'currency_name,project_site.name', {
                        'contract': tuple(lease_contract_ids.ids),
                        'end_date': self.end_date,
                        'state': self.state,
                        'company': self.env.company.id,

                    })
                fixed_asset_account_move_line_ids_qry = self._cr.dictfetchall()
                lease_names_fixed_asset_account_move_line = list(
                    map(itemgetter('lease_name'),
                        fixed_asset_account_move_line_ids_qry))

                self._cr.execute(
                    'select coalesce((sum(item.debit) - sum(item.credit)), 0) total,'
                    'leasee.name as lease_name,'
                    'leasee.external_reference_number,'
                    'currency.name as currency_name,'
                    'project_site.name from leasee_contract as '
                    'leasee inner join account_asset as asset on '
                    'asset.id = leasee.asset_id inner join account_move'
                    ' as journal on journal.asset_id=asset.id or '
                    'journal.leasee_contract_id=leasee.id  inner join '
                    'account_move_line as item on '
                    'item.move_id = journal.id inner join '
                    'res_currency as currency on '
                    'currency.id=leasee.leasee_currency_id left join '
                    'account_analytic_account as project_site on '
                    'project_site.id=leasee.project_site_id where '
                    'leasee.id in %(contract)s and '
                    'journal.date <= %(end_date)s and '
                    'journal.state=%(state)s and '
                    'journal.company_id=%(company)s and '
                    'item.account_id=asset.account_depreciation_id '
                    'group by lease_name,leasee.external_reference_number,'
                    'currency_name,project_site.name',
                    {
                        'contract': tuple(lease_contract_ids.ids),
                        'end_date': self.end_date,
                        'state': self.state,
                        'company': self.env.company.id,

                    }
                )
                depreciation_account_move_line_ids_qry = self._cr.dictfetchall()
                lease_names_depreciation_account_move_line = list(
                    map(itemgetter('lease_name'),
                        depreciation_account_move_line_ids_qry))
            else:
                # computation for STLL
                self._cr.execute(
                    'select coalesce((sum(item.debit) - sum(item.credit)), 0) '
                    'total,leasee.name as lease_name,'
                    'leasee.external_reference_number,'
                    'currency.name as '
                    'currency_name,'
                    'project_site.name from leasee_contract '
                    'as leasee inner join account_move as journal on '
                    'journal.leasee_contract_id=leasee.id inner join '
                    'account_move_line as item on item.move_id = journal.id '
                    ' inner join '
                    'res_currency as currency on '
                    'currency.id=leasee.leasee_currency_id left join '
                    'account_analytic_account as project_site on '
                    'project_site.id=leasee.project_site_id where '
                    'leasee.id in %(contract)s and '
                    'journal.date <= %(end_date)s and ' \
                    'journal.company_id=%(company)s and '
                    'item.account_id=leasee.lease_liability_account_id ' \
                    'group by lease_name,leasee.external_reference_number,' \
                    'currency_name,project_site.name', {
                        'contract': tuple(lease_contract_ids.ids),
                        'end_date': self.end_date,
                        'company': self.env.company.id,
                    })
                stll_move_line_ids_qry = self._cr.dictfetchall()
                lease_names_stll = list(
                    map(itemgetter('lease_name'), stll_move_line_ids_qry))

                # computation for LTLL
                self._cr.execute(
                    'select coalesce((sum(item.debit) - sum(item.credit)), 0) total,'
                    'leasee.name as lease_name,'
                    'leasee.external_reference_number,'
                    'currency.name as currency_name,'
                    'project_site.name from leasee_contract as '
                    'leasee inner join account_move as journal on '
                    'journal.leasee_contract_id=leasee.id  inner join '
                    'account_move_line as item on item.move_id=journal.id'
                    ' inner join '
                    'res_currency as currency on '
                    'currency.id=leasee.leasee_currency_id left join '
                    'account_analytic_account as project_site on '
                    'project_site.id=leasee.project_site_id where '
                    'leasee.id in %(contract)s and '
                    'journal.date <= %(end_date)s '
                    'and journal.company_id=%(company)s and '
                    'item.account_id=leasee.long_lease_liability_account_id '
                    'group by lease_name,leasee.external_reference_number,' \
                    'currency_name,project_site.name',
                    {
                        'contract': tuple(lease_contract_ids.ids),
                        'end_date': self.end_date,
                        'company': self.env.company.id, })
                ltll_move_line_ids_qry = self._cr.dictfetchall()
                lease_names_ltll = list(
                    map(itemgetter('lease_name'), ltll_move_line_ids_qry))
                # computation for Net ROU

                self._cr.execute(
                    'select coalesce((sum(item.debit) - sum(item.credit)), 0) total,'
                    'leasee.name as lease_name,'
                    'leasee.external_reference_number,'
                    'currency.name as currency_name,'
                    'project_site.name from leasee_contract as '
                    'leasee inner join account_asset as asset on '
                    'asset.id = leasee.asset_id '
                    ' inner join account_move'
                    ' as journal on journal.asset_id=asset.id or '
                    'journal.leasee_contract_id=leasee.id  inner join '
                    'account_move_line as item on item.move_id = journal.id '
                    ' inner join '
                    'res_currency as currency on '
                    'currency.id=leasee.leasee_currency_id left join '
                    'account_analytic_account as project_site on '
                    'project_site.id=leasee.project_site_id where '
                    'leasee.id in %(contract)s and '
                    'journal.date <= %(end_date)s and '
                    'journal.company_id=%(company)s and '
                    'item.account_id=asset.account_asset_id group by '
                    'lease_name,leasee.external_reference_number,'
                    'currency_name,project_site.name', {
                        'contract': tuple(lease_contract_ids.ids),
                        'end_date': self.end_date,
                        'company': self.env.company.id,
                    })
                fixed_asset_account_move_line_ids_qry = self._cr.dictfetchall()
                lease_names_fixed_asset_account_move_line = list(
                    map(itemgetter('lease_name'),
                        fixed_asset_account_move_line_ids_qry))

                self._cr.execute(
                    'select coalesce((sum(item.debit) - sum(item.credit)), 0) total,'
                    'leasee.name as lease_name,'
                    'leasee.external_reference_number,'
                    'currency.name as currency_name,'
                    'project_site.name from leasee_contract as '
                    'leasee inner join account_asset as asset on '
                    'asset.id = leasee.asset_id inner join account_move'
                    ' as journal on journal.asset_id=asset.id or '
                    'journal.leasee_contract_id=leasee.id  inner join '
                    'account_move_line as item on '
                    'item.move_id = journal.id inner join '
                    'res_currency as currency on '
                    'currency.id=leasee.leasee_currency_id left join '
                    'account_analytic_account as project_site on '
                    'project_site.id=leasee.project_site_id where '
                    'leasee.id in %(contract)s and '
                    'journal.date <= %(end_date)s and '
                    'journal.company_id=%(company)s and '
                    'item.account_id=asset.account_depreciation_id '
                    'group by lease_name,leasee.external_reference_number,'
                    'currency_name,project_site.name',
                    {
                        'contract': tuple(lease_contract_ids.ids),
                        'end_date': self.end_date,
                        'company': self.env.company.id,
                    }
                )
                depreciation_account_move_line_ids_qry = self._cr.dictfetchall()
                lease_names_depreciation_account_move_line = list(
                    map(itemgetter('lease_name'),
                        depreciation_account_move_line_ids_qry))
            lease_names = lease_names_stll + lease_names_ltll + lease_names_fixed_asset_account_move_line + lease_names_depreciation_account_move_line

        lease_names = list(set(lease_names))
        lease_names.sort()
        for lease in lease_names:
            stll_amount = list(
                filter(lambda x: x['lease_name'] == lease,
                       stll_move_line_ids_qry))
            ltll_amount = list(
                filter(lambda x: x['lease_name'] == lease,
                       ltll_move_line_ids_qry))
            fixed_asset_amount = list(
                filter(lambda x: x['lease_name'] == lease,
                       fixed_asset_account_move_line_ids_qry))
            depreciation_amount = list(
                filter(lambda x: x['lease_name'] == lease,
                       depreciation_account_move_line_ids_qry))
            data_list = stll_amount + ltll_amount + fixed_asset_amount + depreciation_amount
            if len(fixed_asset_amount) >= 1 and len(depreciation_amount) >= 1:
                data.append({
                    'leasor_name': lease,
                    'external_reference_number': data_list[0][
                        "external_reference_number"],
                    'project_site': data_list[0]["name"],
                    'stll': stll_amount[0]['total'] if len(
                        stll_amount) >= 1 else 0.0,
                    'ltll': ltll_amount[0]['total'] if len(
                        ltll_amount) >= 1 else 0.0,
                    'net_rou': fixed_asset_amount[0]["total"] +
                               depreciation_amount[0]["total"],
                    'currency': data_list[0]["currency_name"],
                })
            elif len(fixed_asset_amount) >= 1:
                data.append({
                    'leasor_name': lease,
                    'external_reference_number': data_list[0][
                        "external_reference_number"],
                    'project_site': data_list[0]["name"],
                    'stll': stll_amount[0]['total'] if len(
                        stll_amount) >= 1 else 0.0,
                    'ltll': ltll_amount[0]['total'] if len(
                        ltll_amount) >= 1 else 0.0,
                    'net_rou': fixed_asset_amount[0]["total"],
                    'currency': data_list[0]["currency_name"],
                })
            elif len(depreciation_amount) >= 1:
                data.append({
                    'leasor_name': lease,
                    'external_reference_number': data_list[0][
                        "external_reference_number"],
                    'project_site': data_list[0]["name"],
                    'stll': stll_amount[0]['total'] if len(
                        stll_amount) >= 1 else 0.0,
                    'ltll': ltll_amount[0]['total'] if len(
                        ltll_amount) >= 1 else 0.0,
                    'net_rou': depreciation_amount[0]["total"],
                    'currency': data_list[0]["currency_name"],
                })
            else:
                data.append({
                    'leasor_name': lease,
                    'external_reference_number': data_list[0][
                        "external_reference_number"],
                    'project_site': data_list[0]["name"],
                    'stll': stll_amount[0]['total'] if len(
                        stll_amount) >= 1 else 0.0,
                    'ltll': ltll_amount[0]['total'] if len(
                        ltll_amount) >= 1 else 0.0,
                    'net_rou': 0.0,
                    'currency': data_list[0]["currency_name"],
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
