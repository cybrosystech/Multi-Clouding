from datetime import time
from typing import io

from odoo import api, fields, models, tools, exceptions
from odoo.exceptions import UserError
from odoo.osv import expression
from odoo.tools import date_utils, io, xlsxwriter
from odoo.tools.safe_eval import datetime, json


class ProfitabilityReportWizard(models.TransientModel):
    _name = "profitability.report.wizard"

    def default_service_revenue(self):
        return self.env['account.account'].search([('code', '=',
                                                    '411201')])

    def default_investment_revenue(self):
        return self.env['account.account'].search([('code', '=',
                                                    '411101')])

    def default_colocation(self):
        return self.env['account.account'].search([('code', '=',
                                                    '411501')])

    def default_insurance(self):
        return self.env['account.account'].search([('code', '=',
                                                    '422701')])

    def default_energy_cost(self):
        return self.env['account.account'].search([('code', 'in',
                                                    ['422401', '422401'])])

    def default_security(self):
        return self.env['account.account'].search([('code', '=',
                                                    '422301')])

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
        # if self.date_from and self.date_to:
        #     if self.date_from > self.date_to:
        #         raise UserError("Start date should be less than end date")
        data = {
            'ids': self.ids,
            'model': self._name,
            'service_revenue_ids': self.service_revenue.ids,
            'service_revenue_code': self.service_revenue.code,
            'investment_revenue_ids': self.investment_revenue.ids,
            'investment_revenue_code': self.investment_revenue.code,
            'colocation_ids': self.colocation.ids,
            'colocation_code': self.colocation.code,
            'pass_through_energy_ids': self.pass_through_energy.ids,
            'pass_through_energy_code': self.pass_through_energy.code,
            'active_sharing_fees_ids': self.active_sharing_fees.ids,
            'active_sharing_fees_code': self.active_sharing_fees.code,
            'discount_ids': self.discount.ids,
            'discount_code': self.discount.code,
            'site_maintenance_code': self.site_maintenance.code,
            'site_maintenance_lim_code': self.site_maintenance_lim.code,
            'insurance_ids': self.insurance.ids,
            'insurance_code': self.insurance.code,
            'energy_cost_ids': self.energy_cost.ids,
            'energy_cost_code': self.energy_cost.code,
            'security_ids': self.security.ids,
            'security_code': self.security.code,
            'service_level_credit_ids': self.service_level_credit.ids,
            'service_level_credit_code': self.service_level_credit.code,
            'from': self.from_date,
            'to': self.to_date,
        }
        return {
            'type': 'ir.actions.report',
            'data': {'model': 'profitability.report.wizard',
                     'options': json.dumps(data,
                                           default=date_utils.json_default),
                     'output_format': 'xlsx',
                     'report_name': 'Profitability Report',
                     },
            'report_type': 'xlsx'
        }

    def get_xlsx_report(self, data, response):
        total_site = 0
        print(data)
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})

        project_site = self.env['account.analytic.account'].search(
            [('analytic_account_type',
              '=', 'project_site')])
        print(project_site)
        account_ids = self.env['account.account'].search(
            [('code', 'in', [site for
                             site in range(
                    int(data['site_maintenance_code']),
                    int(data['site_maintenance_lim_code']) + 1)])]).mapped(
            'id')
        profitability_report = []
        for i in project_site:
            prof_rep = {}
            prof_rep.update({
                'project': i.name,
            })
            service_revenue = self.env['account.move.line'].search(
                [('account_id', 'in', data['service_revenue_ids']),
                 ('project_site_id', '=', i.id)])
            total = sum(service_revenue.mapped('debit')) + sum(
                service_revenue.mapped('credit'))
            prof_rep.update({
                'service_revenue': total,
            })
            investment_revenue = self.env['account.move.line'].search(
                [('account_id', 'in', data['investment_revenue_ids']),
                 ('project_site_id', '=', i.id)])
            total = sum(investment_revenue.mapped('debit')) + sum(
                investment_revenue.mapped('credit'))
            prof_rep.update({
                'investment_revenue': total,
            })
            colocation = self.env['account.move.line'].search(
                [('account_id', 'in', data['colocation_ids']),
                 ('project_site_id', '=', i.id)])
            total = sum(colocation.mapped('debit')) + sum(
                colocation.mapped('credit'))
            prof_rep.update({
                'colocation': total,
            })
            pass_through_energy = self.env['account.move.line'].search(
                [('account_id', 'in', data['pass_through_energy_ids']),
                 ('project_site_id', '=', i.id)])
            total = sum(pass_through_energy.mapped('debit')) + sum(
                pass_through_energy.mapped('credit'))
            prof_rep.update({
                'pass_through_energy': total,
            })
            active_sharing_fees = self.env['account.move.line'].search(
                [('account_id', 'in', data['active_sharing_fees_ids']),
                 ('project_site_id', '=', i.id)])
            total = sum(active_sharing_fees.mapped('debit')) + sum(
                active_sharing_fees.mapped('credit'))
            prof_rep.update({
                'active_sharing_fees': total,
            })
            discount = self.env['account.move.line'].search(
                [('account_id', 'in', data['discount_ids']),
                 ('project_site_id', '=', i.id)])
            total = sum(discount.mapped('debit')) + sum(
                discount.mapped('credit'))
            prof_rep.update({
                'discount': total,
            })
            total_revenue = prof_rep['service_revenue'] + prof_rep[
                'investment_revenue'] + prof_rep['colocation'] + prof_rep[
                                'pass_through_energy'] + prof_rep[
                                'active_sharing_fees'] + prof_rep['discount']
            # print(type(prof_rep['service_revenue']))
            prof_rep.update({
                'total_revenue': total_revenue,
            })
            profitability_report.append(prof_rep)
            if data['site_maintenance_code'] and data[
                'site_maintenance_lim_code']:
                for account in account_ids:
                    site_maintenance = self.env['account.move.line'].search(
                        [('account_id', '=', account),
                         ('project_site_id', '=', i.id)])
                    total_site += sum(site_maintenance.mapped('debit')) + sum(
                        site_maintenance.mapped('credit'))
            prof_rep.update({
                'site_maintenance': total_site,
            })
            insurance = self.env['account.move.line'].search(
                [('account_id', 'in', data['insurance_ids']),
                 ('project_site_id', '=', i.id)])
            total = sum(insurance.mapped('debit')) + sum(
                insurance.mapped('credit'))
            prof_rep.update({
                'insurance': total
            })
            energy_cost = self.env['account.move.line'].search(
                [('account_id', 'in', data['energy_cost_ids']),
                 ('project_site_id', '=', i.id)])
            total = sum(energy_cost.mapped('debit')) + sum(
                energy_cost.mapped('credit'))
            prof_rep.update({
                'energy_cost': total
            })
            security = self.env['account.move.line'].search(
                [('account_id', 'in', data['security_ids']),
                 ('project_site_id', '=', i.id)])
            total = sum(security.mapped('debit')) + sum(
                security.mapped('credit'))
            prof_rep.update({
                'security': total
            })
            service_level_credit = self.env['account.move.line'].search(
                [('account_id', 'in', data['service_level_credit_ids']),
                 ('project_site_id', '=', i.id)])
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
        print(profitability_report)

        logged_users = self.env['res.company']._company_default_get(
            'rent.request')
        sheet = workbook.add_worksheet()

        head = workbook.add_format({'align': 'center',
                                    'bg_color': 'blue',
                                    'font_size': '13px'})
        head.set_font_color('white')

        account = workbook.add_format({'bg_color': 'blue'})
        accounts = workbook.add_format({'bg_color': '#34eb77'})
        headings = workbook.add_format({'bg_color': 'blue'})
        sub_heading = workbook.add_format({'bg_color': 'blue'})

        accounts.set_font_color('white')
        headings.set_font_color('white')
        sub_heading.set_font_color('white')

        sub_heading.set_align('vcenter')

        sheet.set_row(2, 70)
        sheet.set_row(4, 60)

        sheet.set_column('B3:H3', 20)
        sheet.set_column('J3:K3', 20)
        sheet.set_column('L3:L3', 30)
        sheet.set_column('M3:M3', 20)
        sheet.set_column('N3:T3', 15)
        sheet.set_column('E5:E5', 35)
        sheet.set_column('F5:F5', 15)
        sheet.set_column('I5:I5', 15)
        sheet.set_column('O5:T5', 15)

        sheet.write('B3', 'Account', account)
        sheet.write('C3', '', account)
        sheet.write('D3', data['service_revenue_code'] if data[
            'service_revenue_code'] else 'NA', accounts)
        sheet.write('E3', data['investment_revenue_code'] if data[
            'investment_revenue_code'] else 'NA', accounts)
        sheet.write('F3', data['colocation_code'] if data[
            'colocation_code'] else 'NA', accounts)
        sheet.write('G3', 'NA', headings)
        sheet.write('H3', 'NA', headings)
        sheet.write('I3', 'NA', headings)
        sheet.write('J3', 'Total', headings)
        sheet.write('K3', '425100 to 425299', headings)
        sheet.write('L3', 'Manual till IFRS goes ', headings)
        sheet.write('M3', '', account)
        sheet.write('N3', data['insurance_code'], headings)
        sheet.write('O3', '422401 and 424201', headings)
        sheet.write('P3', '422301', headings)
        sheet.write('Q3', 'NA', headings)
        sheet.write('R3', 'Calculations', headings)
        sheet.write('S3', 'Calculations', headings)
        sheet.write('T3', 'Calculations', headings)

        sheet.write('B4', 'Site Number', headings)
        sheet.write('C4', 'Site code', headings)

        sheet.write('B5', 'Site Number', sub_heading)
        sheet.write('C5', 'Site code', sub_heading)
        sheet.write('D5', 'Service Revenue', sub_heading)
        sheet.write('E5', 'Investment Revenue', sub_heading)
        sheet.write('F5', 'Colocation', sub_heading)
        sheet.write('G5', 'Pass Through Eenrgy', sub_heading)
        sheet.write('H5', 'Active Sharing fees', sub_heading)
        sheet.write('I5', 'Discount', sub_heading)
        sheet.write('J5', 'Total Revenues', sub_heading)
        sheet.write('K5', 'Site Maintennace', sub_heading)
        sheet.write('L5', 'Site Rent', sub_heading)
        sheet.write('M5', '', sub_heading)
        sheet.write('N5', 'Insurance', sub_heading)
        sheet.write('O5', 'Energy Cost', sub_heading)
        sheet.write('P5', 'Security', sub_heading)
        sheet.write('Q5', 'Service level Credits', sub_heading)
        sheet.write('R5', 'Total Costs', sub_heading)
        sheet.write('S5', 'JOD', sub_heading)
        sheet.write('T5', '%', sub_heading)

        sheet.merge_range('C2:T2', 'JANUARY', head)
        sheet.merge_range('D4:J4', 'Revenues', head)
        sheet.merge_range('K4:R4', 'Costs', head)
        sheet.merge_range('S4:T4', 'Gross profit', head)

        #
        row_num = 4
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
            sheet.write(row_num + 1, col_num + 12, i.get('insurance'))
            sheet.write(row_num + 1, col_num + 13, i.get('energy_cost'))
            sheet.write(row_num + 1, col_num + 14, i.get('security'))
            sheet.write(row_num + 1, col_num + 15,
                        i.get('service_level_credit'))
            sheet.write(row_num + 1, col_num + 16,
                        i.get('total_cost'))
            sheet.write(row_num + 1, col_num + 17, i.get('jdo'))
            sheet.write(row_num + 1, col_num + 18, i.get('%'))
            row_num = row_num + 1
            sln_no = sln_no + 1

        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()
