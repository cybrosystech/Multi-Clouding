import io
from email.policy import default

from dateutil.relativedelta import relativedelta

from odoo import fields, models
from odoo.exceptions import UserError
from odoo.tools import date_utils
import xlsxwriter
from odoo.tools.safe_eval import datetime, json
import calendar


class ProfitabilityReportManagedWizard(models.TransientModel):
    _name = "profitability.report.managed.wizard"

    def lease_anchor_tenant(self):
        profitability_managed = self.env['profitability.report.managed'].search(
            [])
        if profitability_managed:
            return profitability_managed.lease_anchor_tenant
        return self.env['account.account'].search([('code', '=',
                                                    '411401'),
                                                   ('company_id',
                                                    '=',
                                                    self.env.company.id)])

    def default_lease_colo_tenant(self):
        profitability_managed = self.env['profitability.report.managed'].search(
            [])
        if profitability_managed:
            return profitability_managed.lease_colo_tenant

    def default_additional_space_revenue(self):
        profitability_managed = self.env['profitability.report.managed'].search(
            [])
        if profitability_managed:
            return profitability_managed.additional_space_revenue

    def default_bts_revenue(self):
        profitability_managed = self.env['profitability.report.managed'].search(
            [])
        if profitability_managed:
            return profitability_managed.bts_revenue

    def default_active_sharing_fees(self):
        profitability_managed = self.env['profitability.report.managed'].search(
            [])
        if profitability_managed:
            return profitability_managed.active_sharing_fees

    def default_discount(self):
        profitability_managed = self.env['profitability.report.managed'].search(
            [])
        if profitability_managed:
            return profitability_managed.discount

    def default_rou_depreciation(self):
        profitability_managed = self.env['profitability.report.managed'].search(
            [])
        if profitability_managed:
            return profitability_managed.rou_depreciation

    def default_fa_depreciation(self):
        profitability_managed = self.env['profitability.report.managed'].search(
            [])
        if profitability_managed:
            return profitability_managed.fa_depreciation

    def default_lease_finance_cost(self):
        profitability_managed = self.env['profitability.report.managed'].search(
            [])
        if profitability_managed:
            return profitability_managed.lease_finance_cost

    def default_site_maintenance_managed(self):
        profitability_managed = self.env['profitability.report.managed'].search(
            [])
        if profitability_managed:
            return profitability_managed.site_maintenance_managed

    def default_site_maintenance_managed_lim(self):
        profitability_managed = self.env['profitability.report.managed'].search(
            [])
        if profitability_managed:
            return profitability_managed.site_maintenance_managed_lim

    def default_site_rent(self):
        profitability_managed = self.env['profitability.report.managed'].search(
            [])
        if profitability_managed:
            return profitability_managed.site_rent

    def default_security(self):
        profitability_managed = self.env['profitability.report.managed'].search(
            [])
        if profitability_managed:
            return profitability_managed.security
        return self.env['account.account'].search([('code', '=',
                                                    '422301'),
                                                   ('company_id',
                                                    '=',
                                                    self.env.company.id)])

    def default_analytic_account_group(self):
        group = self.env['account.analytic.group'].search(
            [('name', 'ilike', 'managed')])
        return group

    def default_service_level_credits(self):
        profitability_managed = self.env['profitability.report.managed'].search(
            [])
        if profitability_managed:
            return profitability_managed.service_level_credits

    lease_anchor_tenant = fields.Many2many('account.account',
                                           'lease_anchor_tenant_rel',
                                           string='Lease Anchor tenant',
                                           default=lease_anchor_tenant)

    lease_colo_tenant = fields.Many2many('account.account',
                                         'lease_colo_tenant_rel',
                                         string='Lease Colo tenant',
                                         default=default_lease_colo_tenant)

    additional_space_revenue = fields.Many2many('account.account',
                                                'additional_space_revenue_rel',
                                                string='Additional Space '
                                                       'Revenues',
                                                default=default_additional_space_revenue)

    bts_revenue = fields.Many2many('account.account',
                                   'bts_revenue_rel',
                                   string='BTS Revenue',
                                   default=default_bts_revenue)

    active_sharing_fees = fields.Many2many('account.account',
                                           'active_sharing_fees_rel',
                                           string='Active Sharing fees',
                                           default=default_active_sharing_fees)

    discount = fields.Many2many('account.account',
                                'discount_rel',
                                string='Discount',
                                default=default_discount)

    rou_depreciation = fields.Many2many('account.account',
                                        'rou_depreciation_rel',
                                        string='ROU Depreciation',
                                        default=default_rou_depreciation)

    fa_depreciation = fields.Many2many('account.account',
                                       'fa_depreciation_rel',
                                       string='FA Depreciation',
                                       default=default_fa_depreciation)

    lease_finance_cost = fields.Many2many('account.account',
                                          'lease_finance_cost_rel',
                                          string='Lease Finance Cost',
                                          default=default_lease_finance_cost)

    site_maintenance_managed = fields.Many2many('account.account',
                                                'site_maintenance_managed',
                                                default=default_site_maintenance_managed)

    site_maintenance_managed_lim = fields.Many2many('account.account',
                                                    'site_maintenance_managed_'
                                                    'lim',
                                                    default=default_site_maintenance_managed_lim)

    site_rent = fields.Many2many('account.account',
                                 'site_rent_rel',
                                 string='Site Rent',
                                 default=default_site_rent)

    security = fields.Many2many('account.account',
                                'security_rel',
                                string='Security', default=default_security)

    service_level_credits = fields.Many2many('account.account',
                                             'service_level_credits_rel',
                                             string='Service level Credits',
                                             default=default_service_level_credits)

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
    analytic_account_group = fields.Many2one('account.analytic.group',
                                             default=default_analytic_account_group)
    from_date = fields.Date('From')
    to_date = fields.Date('To')

    def generate_xlsx_report(self):
        current_date = fields.Date.today()
        from_date = ''
        to_date = ''
        Current_months = ''
        first, last = calendar.monthrange(current_date.year, current_date.month)
        if self.period == 'this_month':
            from_date = datetime.date(current_date.year, current_date.month, 1)
            to_date = datetime.date(current_date.year, current_date.month, last)
            Current_months = from_date.strftime("%B")
        if self.period == 'this_quarter':
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
        if self.period == 'this_financial_year':
            first, last = calendar.monthrange(current_date.year,
                                              12)
            from_date = datetime.date(current_date.year, 1, 1)
            to_date = datetime.date(current_date.year, 12, last)
            Current_months = from_date.year
        if self.period == 'last_month':
            date = current_date - relativedelta(months=1)
            first, last = calendar.monthrange(date.year,
                                              date.month)
            from_date = datetime.date(date.year, date.month, 1)
            to_date = datetime.date(date.year, date.month, last)
            Current_months = from_date.strftime("%B")
        if self.period == 'last_quarter':
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
        if self.period == 'last_financial_year':
            last_financial_year = current_date.year - 1
            first, last = calendar.monthrange(last_financial_year,
                                              12)
            from_date = datetime.date(last_financial_year, 1, 1)
            to_date = datetime.date(last_financial_year, 12, last)
            Current_months = from_date.year
        if self.from_date and self.to_date:
            if self.from_date > self.to_date:
                raise UserError("Start date should be less than end date")
        profitability_managed = self.env['profitability.report.managed'].search(
            [])
        if not profitability_managed:
            self.env['profitability.report.managed'].create({
                'lease_anchor_tenant': self.lease_anchor_tenant,
                'lease_colo_tenant': self.lease_colo_tenant,
                'additional_space_revenue': self.additional_space_revenue,
                'bts_revenue': self.bts_revenue,
                'active_sharing_fees': self.active_sharing_fees,
                'discount': self.discount,
                'rou_depreciation': self.rou_depreciation,
                'fa_depreciation': self.fa_depreciation,
                'lease_finance_cost': self.lease_finance_cost,
                'site_maintenance_managed': self.site_maintenance_managed,
                'site_maintenance_managed_lim': self.site_maintenance_managed_lim,
                'site_rent': self.site_rent,
                'security': self.security,
                'service_level_credits': self.service_level_credits
            })
        profitability_managed.update({
            'lease_anchor_tenant': self.lease_anchor_tenant,
            'lease_colo_tenant': self.lease_colo_tenant,
            'additional_space_revenue': self.additional_space_revenue,
            'bts_revenue': self.bts_revenue,
            'active_sharing_fees': self.active_sharing_fees,
            'discount': self.discount,
            'rou_depreciation': self.rou_depreciation,
            'fa_depreciation': self.fa_depreciation,
            'lease_finance_cost': self.lease_finance_cost,
            'site_maintenance_managed': self.site_maintenance_managed,
            'site_maintenance_managed_lim': self.site_maintenance_managed_lim,
            'site_rent': self.site_rent,
            'security': self.security,
            'service_level_credits': self.service_level_credits
        })
        data = {
            'ids': self.ids,
            'model': self._name,
            'lease_anchor_tenant_ids': self.lease_anchor_tenant.ids,
            'lease_anchor_tenant_code': self.lease_anchor_tenant.code,
            'lease_colo_tenant_ids': self.lease_colo_tenant.ids,
            'lease_colo_tenant_code': self.lease_colo_tenant.code,
            'additional_space_revenue_ids': self.additional_space_revenue.ids,
            'additional_space_revenue_code': self.additional_space_revenue.code,
            'bts_revenue_ids': self.bts_revenue.ids,
            'bts_revenue_code': self.bts_revenue.code,
            'active_sharing_fees_ids': self.active_sharing_fees.ids,
            'active_sharing_fees_code': self.active_sharing_fees.code,
            'discount_ids': self.discount.ids,
            'discount_code': self.discount.code,
            'rou_depreciation_ids': self.rou_depreciation.ids,
            'rou_depreciation_code': self.rou_depreciation.code,
            'fa_depreciation_ids': self.fa_depreciation.ids,
            'fa_depreciation_code': self.fa_depreciation.code,
            'lease_finance_cost_ids': self.lease_finance_cost.ids,
            'lease_finance_cost_code': self.lease_finance_cost.code,
            'site_maintenance_code': self.site_maintenance_managed.code,
            'site_maintenance_lim_code': self.site_maintenance_managed_lim.code,
            'site_rent_ids': self.site_rent.ids,
            'site_rent_code': self.site_rent.code,
            'security_ids': self.security.ids,
            'security_code': self.security.code,
            'service_level_credit_ids': self.service_level_credits.ids,
            'from': from_date if from_date else self.from_date,
            'to': to_date if to_date else self.to_date,
            'company_id': self.env.company.id,
            'analytic_account_group': self.analytic_account_group.id,
            'Current_months': Current_months
        }
        return {
            'type': 'ir.actions.report',
            'data': {'model': 'profitability.report.managed.wizard',
                     'options': json.dumps(data,
                                           default=date_utils.json_default),
                     'output_format': 'xlsx',
                     'report_name': 'Profitability Managed Report',
                     },
            'report_type': 'xlsx'
        }

    def get_xlsx_report(self, data, response):
        total_site = 0
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        account_ids = ''

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
        if data['site_maintenance_code'] and data['site_maintenance_lim_code']:
            query2 = '''
                    select id from account_account as account
                    where account.code BETWEEN \'''' + data[
                'site_maintenance_code'] + '\' and \'' + data[
                         'site_maintenance_lim_code'] + "\'"

            cr = self._cr
            cr.execute(query2)
            account_ids1 = cr.dictfetchall()
            account_ids = [dic['id'] for dic in account_ids1]
        profitability_managed_report = []
        for i in project_site:
            prof_rep = {}
            prof_rep.update({
                'project': i['name'],
            })
            projects = self.env['account.move.line'].search(
                [('project_site_id', '=', i['id']),
                 ('move_id.date', '<=', data['to']),
                 ('move_id.date', '>=', data['from'])])

            lease_anchor_tenant = projects.filtered(
                lambda x: x.account_id.id in data['lease_anchor_tenant_ids'])
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
                lambda x: x.account_id.id in data['active_sharing_fees_ids'])
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

            discount = projects.filtered(
                lambda x: x.account_id.id in data['discount_ids'])
            total = sum(discount.mapped('debit')) - sum(
                discount.mapped('credit'))
            prof_rep.update({
                'discount': total,
            })

            total_revenue = prof_rep['lease_anchor_tenant'] + prof_rep[
                'lease_colo_tenant'] + prof_rep['additional_space_revenue'] + \
                            prof_rep[
                                'bts_revenue'] + prof_rep[
                                'active_sharing_fees'] + prof_rep['discount']
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
                lambda x: x.account_id.id in account_ids if account_ids else None)
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
                lambda x: x.account_id.id in data['service_level_credit_ids'])
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

            profitability_managed_report.append(prof_rep)
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

        sheet.merge_range('B2:T2', data['Current_months'], main_head)
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
