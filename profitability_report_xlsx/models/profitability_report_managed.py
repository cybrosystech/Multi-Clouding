from odoo import fields, models
import json
import calendar
import io

from odoo.exceptions import UserError
from odoo.tools import date_utils
from odoo.tools.safe_eval import datetime
from datetime import timedelta
import xlsxwriter


class ProfitabilityReportManaged(models.Model):
    _name = "profitability.report.managed"

    lease_anchor_tenant = fields.Many2many('account.account',
                                           'lease_anchor_tenant_managed_rels')

    lease_colo_tenant = fields.Many2many('account.account',
                                         'lease_colo_tenant_managed_rels')

    additional_space_revenue = fields.Many2many('account.account',
                                                'additional_space_revenue_managed_rels')

    bts_revenue = fields.Many2many('account.account',
                                   'bts_revenue_managed_rels')

    active_sharing_fees = fields.Many2many('account.account',
                                           'active_sharing_fees_managed_rels')

    discount = fields.Many2many('account.account',
                                'discount_managed_rels')

    rou_depreciation = fields.Many2many('account.account',
                                        'rou_depreciation_managed_rela')

    fa_depreciation = fields.Many2many('account.account',
                                       'fa_depreciation_managed_rela')

    lease_finance_cost = fields.Many2many('account.account',
                                          'lease_finance_cost_managed_rel')

    site_maintenance_managed = fields.Many2many('account.account',
                                                'site_maintenances_managed')

    # site_maintenance_managed_lim = fields.Many2many('account.account',
    #                                                 'site_maintenance_managed_lims')

    site_rent = fields.Many2many('account.account',
                                 'site_rent_managed_rels')

    security = fields.Many2many('account.account',
                                'security_managed_rels')

    service_level_credits = fields.Many2many('account.account',
                                             'service_level_credits_managed_rels')
    json_report_values = fields.Char('Report Values')
    limits_pr = fields.Integer('Limit', default=0)
    period = fields.Selection(selection=([('this_quarter', 'This Quarter'),
                                          ('this_financial_year',
                                           'This Financial Year'),
                                          ('last_quarter', 'Last Quarter'),
                                          ('last_financial_year',
                                           'Last Financial Year'),
                                          ('custom', 'Custom')]),
                              string='Periods', required=True,
                              default='last_financial_year')
    company_id = fields.Many2one('res.company', 'Company',
                                 default=lambda self: self.env.company)
    end_limit = fields.Integer('end limit', default=0)
    from_date = fields.Date('From')
    to_date = fields.Date('To')
    current_filter = fields.Char('Selected Filter')

    def profitability_managed_report(self, limit):
        profitability_managed = self.env['profitability.report.managed'].search(
            [('company_id', '=', self.env.company.id)])
        current_date = fields.Date.today()
        profitability_managed_report = profitability_managed.json_report_values
        from_date = ''
        to_date = ''
        Current_months = ''
        if profitability_managed.period == 'this_financial_year':
            first, last = calendar.monthrange(current_date.year,
                                              12)
            from_date = datetime.date(current_date.year, 1, 1)
            to_date = datetime.date(current_date.year, 12, last)
            Current_months = from_date.year
        if profitability_managed.period == 'last_financial_year':
            last_financial_year = current_date.year - 1
            first, last = calendar.monthrange(last_financial_year,
                                              12)
            from_date = datetime.date(last_financial_year, 1, 1)
            to_date = datetime.date(last_financial_year, 12, last)
            Current_months = from_date.year
        if profitability_managed.period == 'this_quarter':
            current_quarter = (current_date.month - 1) // 3 + 1
            first, last = calendar.monthrange(current_date.year,
                                              3 * current_quarter)
            from_date = datetime.date(current_date.year,
                                      3 * current_quarter - 2, 1)
            to_date = datetime.date(current_date.year, 3 * current_quarter,
                                    last)
            from_month = from_date.strftime("%B")
            to_month = to_date.strftime("%B")
            Current_months = from_month + ' - ' + to_month
        if profitability_managed.period == 'last_quarter':
            last_quarter = ((current_date.month - 1) // 3 + 1) - 1
            first, last = calendar.monthrange(current_date.year,
                                              3 * last_quarter)
            from_date = datetime.date(current_date.year,
                                      3 * last_quarter - 2, 1)
            to_date = datetime.date(current_date.year, 3 * last_quarter,
                                    last)
            from_month = from_date.strftime("%B")
            to_month = to_date.strftime("%B")
            Current_months = from_month + ' - ' + to_month
        if profitability_managed.from_date and profitability_managed.to_date:
            if profitability_managed.from_date > profitability_managed.to_date:
                raise UserError("Start date should be less than end date")
        group = self.env['account.analytic.group'].search(
            [('name', 'ilike', 'managed'),
             ('company_id', '=', profitability_managed.company_id.id)])
        data = {
            'ids': self.ids,
            'model': self._name,
            'lease_anchor_tenant_ids': profitability_managed.lease_anchor_tenant.ids,
            'lease_colo_tenant_ids': profitability_managed.lease_colo_tenant.ids,
            'additional_space_revenue_ids': profitability_managed.additional_space_revenue.ids,
            'bts_revenue_ids': profitability_managed.bts_revenue.ids,
            'active_sharing_fees_ids': profitability_managed.active_sharing_fees.ids,
            'discount_ids': profitability_managed.discount.ids,
            'rou_depreciation_ids': profitability_managed.rou_depreciation.ids,
            'fa_depreciation_ids': profitability_managed.fa_depreciation.ids,
            'lease_finance_cost_ids': profitability_managed.lease_finance_cost.ids,
            'site_maintenance_ids': profitability_managed.site_maintenance_managed.ids,
            'site_rent_ids': profitability_managed.site_rent.ids,
            'security_ids': profitability_managed.security.ids,
            'service_level_credit_ids': profitability_managed.service_level_credits.ids,
            'from': from_date if from_date else profitability_managed.from_date,
            'to': to_date if to_date else profitability_managed.to_date,
            'company_id': profitability_managed.company_id.id,
            'analytic_account_group': group.id,
            'Current_months': Current_months,
            'limit': limit
        }
        report_values = profitability_managed.get_profitability_managed(data,
                                                                        profitability_managed_report,
                                                                        profitability_managed)
        profitability_managed.json_report_values = json.dumps(report_values)
        profitability_managed.current_filter = Current_months

    def get_profitability_managed(self, data, profitability_managed_report,
                                  profitability_managed):
        projects = ''
        if profitability_managed_report:
            profitability_managed_report_load = json.loads(profitability_managed_report)
            query = '''
                                    select id,name from account_analytic_account as analatyc_account
                                    WHERE analatyc_account.analytic_account_type = 'project_site'
                                    and analatyc_account.company_id = ''' + str(
                data['company_id']) + '''
                                    and analatyc_account.group_id = ''' + str(
                data['analytic_account_group'])

            cr = self._cr
            cr.execute(query)
            project_site = cr.dictfetchall()
            end_limit = profitability_managed.limits_pr + int(data['limit'])
            profitability_managed.end_limit = end_limit
            for i in project_site[
                     profitability_managed.limits_pr: end_limit]:
                prof_rep = {}
                prof_rep.update({
                    'project': i['name'],
                })
                projects = self.env['account.move.line'].search(
                    [('project_site_id', '=', i['id']),
                     ('move_id.date', '<=', data['to']),
                     ('move_id.date', '>=', data['from']),
                     ('parent_state', '=', 'posted'),
                     ('company_id', '=', profitability_managed.company_id.id)])
                lease_anchor_tenant = projects.filtered(
                    lambda x: x.account_id.id in data[
                        'lease_anchor_tenant_ids'])
                total = sum(lease_anchor_tenant.mapped('debit')) - sum(
                    lease_anchor_tenant.mapped('credit'))
                prof_rep.update({
                    'lease_anchor_tenant': total,
                })

                lease_colo_tenant = projects.filtered(
                    lambda x: x.account_id.id in data['lease_colo_tenant_ids'])
                total = sum(lease_colo_tenant.mapped('debit')) - sum(
                    lease_colo_tenant.mapped('credit'))
                prof_rep.update({
                    'lease_colo_tenant': total,
                })

                additional_space_revenue = projects.filtered(
                    lambda x: x.account_id.id in data[
                        'additional_space_revenue_ids'])
                total = sum(additional_space_revenue.mapped('debit')) - sum(
                    additional_space_revenue.mapped('credit'))
                prof_rep.update({
                    'additional_space_revenue': total,
                })

                bts_revenue = projects.filtered(
                    lambda x: x.account_id.id in data['bts_revenue_ids'])
                total = sum(bts_revenue.mapped('debit')) - sum(
                    bts_revenue.mapped('credit'))
                prof_rep.update({
                    'bts_revenue': total,
                })

                active_sharing_fees = projects.filtered(
                    lambda x: x.account_id.id in data[
                        'active_sharing_fees_ids'])
                total = sum(active_sharing_fees.mapped('debit')) - sum(
                    active_sharing_fees.mapped('credit'))
                prof_rep.update({
                    'active_sharing_fees': total,
                })

                discount = projects.filtered(
                    lambda x: x.account_id.id in data['discount_ids'])
                total = sum(discount.mapped('debit')) - sum(
                    discount.mapped('credit'))
                prof_rep.update({
                    'discount': total,
                })

                total_revenue = prof_rep['lease_anchor_tenant'] + prof_rep[
                    'lease_colo_tenant'] + prof_rep[
                                    'additional_space_revenue'] + \
                                prof_rep[
                                    'bts_revenue'] + prof_rep[
                                    'active_sharing_fees'] + prof_rep[
                                    'discount']
                prof_rep.update({
                    'total_revenue': total_revenue,
                })

                rou_depreciation = projects.filtered(
                    lambda x: x.account_id.id in data['rou_depreciation_ids'])
                total = sum(rou_depreciation.mapped('debit')) - sum(
                    rou_depreciation.mapped('credit'))
                prof_rep.update({
                    'rou_depreciation': total,
                })

                fa_depreciation = projects.filtered(
                    lambda x: x.account_id.id in data['fa_depreciation_ids'])
                total = sum(fa_depreciation.mapped('debit')) - sum(
                    fa_depreciation.mapped('credit'))
                prof_rep.update({
                    'fa_depreciation': total,
                })

                lease_finance_cost = projects.filtered(
                    lambda x: x.account_id.id in data['lease_finance_cost_ids'])
                total = sum(lease_finance_cost.mapped('debit')) - sum(
                    lease_finance_cost.mapped('credit'))
                prof_rep.update({
                    'lease_finance_cost': total,
                })

                site_maintenance = projects.filtered(
                    lambda x: x.account_id.id in data['site_maintenance_ids'])
                total = sum(site_maintenance.mapped('debit')) - sum(
                    site_maintenance.mapped('credit'))
                prof_rep.update({
                    'site_maintenance': total,
                })

                site_rent = projects.filtered(
                    lambda x: x.account_id.id in data['site_rent_ids'])
                total = sum(site_rent.mapped('debit')) - sum(
                    site_rent.mapped('credit'))
                prof_rep.update({
                    'site_rent': total,
                })

                security = projects.filtered(
                    lambda x: x.account_id.id in data['security_ids'])
                total = sum(security.mapped('debit')) - sum(
                    security.mapped('credit'))
                prof_rep.update({
                    'security': total,
                })

                service_level_credit = projects.filtered(
                    lambda x: x.account_id.id in data[
                        'service_level_credit_ids'])
                total = sum(service_level_credit.mapped('debit')) - sum(
                    service_level_credit.mapped('credit'))
                prof_rep.update({
                    'service_level_credit': total,
                })

                total_cost = prof_rep['rou_depreciation'] + prof_rep[
                    'fa_depreciation'] + \
                             prof_rep['lease_finance_cost'] + prof_rep[
                                 'site_maintenance'] + \
                             prof_rep['site_rent'] + prof_rep['security'] + \
                             prof_rep['service_level_credit']
                jdo = total_revenue - total_cost
                total_percent = ''
                if total_revenue != 0:
                    total_percent = (abs(jdo) / total_revenue) * 100
                prof_rep.update({
                    'total_cost': total_cost,
                    'jdo': abs(jdo),
                    '%': total_percent if total_percent else 0
                })
                profitability_managed_report_load.append(prof_rep)
            profitability_managed.limits_pr = end_limit
            if end_limit <= len(project_site):
                date = fields.Datetime.now()
                schedule = self.env.ref(
                    'profitability_report_xlsx.action_profitability_managed_cron_update')
                schedule.update({
                    'nextcall': date + timedelta(seconds=10),
                })
            return profitability_managed_report_load
        else:
            dummy_prof_list = []
            query = '''
                                            select id,name from account_analytic_account as analatyc_account 
                                            WHERE analatyc_account.analytic_account_type = 'project_site'
                                            and analatyc_account.company_id = ''' + str(
                data['company_id']) + ''' 
                                            and analatyc_account.group_id = ''' + str(
                data['analytic_account_group'])

            cr = self._cr
            cr.execute(query)
            project_site = cr.dictfetchall()
            end_limit = profitability_managed.limits_pr + int(data['limit'])
            profitability_managed.end_limit = end_limit
            for i in project_site[profitability_managed.limits_pr: end_limit]:
                prof_rep = {}
                prof_rep.update({
                    'project': i['name'],
                })
                projects = self.env['account.move.line'].search(
                    [('project_site_id', '=', i['id']),
                     ('move_id.date', '<=', data['to']),
                     ('move_id.date', '>=', data['from']),
                     ('parent_state', '=', 'posted'),
                     ('company_id', '=', profitability_managed.company_id.id)])
                lease_anchor_tenant = projects.filtered(
                    lambda x: x.account_id.id in data[
                        'lease_anchor_tenant_ids'])
                total = sum(lease_anchor_tenant.mapped('debit')) - sum(
                    lease_anchor_tenant.mapped('credit'))
                prof_rep.update({
                    'lease_anchor_tenant': total,
                })

                lease_colo_tenant = projects.filtered(
                    lambda x: x.account_id.id in data['lease_colo_tenant_ids'])
                total = sum(lease_colo_tenant.mapped('debit')) - sum(
                    lease_colo_tenant.mapped('credit'))
                prof_rep.update({
                    'lease_colo_tenant': total,
                })

                additional_space_revenue = projects.filtered(
                    lambda x: x.account_id.id in data[
                        'additional_space_revenue_ids'])
                total = sum(additional_space_revenue.mapped('debit')) - sum(
                    additional_space_revenue.mapped('credit'))
                prof_rep.update({
                    'additional_space_revenue': total,
                })

                bts_revenue = projects.filtered(
                    lambda x: x.account_id.id in data['bts_revenue_ids'])
                total = sum(bts_revenue.mapped('debit')) - sum(
                    bts_revenue.mapped('credit'))
                prof_rep.update({
                    'bts_revenue': total,
                })

                active_sharing_fees = projects.filtered(
                    lambda x: x.account_id.id in data[
                        'active_sharing_fees_ids'])
                total = sum(active_sharing_fees.mapped('debit')) - sum(
                    active_sharing_fees.mapped('credit'))
                prof_rep.update({
                    'active_sharing_fees': total,
                })

                discount = projects.filtered(
                    lambda x: x.account_id.id in data['discount_ids'])
                total = sum(discount.mapped('debit')) - sum(
                    discount.mapped('credit'))
                prof_rep.update({
                    'discount': total,
                })

                total_revenue = prof_rep['lease_anchor_tenant'] + prof_rep[
                    'lease_colo_tenant'] + prof_rep[
                                    'additional_space_revenue'] + \
                                prof_rep[
                                    'bts_revenue'] + prof_rep[
                                    'active_sharing_fees'] + prof_rep[
                                    'discount']
                prof_rep.update({
                    'total_revenue': total_revenue,
                })

                rou_depreciation = projects.filtered(
                    lambda x: x.account_id.id in data['rou_depreciation_ids'])
                total = sum(rou_depreciation.mapped('debit')) - sum(
                    rou_depreciation.mapped('credit'))
                prof_rep.update({
                    'rou_depreciation': total,
                })

                fa_depreciation = projects.filtered(
                    lambda x: x.account_id.id in data['fa_depreciation_ids'])
                total = sum(fa_depreciation.mapped('debit')) - sum(
                    fa_depreciation.mapped('credit'))
                prof_rep.update({
                    'fa_depreciation': total,
                })

                lease_finance_cost = projects.filtered(
                    lambda x: x.account_id.id in data['lease_finance_cost_ids'])
                total = sum(lease_finance_cost.mapped('debit')) - sum(
                    lease_finance_cost.mapped('credit'))
                prof_rep.update({
                    'lease_finance_cost': total,
                })

                site_maintenance = projects.filtered(
                    lambda x: x.account_id.id in data['site_maintenance_ids'])
                total = sum(site_maintenance.mapped('debit')) - sum(
                    site_maintenance.mapped('credit'))
                prof_rep.update({
                    'site_maintenance': total,
                })

                site_rent = projects.filtered(
                    lambda x: x.account_id.id in data['site_rent_ids'])
                total = sum(site_rent.mapped('debit')) - sum(
                    site_rent.mapped('credit'))
                prof_rep.update({
                    'site_rent': total,
                })

                security = projects.filtered(
                    lambda x: x.account_id.id in data['security_ids'])
                total = sum(security.mapped('debit')) - sum(
                    security.mapped('credit'))
                prof_rep.update({
                    'security': total,
                })

                service_level_credit = projects.filtered(
                    lambda x: x.account_id.id in data[
                        'service_level_credit_ids'])
                total = sum(service_level_credit.mapped('debit')) - sum(
                    service_level_credit.mapped('credit'))
                prof_rep.update({
                    'service_level_credit': total,
                })

                total_cost = prof_rep['rou_depreciation'] + prof_rep[
                    'fa_depreciation'] + \
                             prof_rep['lease_finance_cost'] + prof_rep[
                                 'site_maintenance'] + \
                             prof_rep['site_rent'] + prof_rep['security'] + \
                             prof_rep['service_level_credit']
                jdo = total_revenue - total_cost
                total_percent = ''
                if total_revenue != 0:
                    total_percent = (abs(jdo) / total_revenue) * 100
                prof_rep.update({
                    'total_cost': total_cost,
                    'jdo': abs(jdo),
                    '%': total_percent if total_percent else 0
                })
                dummy_prof_list.append(prof_rep)
            profitability_managed.limits_pr = end_limit
            if end_limit <= len(project_site):
                date = fields.Datetime.now()
                schedule = self.env.ref(
                    'profitability_report_xlsx.action_profitability_managed_cron_update')
                schedule.update({
                    'nextcall': date + timedelta(seconds=10),
                })
            return dummy_prof_list

    def profitability_managed_cron_update(self):
        date = fields.Datetime.now()
        schedule = self.env.ref(
            'profitability_report_xlsx.action_profitability_managed_cron')
        schedule.update({
            'nextcall': date + timedelta(seconds=10)
        })

    def action_get_report(self):
        return {
            'type': 'ir.actions.report',
            'data': {'model': 'profitability.report.managed',
                     'options': json.dumps(self.json_report_values,
                                           default=date_utils.json_default),
                     'output_format': 'xlsx',
                     'report_name': 'Profitability Managed Report',
                     },
            'report_type': 'xlsx'
        }

    def get_xlsx(self, data, response):
        profitability_managed_report = json.loads(data)
        profitability_managed_object = self.env[
            'profitability.report.managed'].search([])
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})

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

        sheet.write('B4', '', sub_heading1)
        sheet.write('C4', '', sub_heading1)
        sheet.write('D4', 'Lease Anchor tenant', sub_heading1)
        sheet.write('E4', 'Lease Colo tenant', sub_heading1)
        sheet.write('F4', 'Additional Space Revenues', sub_heading1)
        sheet.write('G4', 'BTS Revenue', sub_heading1)
        sheet.write('H4', 'Active Sharing fees', sub_heading1)
        sheet.write('I4', 'Discount', sub_heading1)
        sheet.write('J4', 'Total Revenues', sub_heading1)
        sheet.write('K4', 'ROU Depreciation', sub_heading1)
        sheet.write('L4', 'FA Depreciation', sub_heading1)
        sheet.write('M4', 'Lease Finance Cost', sub_heading1)
        sheet.write('N4', 'Site Maintenance', sub_heading1)
        sheet.write('O4', 'Site Rent', sub_heading1)
        sheet.write('P4', 'Security', sub_heading1)
        sheet.write('Q4', 'Service level Credits', sub_heading1)
        sheet.write('R4', 'Total Costs', sub_heading1)
        sheet.write('S4', 'JOD', sub_heading1)
        sheet.write('T4', '%', sub_heading1)

        sheet.merge_range('B2:T2', profitability_managed_object.current_filter,
                          main_head)
        sheet.merge_range('D3:J3', 'Revenues', head)
        sheet.merge_range('K3:R3', 'Costs', head)
        sheet.merge_range('S3:T3', 'Gross Profit', head)

        row_num = 3
        col_num = 1
        sln_no = 1

        for i in profitability_managed_report:
            sheet.write(row_num + 1, col_num, sln_no)
            sheet.write(row_num + 1, col_num + 1, i.get('project'))
            sheet.write(row_num + 1, col_num + 2, i.get('lease_anchor_tenant'))
            sheet.write(row_num + 1, col_num + 3, i.get('lease_colo_tenant'))
            sheet.write(row_num + 1, col_num + 4,
                        i.get('additional_space_revenue'))
            sheet.write(row_num + 1, col_num + 5, i.get('bts_revenue'))
            sheet.write(row_num + 1, col_num + 6, i.get('active_sharing_fees'))
            sheet.write(row_num + 1, col_num + 7, i.get('discount'))
            sheet.write(row_num + 1, col_num + 8, i.get('total_revenue'))
            sheet.write(row_num + 1, col_num + 9, i.get('rou_depreciation'))
            sheet.write(row_num + 1, col_num + 10, i.get('fa_depreciation'))
            sheet.write(row_num + 1, col_num + 11, i.get('lease_finance_cost'))
            sheet.write(row_num + 1, col_num + 12, i.get('site_maintenance'))
            sheet.write(row_num + 1, col_num + 13, i.get('site_rent'))
            sheet.write(row_num + 1, col_num + 14, i.get('security'))
            sheet.write(row_num + 1, col_num + 15,
                        i.get('service_level_credit'))
            sheet.write(row_num + 1, col_num + 16, i.get('total_cost'))
            sheet.write(row_num + 1, col_num + 17, i.get('jdo'))
            sheet.write(row_num + 1, col_num + 18, i.get('%'))

            row_num = row_num + 1
            sln_no = sln_no + 1

        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()

    def schedule_managed_cron(self):
        date = fields.Datetime.now()
        schedule_action = self.env.ref('profitability_report_xlsx.action_profitability_managed_cron')
        schedule_action.update({
            'nextcall': date + timedelta(minutes=1)
        })
        self.update({
            'limits_pr': 0,
            'end_limit': 0,
            'json_report_values': ''
        })

