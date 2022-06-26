import io

from dateutil.relativedelta import relativedelta

from odoo import fields, models
from odoo.exceptions import UserError
from odoo.tools import date_utils, xlsxwriter
from odoo.tools.safe_eval import datetime, json
import calendar


class ProfitabilityReportWizard(models.TransientModel):
    _name = "profitability.report.wizard"

    def default_service_revenue(self):
        return self.env['account.account'].search([('code', '=',
                                                    '411201'),
                                                   ('company_id',
                                                    '=',
                                                    self.env.company.id)])

    def default_investment_revenue(self):
        return self.env['account.account'].search([('code', '=',
                                                    '411101'),
                                                   ('company_id',
                                                    '=',
                                                    self.env.company.id)])

    def default_colocation(self):
        return self.env['account.account'].search([('code', '=',
                                                    '411501'),
                                                   ('company_id',
                                                    '=',
                                                    self.env.company.id)])

    def default_insurance(self):
        return self.env['account.account'].search([('code', '=',
                                                    '422701'),
                                                   ('company_id',
                                                    '=',
                                                    self.env.company.id)])

    def default_energy_cost(self):
        return self.env['account.account'].search([('code', 'in',
                                                    ['422401', '422401']),
                                                   ('company_id',
                                                    '=',
                                                    self.env.company.id)])

    def default_security(self):
        return self.env['account.account'].search([('code', '=',
                                                    '422301'),
                                                   ('company_id',
                                                    '=',
                                                    self.env.company.id)])

    def default_rou_depreciation(self):
        return self.env['account.account'].search([('code', '=',
                                                    '554101'),
                                                   ('company_id',
                                                    '=',
                                                    self.env.company.id)])

    service_revenue = fields.Many2many('account.account', 'service_revenue_rel',
                                       string='Service Revenue',
                                       default=default_service_revenue)
    investment_revenue = fields.Many2many('account.account',
                                          'investment_revenue_rel',
                                          string='Investment Revenue',
                                          default=default_investment_revenue)
    colocation = fields.Many2many('account.account', 'colocation_rel',
                                  string='Colocation',
                                  default=default_colocation)
    pass_through_energy = fields.Many2many('account.account',
                                           'pass_through_energy',
                                           string='Pass Through Energy')
    active_sharing_fees = fields.Many2many('account.account',
                                           'active_sharing_fees',
                                           string='Active Sharing Fees')
    discount = fields.Many2many('account.account', 'disc',
                                string='Discount')
    site_maintenance = fields.Many2many('account.account', 'site_maintenance')
    site_maintenance_lim = fields.Many2many('account.account',
                                            'site_maintenance_lim')
    insurance = fields.Many2many('account.account', 'insurance',
                                 string="Insurance", default=default_insurance)
    energy_cost = fields.Many2many('account.account', 'energy_cost',
                                   string='Energy Cost',
                                   default=default_energy_cost)
    security = fields.Many2many('account.account', 'security',
                                string='Security', default=default_security)
    service_level_credit = fields.Many2many('account.account',
                                            'service_level_credit',
                                            string='Service Level Credit')
    rou_depreciation = fields.Many2many('account.account',
                                        'rou_depreciation_rels',
                                        string='ROU Depreciation',
                                        default=default_rou_depreciation)
    fa_depreciation = fields.Many2many('account.account',
                                       'fa_depreciation_rels',
                                       string='FA Depreciation')
    fa_depreciation_lim = fields.Many2many('account.account',
                                           'fa_depreciation_lim_rels',
                                           string='FA Depreciation')
    lease_finance_cost = fields.Many2many('account.account',
                                          'lease_finance_cost_rels',
                                          string='Leases Finance Cost')

    period = fields.Selection(selection=([('this_month', 'This Month'),
                                          ('this_quarter', 'This Quarter'),
                                          ('this_financial_year',
                                           'This Financial Year'),
                                          ('last_month', 'Last Month'),
                                          ('last_quarter', 'Last Quarter'),
                                          ('last_financial_year',
                                           'Last Financial Year'),
                                          ('custom', 'Custom')]),
                              string='Periods', required=True,
                              default='this_month')
    from_date = fields.Date('From')
    to_date = fields.Date('To')

    def generate_xlsx_report(self):

        current_date = fields.Date.today()
        from_date = ''
        to_date = ''
        first, last = calendar.monthrange(current_date.year, current_date.month)
        if self.period == 'this_month':
            from_date = datetime.date(current_date.year, current_date.month, 1)
            to_date = datetime.date(current_date.year, current_date.month, last)
        if self.period == 'this_quarter':
            current_quarter = (current_date.month - 1) // 3 + 1
            from_date = datetime.date(current_date.year,
                                      3 * current_quarter - 2, 1)
            to_date = datetime.date(current_date.year, 3 * current_quarter,
                                    last)
        if self.period == 'this_financial_year':
            first, last = calendar.monthrange(current_date.year,
                                              12)
            from_date = datetime.date(current_date.year, 1, 1)
            to_date = datetime.date(current_date.year, 12, last)
        if self.period == 'last_month':
            date = current_date - relativedelta(months=1)
            first, last = calendar.monthrange(date.year,
                                              date.month)
            from_date = datetime.date(date.year, date.month, 1)
            to_date = datetime.date(date.year, date.month, last)
        if self.period == 'last_quarter':
            last_quarter = ((current_date.month - 1) // 3 + 1) - 1
            first, last = calendar.monthrange(current_date.year,
                                              3 * last_quarter)
            from_date = datetime.date(current_date.year,
                                      3 * last_quarter - 2, 1)
            to_date = datetime.date(current_date.year, 3 * last_quarter,
                                    last)
        if self.period == 'last_financial_year':
            last_financial_year = current_date.year - 1
            first, last = calendar.monthrange(last_financial_year,
                                              12)
            from_date = datetime.date(last_financial_year, 1, 1)
            to_date = datetime.date(last_financial_year, 12, last)
        if self.from_date and self.to_date:
            if self.from_date > self.to_date:
                raise UserError("Start date should be less than end date")
        data = {
            'ids': self.ids,
            'model': self._name,
            'service_revenue_ids': self.service_revenue.ids,
            'investment_revenue_ids': self.investment_revenue.ids,
            'colocation_ids': self.colocation.ids,
            'pass_through_energy_ids': self.pass_through_energy.ids,
            'active_sharing_fees_ids': self.active_sharing_fees.ids,
            'discount_ids': self.discount.ids,
            'site_maintenance_code': self.site_maintenance.code,
            'site_maintenance_lim_code': self.site_maintenance_lim.code,
            'insurance_ids': self.insurance.ids,
            'energy_cost_ids': self.energy_cost.ids,
            'security_ids': self.security.ids,
            'service_level_credit_ids': self.service_level_credit.ids,
            'rou_depreciation_ids': self.rou_depreciation.ids,
            'fa_depreciation_code': self.fa_depreciation.code,
            'fa_depreciation_lim_code': self.fa_depreciation_lim.code,
            'lease_finance_cost_ids': self.lease_finance_cost.ids,
            'from': from_date if from_date else self.from_date,
            'to': to_date if to_date else self.to_date,
            'company_id': self.env.company.id
        }
        return {
            'type': 'ir.actions.report',
            'data': {'model': 'profitability.report.wizard',
                     'options': json.dumps(data,
                                           default=date_utils.json_default),
                     'output_format': 'xlsx',
                     'report_name': 'Profitability Owned Report',
                     },
            'report_type': 'xlsx'
        }

    def get_xlsx_report(self, data, response):
        total_site = 0
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})

        project_site = self.env['account.analytic.account'].search(
            [('analytic_account_type',
              '=', 'project_site'), ('company_id',
                                     '=',
                                     data['company_id']),
             ('group_id.name', 'ilike', 'owned')])
        account_ids = self.env['account.account'].search(
            [('code', 'in', [site for
                             site in range(
                    int(data['site_maintenance_code']),
                    int(data['site_maintenance_lim_code']) + 1)])]).mapped('id')
        account_fa_depreciation_ids = self.env['account.account'].search(
            [('code', 'in', [site for
                             site in range(
                    int(data['fa_depreciation_code']),
                    int(data['fa_depreciation_lim_code']) + 1)])]).mapped('id')
        profitability_report = []
        for i in project_site:
            prof_rep = {}
            prof_rep.update({
                'project': i.name,
            })
            service_revenue = self.env['account.move.line'].search(
                [('account_id', 'in', data['service_revenue_ids']),
                 ('project_site_id', '=', i.id),
                 ('move_id.date', '<=', data['to']),
                 ('move_id.date', '>=', data['from'])])
            total = sum(service_revenue.mapped('debit')) + sum(
                service_revenue.mapped('credit'))
            prof_rep.update({
                'service_revenue': total,
            })
            investment_revenue = self.env['account.move.line'].search(
                [('account_id', 'in', data['investment_revenue_ids']),
                 ('project_site_id', '=', i.id),
                 ('move_id.date', '<=', data['to']),
                 ('move_id.date', '>=', data['from'])])
            total = sum(investment_revenue.mapped('debit')) + sum(
                investment_revenue.mapped('credit'))
            prof_rep.update({
                'investment_revenue': total,
            })
            colocation = self.env['account.move.line'].search(
                [('account_id', 'in', data['colocation_ids']),
                 ('project_site_id', '=', i.id),
                 ('move_id.date', '<=', data['to']),
                 ('move_id.date', '>=', data['from'])])
            total = sum(colocation.mapped('debit')) + sum(
                colocation.mapped('credit'))
            prof_rep.update({
                'colocation': total,
            })
            pass_through_energy = self.env['account.move.line'].search(
                [('account_id', 'in', data['pass_through_energy_ids']),
                 ('project_site_id', '=', i.id),
                 ('move_id.date', '<=', data['to']),
                 ('move_id.date', '>=', data['from'])])
            total = sum(pass_through_energy.mapped('debit')) + sum(
                pass_through_energy.mapped('credit'))
            prof_rep.update({
                'pass_through_energy': total,
            })
            active_sharing_fees = self.env['account.move.line'].search(
                [('account_id', 'in', data['active_sharing_fees_ids']),
                 ('project_site_id', '=', i.id),
                 ('move_id.date', '<=', data['to']),
                 ('move_id.date', '>=', data['from'])])
            total = sum(active_sharing_fees.mapped('debit')) + sum(
                active_sharing_fees.mapped('credit'))
            prof_rep.update({
                'active_sharing_fees': total,
            })
            discount = self.env['account.move.line'].search(
                [('account_id', 'in', data['discount_ids']),
                 ('project_site_id', '=', i.id),
                 ('move_id.date', '<=', data['to']),
                 ('move_id.date', '>=', data['from'])])
            total = sum(discount.mapped('debit')) + sum(
                discount.mapped('credit'))
            prof_rep.update({
                'discount': total,
            })
            total_revenue = prof_rep['service_revenue'] + prof_rep[
                'investment_revenue'] + prof_rep['colocation'] + prof_rep[
                                'pass_through_energy'] + prof_rep[
                                'active_sharing_fees'] + prof_rep['discount']
            prof_rep.update({
                'total_revenue': total_revenue,
            })
            # profitability_report.append(prof_rep)
            if data['site_maintenance_code'] and data[
                'site_maintenance_lim_code']:
                for account in account_ids:
                    site_maintenance = self.env['account.move.line'].search(
                        [('account_id', '=', account),
                         ('project_site_id', '=', i.id),
                         ('move_id.date', '<=', data['to']),
                         ('move_id.date', '>=', data['from'])])
                    total_site += sum(site_maintenance.mapped('debit')) + sum(
                        site_maintenance.mapped('credit'))
            prof_rep.update({
                'site_maintenance': total_site,
            })
            insurance = self.env['account.move.line'].search(
                [('account_id', 'in', data['insurance_ids']),
                 ('project_site_id', '=', i.id),
                 ('move_id.date', '<=', data['to']),
                 ('move_id.date', '>=', data['from'])])
            total = sum(insurance.mapped('debit')) + sum(
                insurance.mapped('credit'))
            prof_rep.update({
                'insurance': total
            })
            energy_cost = self.env['account.move.line'].search(
                [('account_id', 'in', data['energy_cost_ids']),
                 ('project_site_id', '=', i.id),
                 ('move_id.date', '<=', data['to']),
                 ('move_id.date', '>=', data['from'])])
            total = sum(energy_cost.mapped('debit')) + sum(
                energy_cost.mapped('credit'))
            prof_rep.update({
                'energy_cost': total
            })
            security = self.env['account.move.line'].search(
                [('account_id', 'in', data['security_ids']),
                 ('project_site_id', '=', i.id),
                 ('move_id.date', '<=', data['to']),
                 ('move_id.date', '>=', data['from'])])
            total = sum(security.mapped('debit')) + sum(
                security.mapped('credit'))
            prof_rep.update({
                'security': total
            })
            service_level_credit = self.env['account.move.line'].search(
                [('account_id', 'in', data['service_level_credit_ids']),
                 ('project_site_id', '=', i.id),
                 ('move_id.date', '<=', data['to']),
                 ('move_id.date', '>=', data['from'])])
            total = sum(service_level_credit.mapped('debit')) + sum(
                service_level_credit.mapped('credit'))
            prof_rep.update({
                'service_level_credit': total
            })
            total_cost = prof_rep['site_maintenance'] + prof_rep['insurance'] + \
                         prof_rep['energy_cost'] + prof_rep['security'] + \
                         prof_rep['service_level_credit']
            jdo = total_revenue + total_cost
            total_percent = ''
            if total_revenue != 0:
                total_percent = (total_cost / total_revenue) * 100
            prof_rep.update({
                'total_cost': total_cost,
                'jdo': jdo,
                '%': total_percent if total_percent else 0
            })
            rou_depreciation = self.env['account.move.line'].search(
                [('account_id', 'in', data['rou_depreciation_ids']),
                 ('project_site_id', '=', i.id),
                 ('move_id.date', '<=', data['to']),
                 ('move_id.date', '>=', data['from'])])
            total = sum(rou_depreciation.mapped('debit')) + sum(
                rou_depreciation.mapped('credit'))
            prof_rep.update({
                'rou_depreciation': total
            })
            if data['fa_depreciation_code'] and data[
                'fa_depreciation_lim_code']:
                for account in account_fa_depreciation_ids:
                    fa_depreciation = self.env['account.move.line'].search(
                        [('account_id', '=', account),
                         ('project_site_id', '=', i.id),
                         ('move_id.date', '<=', data['to']),
                         ('move_id.date', '>=', data['from'])])
                    total_site += sum(fa_depreciation.mapped('debit')) + sum(
                        fa_depreciation.mapped('credit'))
            prof_rep.update({
                'fa_depreciation': total_site,
            })
            lease_finance_cost = self.env['account.move.line'].search(
                [('account_id', 'in', data['lease_finance_cost_ids']),
                 ('project_site_id', '=', i.id),
                 ('move_id.date', '<=', data['to']),
                 ('move_id.date', '>=', data['from'])])
            total = sum(lease_finance_cost.mapped('debit')) + sum(
                lease_finance_cost.mapped('credit'))
            prof_rep.update({
                'lease_finance_cost': total
            })
            profitability_report.append(prof_rep)

        logged_users = self.env['res.company']._company_default_get(
            'rent.request')
        sheet = workbook.add_worksheet()

        main_head = workbook.add_format(
            {'font_size': 13, 'align': 'center', 'bg_color': '#34a4eb',
             'font_color': '#f2f7f4', 'border': 2})

        head = workbook.add_format(
            {'font_size': 13, 'align': 'center', 'bg_color': '#1a1c99',
             'font_color': '#f2f7f4', 'border': 2})

        sub_heading = workbook.add_format(
            {'valign': 'vcenter', 'bg_color': '#1a1c99',
             'font_color': '#f2f7f4', 'border': 2})

        sub_heading1 = workbook.add_format(
            {'align': 'center', 'valign': 'vcenter', 'bg_color': '#7434eb',
             'font_color': '#f2f7f4', 'border': 2})

        sheet.set_row(3, 70)

        sheet.set_column('B3:B3', 15)
        sheet.set_column('C3:C3', 20)
        sheet.set_column('D4:R4', 20)

        sheet.write('B3', 'Site Number', sub_heading)
        sheet.write('C3', 'Site code', sub_heading)

        sheet.write('B4', 'Site Number', sub_heading1)
        sheet.write('C4', 'Site code', sub_heading1)
        sheet.write('D4', 'Service Revenue', sub_heading1)
        sheet.write('E4', 'Investment Revenue', sub_heading1)
        sheet.write('F4', 'Colocation', sub_heading1)
        sheet.write('G4', 'Pass Through Eenrgy', sub_heading1)
        sheet.write('H4', 'Active Sharing fees', sub_heading1)
        sheet.write('I4', 'Discount', sub_heading1)
        sheet.write('J4', 'Total Revenues', sub_heading1)
        sheet.write('K4', 'Site Maintenance', sub_heading1)
        sheet.write('L4', 'Site Rent', sub_heading1)
        sheet.write('M4', 'Insurance', sub_heading1)
        sheet.write('N4', 'Energy Cost', sub_heading1)
        sheet.write('O4', 'Security', sub_heading1)
        sheet.write('P4', 'Service level Credits', sub_heading1)
        sheet.write('Q4', 'Total Costs', sub_heading1)
        sheet.write('R4', 'JOD', sub_heading1)
        sheet.write('S4', '%', sub_heading1)
        sheet.write('U4', 'ROU Depreciation', sub_heading1)
        sheet.write('V4', 'FA Depreciation', sub_heading1)
        sheet.write('W4', 'Leases Finance Cost', sub_heading1)

        sheet.merge_range('B2:S2', 'JANUARY', main_head)
        sheet.merge_range('U2:W2', '', main_head)
        sheet.merge_range('D3:J3', 'Revenues', head)
        sheet.merge_range('K3:Q3', 'Costs', head)
        sheet.merge_range('R3:S3', 'Gross Profit', head)
        sheet.merge_range('U3:W3', '', head)

        row_num = 3
        col_num = 1
        sln_no = 1

        for i in profitability_report:
            sheet.write(row_num + 1, col_num, sln_no)
            sheet.write(row_num + 1, col_num + 1, i.get('project'))
            sheet.write(row_num + 1, col_num + 2, i.get('service_revenue'))
            sheet.write(row_num + 1, col_num + 3, i.get('investment_revenue'))
            sheet.write(row_num + 1, col_num + 4, i.get('colocation'))
            sheet.write(row_num + 1, col_num + 5, i.get('pass_through_energy'))
            sheet.write(row_num + 1, col_num + 6, i.get('active_sharing_fees'))
            sheet.write(row_num + 1, col_num + 7, i.get('discount'))
            sheet.write(row_num + 1, col_num + 8, i.get('total_revenue'))
            sheet.write(row_num + 1, col_num + 9, i.get('site_maintenance'))
            sheet.write(row_num + 1, col_num + 11, i.get('insurance'))
            sheet.write(row_num + 1, col_num + 12, i.get('energy_cost'))
            sheet.write(row_num + 1, col_num + 13, i.get('security'))
            sheet.write(row_num + 1, col_num + 14,
                        i.get('service_level_credit'))
            sheet.write(row_num + 1, col_num + 15,
                        i.get('total_cost'))
            sheet.write(row_num + 1, col_num + 16, i.get('jdo'))
            sheet.write(row_num + 1, col_num + 17, i.get('%'))
            sheet.write(row_num + 1, col_num + 19, i.get('rou_depreciation'))
            sheet.write(row_num + 1, col_num + 20, i.get('fa_depreciation'))
            sheet.write(row_num + 1, col_num + 21, i.get('lease_finance_cost'))
            row_num = row_num + 1
            sln_no = sln_no + 1

        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()
