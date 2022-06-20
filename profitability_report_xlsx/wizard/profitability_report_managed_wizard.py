from typing import io

from dateutil.relativedelta import relativedelta

from odoo import fields, models
from odoo.exceptions import UserError
from odoo.tools import date_utils, io, xlsxwriter
from odoo.tools.safe_eval import datetime, json
import calendar


class ProfitabilityReportManagedWizard(models.TransientModel):
    _name = "profitability.report.managed.wizard"

    def lease_anchor_tenant(self):
        return self.env['account.account'].search([('code', '=',
                                                    '411401'),
                                                   ('company_id',
                                                    '=',
                                                    self.env.company.id)])

    lease_anchor_tenant = fields.Many2many('account.account',
                                           'lease_anchor_tenant_rel',
                                           string='Lease Anchor tenant',
                                           default=lease_anchor_tenant)

    def generate_xlsx_report(self):
        # current_date = fields.Date.today()
        # from_date = ''
        # to_date = ''
        # first, last = calendar.monthrange(current_date.year, current_date.month)
        # if self.period == 'this_month':
        #     from_date = datetime.date(current_date.year, current_date.month, 1)
        #     to_date = datetime.date(current_date.year, current_date.month, last)
        # if self.period == 'this_quarter':
        #     current_quarter = (current_date.month - 1) // 3 + 1
        #     print(current_quarter)
        #     # date = current_date - relativedelta(months=2)
        #     from_date = datetime.date(current_date.year,
        #                               3 * current_quarter - 2, 1)
        #     to_date = datetime.date(current_date.year, 3 * current_quarter,
        #                             last)
        #     print(from_date, to_date, 'jjjjjjjjjj')
        # if self.period == 'this_financial_year':
        #     first, last = calendar.monthrange(current_date.year,
        #                                       12)
        #     from_date = datetime.date(current_date.year, 1, 1)
        #     to_date = datetime.date(current_date.year, 12, last)
        # if self.period == 'last_month':
        #     date = current_date - relativedelta(months=1)
        #     first, last = calendar.monthrange(date.year,
        #                                       date.month)
        #     from_date = datetime.date(date.year, date.month, 1)
        #     to_date = datetime.date(date.year, date.month, last)
        # if self.period == 'last_quarter':
        #     last_quarter = ((current_date.month - 1) // 3 + 1) - 1
        #     first, last = calendar.monthrange(current_date.year,
        #                                       3 * last_quarter)
        #     from_date = datetime.date(current_date.year,
        #                               3 * last_quarter - 2, 1)
        #     to_date = datetime.date(current_date.year, 3 * last_quarter,
        #                             last)
        # if self.period == 'last_financial_year':
        #     last_financial_year = current_date.year - 1
        #     first, last = calendar.monthrange(last_financial_year,
        #                                       12)
        #     from_date = datetime.date(last_financial_year, 1, 1)
        #     to_date = datetime.date(last_financial_year, 12, last)
        #     print(last_financial_year, from_date, to_date)
        # if self.from_date and self.to_date:
        #     if self.from_date > self.to_date:
        #         raise UserError("Start date should be less than end date")
        data = {
            'ids': self.ids,
            'model': self._name,
            'lease_anchor_tenant_ids': self.lease_anchor_tenant.ids,
            'lease_anchor_tenant_code': self.lease_anchor_tenant.code,
            # 'investment_revenue_ids': self.investment_revenue.ids,
            # 'investment_revenue_code': self.investment_revenue.code,
            # 'colocation_ids': self.colocation.ids,
            # 'colocation_code': self.colocation.code,
            # 'pass_through_energy_ids': self.pass_through_energy.ids,
            # 'pass_through_energy_code': self.pass_through_energy.code,
            # 'active_sharing_fees_ids': self.active_sharing_fees.ids,
            # 'active_sharing_fees_code': self.active_sharing_fees.code,
            # 'discount_ids': self.discount.ids,
            # 'discount_code': self.discount.code,
            # 'site_maintenance_code': self.site_maintenance.code,
            # 'site_maintenance_lim_code': self.site_maintenance_lim.code,
            # 'insurance_ids': self.insurance.ids,
            # 'insurance_code': self.insurance.code,
            # 'energy_cost_ids': self.energy_cost.ids,
            # 'energy_cost_code': self.energy_cost.code,
            # 'security_ids': self.security.ids,
            # 'security_code': self.security.code,
            # 'service_level_credit_ids': self.service_level_credit.ids,
            # 'service_level_credit_code': self.service_level_credit.code,
            # 'from': from_date if from_date else self.from_date,
            # 'to': to_date if to_date else self.to_date,
            'company_id': self.env.company.id
        }
        return {
            'type': 'ir.actions.report',
            'data': {'model': 'profitability.report.managed.wizard',
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
              '=', 'project_site'), ('company_id',
                                     '=',
                                     data['company_id'])])
        profitability_managed_report = []
        for i in project_site:
            prof_rep = {}
            prof_rep.update({
                'project': i.name,
            })
            # lease_anchor_tenant = self.env['account.move.line'].search(
            #     [('account_id', 'in', data['lease_anchor_tenant_ids']),
            #      ('project_site_id', '=', i.id),
            #      ('move_id.date', '<=', data['to']),
            #      ('move_id.date', '>=', data['from'])])
            # total = sum(lease_anchor_tenant.mapped('debit')) + sum(
            #     lease_anchor_tenant.mapped('credit'))
            # prof_rep.update({
            #     'lease_anchor_tenant': total,
            # })
            profitability_managed_report.append(prof_rep)
        print(profitability_managed_report)
        sheet = workbook.add_worksheet()

        head = workbook.add_format({'align': 'center',
                                    'bg_color': 'blue',
                                    'font_size': '13px'})
        head.set_font_color('white')

        # sheet.set_row(1, 70)
        #
        sheet.set_column('B3:C3', 20)

        account = workbook.add_format({'bg_color': 'blue'})
        sub_heading = workbook.add_format({'bg_color': 'blue'})

        sub_heading.set_font_color('white')

        sub_heading.set_align('vcenter')

        sheet.write('B3', 'Site Number', sub_heading)
        sheet.write('C3', 'Site code', sub_heading)

        sheet.merge_range('B2:T2', 'JANUARY', head)
        sheet.merge_range('D3:J3', 'Revenues', head)

        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()
