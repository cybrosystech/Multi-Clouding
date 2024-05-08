from odoo import models, fields
from odoo.exceptions import UserError
from odoo.tools.safe_eval import datetime, json
from odoo.tools import date_utils, get_lang
import calendar
from datetime import timedelta
from odoo.tools import date_utils
import io
import xlsxwriter


class ProfitabilityReportOwned(models.Model):
    _name = 'profitability.report.owned'

    service_revenue = fields.Many2many('account.account',
                                       'service_revenue_owned_rel',
                                       string='Service Revenue')
    investment_revenue = fields.Many2many('account.account',
                                          'investment_revenue_owned_rel',
                                          string='Investment Revenue')
    colocation = fields.Many2many('account.account', 'colocation_owned_rel',
                                  string='Colocation')
    pass_through_energy = fields.Many2many('account.account',
                                           'pass_through_owned_energy',
                                           string='Pass Through Energy')
    active_sharing_fees = fields.Many2many('account.account',
                                           'active_sharing_owned_fees',
                                           string='Active Sharing Fees')
    discount = fields.Many2many('account.account', 'disc_owned',
                                string='Discount')
    site_maintenance = fields.Many2many('account.account',
                                        'site_owned_maintenance')
    insurance = fields.Many2many('account.account', 'insurance_owned_',
                                 string="Insurance")
    energy_cost = fields.Many2many('account.account', 'energy_owned_cost',
                                   string='Energy Cost')
    security = fields.Many2many('account.account', 'security_owned',
                                string='Security')
    service_level_credit = fields.Many2many('account.account',
                                            'service_level_owned_credit',
                                            string='Service Level Credit')
    rou_depreciation = fields.Many2many('account.account',
                                        'rou_depreciation_owned_rels',
                                        string='ROU Depreciation')
    fa_depreciation = fields.Many2many('account.account',
                                       'fa_depreciation_owned_rel')
    fa_depreciation_lim = fields.Many2many('account.account',
                                           'fa_depreciation_lim_owned_rel',
                                           )
    lease_finance_cost = fields.Many2many('account.account',
                                          'lease_finance_cost_owned_rels',
                                          string='Leases Finance Cost')

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
    from_date = fields.Date('From')
    to_date = fields.Date('To')
    end_limit = fields.Integer('end limit', default=0)
    current_filter = fields.Char('Selected Filter')
    cron_id = fields.Many2one('ir.cron', String="Scheduled Action",
                              domain=[('name', 'ilike',
                                       'Profitability Owned Cron :')])
    _sql_constraints = [
        ('cron_uniq', 'unique (cron_id)',
         """This scheduled action is already selected on another!."""),
    ]

    def profitability_owned_report_general(self, limit):
        cron_id = self.env.ref(
            'profitability_report_xlsx.action_profitability_owned_cron_general').id
        profitability_owned = self.env['profitability.report.owned'].search(
            [('cron_id', '=', cron_id)])
        current_date = fields.Date.today()
        profitability_owned_report = profitability_owned.json_report_values
        from_date = ''
        to_date = ''
        Current_months = ''
        if profitability_owned.period == 'this_financial_year':
            first, last = calendar.monthrange(current_date.year,
                                              12)
            from_date = datetime.date(current_date.year, 1, 1)
            to_date = datetime.date(current_date.year, 12, last)
            Current_months = from_date.year
        if profitability_owned.period == 'last_financial_year':
            last_financial_year = current_date.year - 1
            first, last = calendar.monthrange(last_financial_year,
                                              12)
            from_date = datetime.date(last_financial_year, 1, 1)
            to_date = datetime.date(last_financial_year, 12, last)
            Current_months = from_date.year
        if profitability_owned.period == 'this_quarter':
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
        if profitability_owned.period == 'last_quarter':
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
        if profitability_owned.from_date and profitability_owned.to_date:
            if profitability_owned.from_date > profitability_owned.to_date:
                raise UserError("Start date should be less than end date")
        # group = self.env['account.analytic.group'].search(
        #     [('name', 'ilike', 'owned'),
        #      ('company_id', '=', profitability_owned.company_id.id)])
        # group = self.env['account.analytic.plan'].search(
        #     [('name', 'ilike', 'owned')])
        group_id = 'owned'

        data = {
            'ids': self.ids,
            'model': self._name,
            'service_revenue_ids': profitability_owned.service_revenue.ids,
            'investment_revenue_ids': profitability_owned.investment_revenue.ids,
            'colocation_ids': profitability_owned.colocation.ids,
            'pass_through_energy_ids': profitability_owned.pass_through_energy.ids,
            'active_sharing_fees_ids': profitability_owned.active_sharing_fees.ids,
            'discount_ids': profitability_owned.discount.ids,
            'site_maintenance_ids': profitability_owned.site_maintenance.ids,
            'insurance_ids': profitability_owned.insurance.ids,
            'energy_cost_ids': profitability_owned.energy_cost.ids,
            'security_ids': profitability_owned.security.ids,
            'service_level_credit_ids': profitability_owned.service_level_credit.ids,
            'rou_depreciation_ids': profitability_owned.rou_depreciation.ids,
            'fa_depreciation_code': profitability_owned.fa_depreciation.code,
            'fa_depreciation_lim_code': profitability_owned.fa_depreciation_lim.code,
            'lease_finance_cost_ids': profitability_owned.lease_finance_cost.ids,
            'from': from_date if from_date else profitability_owned.from_date,
            'to': to_date if to_date else profitability_owned.to_date,
            'company_id': profitability_owned.company_id.id,
            # 'analatyc_account_group': group.id,
            'group_id':group_id,
            'Current_months': Current_months,
            'limit': limit
        }
        report_values = profitability_owned.get_profitability_owned(data,
                                                                    profitability_owned_report,
                                                                    profitability_owned)
        profitability_owned.json_report_values = json.dumps(report_values)
        profitability_owned.current_filter = Current_months

    def profitability_owned_report(self, limit):
        cron_id = self.env.ref(
            'profitability_report_xlsx.action_profitability_owned_cron').id
        profitability_owned = self.env['profitability.report.owned'].search(
            [('cron_id', '=', cron_id)])
        current_date = fields.Date.today()
        profitability_owned_report = profitability_owned.json_report_values
        from_date = ''
        to_date = ''
        Current_months = ''
        if profitability_owned.period == 'this_financial_year':
            first, last = calendar.monthrange(current_date.year,
                                              12)
            from_date = datetime.date(current_date.year, 1, 1)
            to_date = datetime.date(current_date.year, 12, last)
            Current_months = from_date.year
        if profitability_owned.period == 'last_financial_year':
            last_financial_year = current_date.year - 1
            first, last = calendar.monthrange(last_financial_year,
                                              12)
            from_date = datetime.date(last_financial_year, 1, 1)
            to_date = datetime.date(last_financial_year, 12, last)
            Current_months = from_date.year
        if profitability_owned.period == 'this_quarter':
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
        if profitability_owned.period == 'last_quarter':
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
        if profitability_owned.from_date and profitability_owned.to_date:
            if profitability_owned.from_date > profitability_owned.to_date:
                raise UserError("Start date should be less than end date")
        # group = self.env['account.analytic.group'].search(
        #     [('name', 'ilike', 'owned'),
        #      ('company_id', '=', profitability_owned.company_id.id)])
        # group = self.env['account.analytic.plan'].search(
        #     [('name', 'ilike', 'owned')])
        group_id = 'owned'

        data = {
            'ids': self.ids,
            'model': self._name,
            'service_revenue_ids': profitability_owned.service_revenue.ids,
            'investment_revenue_ids': profitability_owned.investment_revenue.ids,
            'colocation_ids': profitability_owned.colocation.ids,
            'pass_through_energy_ids': profitability_owned.pass_through_energy.ids,
            'active_sharing_fees_ids': profitability_owned.active_sharing_fees.ids,
            'discount_ids': profitability_owned.discount.ids,
            'site_maintenance_ids': profitability_owned.site_maintenance.ids,
            'insurance_ids': profitability_owned.insurance.ids,
            'energy_cost_ids': profitability_owned.energy_cost.ids,
            'security_ids': profitability_owned.security.ids,
            'service_level_credit_ids': profitability_owned.service_level_credit.ids,
            'rou_depreciation_ids': profitability_owned.rou_depreciation.ids,
            'fa_depreciation_code': profitability_owned.fa_depreciation.code,
            'fa_depreciation_lim_code': profitability_owned.fa_depreciation_lim.code,
            'lease_finance_cost_ids': profitability_owned.lease_finance_cost.ids,
            'from': from_date if from_date else profitability_owned.from_date,
            'to': to_date if to_date else profitability_owned.to_date,
            'company_id': profitability_owned.company_id.id,
            # 'analatyc_account_group': group.id,
            'group_id':group_id,
            'Current_months': Current_months,
            'limit': limit
        }
        report_values = profitability_owned.get_profitability_owned(data,
                                                                    profitability_owned_report,
                                                                    profitability_owned)
        profitability_owned.json_report_values = json.dumps(report_values)
        profitability_owned.current_filter = Current_months

    def profitability_owned_report_baghdad(self, limit):
        cron_id = self.env.ref(
            'profitability_report_xlsx.action_profitability_owned_cron_baghdad').id
        profitability_owned = self.env['profitability.report.owned'].search(
            [('cron_id', '=', cron_id)])
        current_date = fields.Date.today()
        profitability_owned_report = profitability_owned.json_report_values
        from_date = ''
        to_date = ''
        Current_months = ''
        if profitability_owned.period == 'this_financial_year':
            first, last = calendar.monthrange(current_date.year,
                                              12)
            from_date = datetime.date(current_date.year, 1, 1)
            to_date = datetime.date(current_date.year, 12, last)
            Current_months = from_date.year
        if profitability_owned.period == 'last_financial_year':
            last_financial_year = current_date.year - 1
            first, last = calendar.monthrange(last_financial_year,
                                              12)
            from_date = datetime.date(last_financial_year, 1, 1)
            to_date = datetime.date(last_financial_year, 12, last)
            Current_months = from_date.year
        if profitability_owned.period == 'this_quarter':
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
        if profitability_owned.period == 'last_quarter':
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
        if profitability_owned.from_date and profitability_owned.to_date:
            if profitability_owned.from_date > profitability_owned.to_date:
                raise UserError("Start date should be less than end date")
        # group = self.env['account.analytic.plan'].search(
        #     [('name', 'ilike', 'owned')])
        group_id = 'owned'

        data = {
            'ids': self.ids,
            'model': self._name,
            'service_revenue_ids': profitability_owned.service_revenue.ids,
            'investment_revenue_ids': profitability_owned.investment_revenue.ids,
            'colocation_ids': profitability_owned.colocation.ids,
            'pass_through_energy_ids': profitability_owned.pass_through_energy.ids,
            'active_sharing_fees_ids': profitability_owned.active_sharing_fees.ids,
            'discount_ids': profitability_owned.discount.ids,
            'site_maintenance_ids': profitability_owned.site_maintenance.ids,
            'insurance_ids': profitability_owned.insurance.ids,
            'energy_cost_ids': profitability_owned.energy_cost.ids,
            'security_ids': profitability_owned.security.ids,
            'service_level_credit_ids': profitability_owned.service_level_credit.ids,
            'rou_depreciation_ids': profitability_owned.rou_depreciation.ids,
            'fa_depreciation_code': profitability_owned.fa_depreciation.code,
            'fa_depreciation_lim_code': profitability_owned.fa_depreciation_lim.code,
            'lease_finance_cost_ids': profitability_owned.lease_finance_cost.ids,
            'from': from_date if from_date else profitability_owned.from_date,
            'to': to_date if to_date else profitability_owned.to_date,
            'company_id': profitability_owned.company_id.id,
            # 'analatyc_account_group': group.id,
            'group_id':group_id,
            'Current_months': Current_months,
            'limit': limit
        }
        report_values = profitability_owned.get_profitability_owned(data,
                                                                    profitability_owned_report,
                                                                    profitability_owned)
        profitability_owned.json_report_values = json.dumps(report_values)
        profitability_owned.current_filter = Current_months

    def profitability_owned_report_erbill(self, limit):
        cron_id = self.env.ref(
            'profitability_report_xlsx.action_profitability_owned_cron_erbill').id
        profitability_owned = self.env['profitability.report.owned'].search(
            [('cron_id', '=', cron_id)])
        current_date = fields.Date.today()
        profitability_owned_report = profitability_owned.json_report_values
        from_date = ''
        to_date = ''
        Current_months = ''
        if profitability_owned.period == 'this_financial_year':
            first, last = calendar.monthrange(current_date.year,
                                              12)
            from_date = datetime.date(current_date.year, 1, 1)
            to_date = datetime.date(current_date.year, 12, last)
            Current_months = from_date.year
        if profitability_owned.period == 'last_financial_year':
            last_financial_year = current_date.year - 1
            first, last = calendar.monthrange(last_financial_year,
                                              12)
            from_date = datetime.date(last_financial_year, 1, 1)
            to_date = datetime.date(last_financial_year, 12, last)
            Current_months = from_date.year
        if profitability_owned.period == 'this_quarter':
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
        if profitability_owned.period == 'last_quarter':
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
        if profitability_owned.from_date and profitability_owned.to_date:
            if profitability_owned.from_date > profitability_owned.to_date:
                raise UserError("Start date should be less than end date")
        # group = self.env['account.analytic.plan'].search(
        #     [('name', 'ilike', 'owned')])
        group_id = 'owned'

        data = {
            'ids': self.ids,
            'model': self._name,
            'service_revenue_ids': profitability_owned.service_revenue.ids,
            'investment_revenue_ids': profitability_owned.investment_revenue.ids,
            'colocation_ids': profitability_owned.colocation.ids,
            'pass_through_energy_ids': profitability_owned.pass_through_energy.ids,
            'active_sharing_fees_ids': profitability_owned.active_sharing_fees.ids,
            'discount_ids': profitability_owned.discount.ids,
            'site_maintenance_ids': profitability_owned.site_maintenance.ids,
            'insurance_ids': profitability_owned.insurance.ids,
            'energy_cost_ids': profitability_owned.energy_cost.ids,
            'security_ids': profitability_owned.security.ids,
            'service_level_credit_ids': profitability_owned.service_level_credit.ids,
            'rou_depreciation_ids': profitability_owned.rou_depreciation.ids,
            'fa_depreciation_code': profitability_owned.fa_depreciation.code,
            'fa_depreciation_lim_code': profitability_owned.fa_depreciation_lim.code,
            'lease_finance_cost_ids': profitability_owned.lease_finance_cost.ids,
            'from': from_date if from_date else profitability_owned.from_date,
            'to': to_date if to_date else profitability_owned.to_date,
            'company_id': profitability_owned.company_id.id,
            # 'analatyc_account_group': group.id,
            'group_id': group_id,
            'Current_months': Current_months,
            'limit': limit
        }
        report_values = profitability_owned.get_profitability_owned(data,
                                                                    profitability_owned_report,
                                                                    profitability_owned)
        profitability_owned.json_report_values = json.dumps(report_values)
        profitability_owned.current_filter = Current_months

    def get_profitability_owned(self, data, profitability_owned_report,
                                profitability_owned):
        lang = self.env.user.lang or get_lang(self.env).code

        if profitability_owned_report:
            account_fa_depreciation_ids = []
            profitability_owned_report_load = json.loads(
                profitability_owned_report)
            name = f"COALESCE(analatyc_account.name->>'{lang}', analatyc_account.name->>'en_US')" if \
                self.pool[
                    'account.analytic.account'].name.translate else 'analatyc_account.name'
            query = f'''
                                        select id,{name} as name from account_analytic_account as analatyc_account 
                                        WHERE analatyc_account.analytic_account_type = 'project_site'
                                        and analatyc_account.company_id = ''' + str(
                data['company_id']) + ''' 
                                        and analatyc_account.group_id = ''' + str(
                data['group_id'])

            cr = self._cr
            cr.execute(query)
            project_site = cr.dictfetchall()
            if data['fa_depreciation_code'] and data[
                'fa_depreciation_lim_code']:
                query3 = '''
                                            select id from account_account as account
                                            where account.code BETWEEN \'''' + \
                         data[
                             'fa_depreciation_code'] + '\' and \'' + data[
                             'fa_depreciation_lim_code'] + "\'"

                cr = self._cr
                cr.execute(query3)
                account_ids_depreciation = cr.dictfetchall()
                account_fa_depreciation_ids = [dic['id'] for dic in
                                               account_ids_depreciation]
            end_limit = profitability_owned.limits_pr + int(data['limit'])
            profitability_owned.end_limit = end_limit
            for i in project_site[profitability_owned.limits_pr: end_limit]:
                prof_rep = {}
                prof_rep.update({
                    'project': i['name'],
                    'company_id': profitability_owned.company_id.id,
                })
                projects = self.env['account.move.line'].search(
                    [('project_site_id', '=', i['id']),
                     ('move_id.date', '<=', data['to']),
                     ('move_id.date', '>=', data['from']),
                     ('parent_state', '=', 'posted'),
                     ('company_id', '=', profitability_owned.company_id.id)])

                service_revenue = projects.filtered(
                    lambda x: x.account_id.id in data[
                        'service_revenue_ids'])
                total = sum(service_revenue.mapped('debit')) - sum(
                    service_revenue.mapped('credit'))
                prof_rep.update({
                    'service_revenue': total,
                })

                colocation = projects.filtered(
                    lambda x: x.account_id.id in data['colocation_ids'])
                total = sum(colocation.mapped('debit')) - sum(
                    colocation.mapped('credit'))
                prof_rep.update({
                    'colocation': total,
                })

                investment_revenue = projects.filtered(
                    lambda x: x.account_id.id in data[
                        'investment_revenue_ids'])
                total = sum(investment_revenue.mapped('debit')) - sum(
                    investment_revenue.mapped('credit'))
                prof_rep.update({
                    'investment_revenue': total,
                })

                pass_through_energy = projects.filtered(
                    lambda x: x.account_id.id in data[
                        'pass_through_energy_ids'])
                total = sum(pass_through_energy.mapped('debit')) - sum(
                    pass_through_energy.mapped('credit'))
                prof_rep.update({
                    'pass_through_energy': total,
                })

                discount = projects.filtered(
                    lambda x: x.account_id.id in data['discount_ids'])
                total = sum(discount.mapped('debit')) - sum(
                    discount.mapped('credit'))
                prof_rep.update({
                    'discount': total,
                })

                active_sharing_fees = projects.filtered(
                    lambda x: x.account_id.id in data[
                        'active_sharing_fees_ids'])
                total = sum(active_sharing_fees.mapped('debit')) - sum(
                    active_sharing_fees.mapped('credit'))
                prof_rep.update({
                    'active_sharing_fees': total,
                })

                total_revenue = prof_rep['service_revenue'] + prof_rep[
                    'investment_revenue'] + prof_rep['colocation'] + \
                                prof_rep[
                                    'pass_through_energy'] + prof_rep[
                                    'active_sharing_fees'] + prof_rep[
                                    'discount']
                prof_rep.update({
                    'total_revenue': total_revenue,
                })

                site_maintenance = projects.filtered(
                    lambda x: x.account_id.id in data[
                        'site_maintenance_ids'])
                total = sum(site_maintenance.mapped('debit')) - sum(
                    site_maintenance.mapped('credit'))
                prof_rep.update({
                    'site_maintenance': total,
                })

                insurance = projects.filtered(
                    lambda x: x.account_id.id in data['insurance_ids'])
                total = sum(insurance.mapped('debit')) - sum(
                    insurance.mapped('credit'))
                prof_rep.update({
                    'insurance': total,
                })

                energy_cost = projects.filtered(
                    lambda x: x.account_id.id in data['energy_cost_ids'])
                total = sum(energy_cost.mapped('debit')) - sum(
                    energy_cost.mapped('credit'))
                prof_rep.update({
                    'energy_cost': total,
                })

                service_level_credit = projects.filtered(
                    lambda x: x.account_id.id in data[
                        'service_level_credit_ids'])
                total = sum(service_level_credit.mapped('debit')) - sum(
                    service_level_credit.mapped('credit'))
                prof_rep.update({
                    'service_level_credit': total,
                })

                security = projects.filtered(
                    lambda x: x.account_id.id in data['security_ids'])
                total = sum(security.mapped('debit')) - sum(
                    security.mapped('credit'))
                prof_rep.update({
                    'security': total,
                })

                total_cost = prof_rep['site_maintenance'] + prof_rep[
                    'insurance'] + \
                             prof_rep['energy_cost'] + prof_rep[
                                 'security'] + \
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

                rou_depreciation = projects.filtered(
                    lambda x: x.account_id.id in data[
                        'rou_depreciation_ids'])
                total = sum(rou_depreciation.mapped('debit')) - sum(
                    rou_depreciation.mapped('credit'))
                prof_rep.update({
                    'rou_depreciation': total,
                })

                fa_depreciation = projects.filtered(
                    lambda
                        x: x.account_id.id in account_fa_depreciation_ids if
                    account_fa_depreciation_ids else None)
                total = sum(fa_depreciation.mapped('debit')) - sum(
                    fa_depreciation.mapped('credit'))
                prof_rep.update({
                    'fa_depreciation': total,
                })

                lease_finance_cost = projects.filtered(
                    lambda x: x.account_id.id in data[
                        'lease_finance_cost_ids'])
                total = sum(lease_finance_cost.mapped('debit')) - sum(
                    lease_finance_cost.mapped('credit'))
                prof_rep.update({
                    'lease_finance_cost': total,
                })
                profitability_owned_report_load.append(prof_rep)
            profitability_owned.limits_pr = end_limit
            if end_limit <= len(project_site):
                date = fields.Datetime.now()
                xml_id = profitability_owned.cron_id.get_xml_id()
                if xml_id.get(
                        profitability_owned.cron_id.id) == 'profitability_report_xlsx.action_profitability_owned_cron':
                    schedule = self.env.ref(
                        'profitability_report_xlsx.action_profitability_owned_cron_update')
                    schedule.update({
                        'nextcall': date + timedelta(seconds=10),
                    })
                elif xml_id.get(
                        profitability_owned.cron_id.id) == 'profitability_report_xlsx.action_profitability_owned_cron_baghdad':
                    schedule = self.env.ref(
                        'profitability_report_xlsx.action_profitability_owned_cron_update_baghdad')
                    schedule.update({
                        'nextcall': date + timedelta(seconds=10),
                    })
                elif xml_id.get(
                        profitability_owned.cron_id.id) == 'profitability_report_xlsx.action_profitability_owned_cron_erbill':
                    schedule = self.env.ref(
                        'profitability_report_xlsx.action_profitability_owned_cron_update_erbill')
                    schedule.update({
                        'nextcall': date + timedelta(seconds=10),
                    })
                elif xml_id.get(
                        profitability_owned.cron_id.id) == 'profitability_report_xlsx.action_profitability_owned_cron_general':
                    schedule = self.env.ref(
                        'profitability_report_xlsx.action_profitability_owned_cron_update_general')
                    schedule.update({
                        'nextcall': date + timedelta(seconds=10),
                    })
                else:
                    pass
            return profitability_owned_report_load
        else:
            account_fa_depreciation_ids = []
            dummy_prof_list = []
            name = f"COALESCE(analatyc_account.name->>'{lang}', analatyc_account.name->>'en_US')" if \
                self.pool[
                    'account.analytic.account'].name.translate else 'analatyc_account.name'
            query = f'''
                            select id,{name} as name from account_analytic_account as analatyc_account 
                            WHERE analatyc_account.analytic_account_type = 'project_site'
                            and analatyc_account.company_id = ''' + str(
                data['company_id']) + ''' 
                            and analatyc_account.group_id = ''' + str(
                data['group_id'])

            cr = self._cr
            cr.execute(query)
            project_site = cr.dictfetchall()
            if data['fa_depreciation_code'] and data[
                'fa_depreciation_lim_code']:
                query3 = '''
                                select id from account_account as account
                                where account.code BETWEEN \'''' + data[
                    'fa_depreciation_code'] + '\' and \'' + data[
                             'fa_depreciation_lim_code'] + "\'"

                cr = self._cr
                cr.execute(query3)
                account_ids_depreciation = cr.dictfetchall()
                account_fa_depreciation_ids = [dic['id'] for dic in
                                               account_ids_depreciation]
            else:
                account_fa_depreciation_ids = []
            end_limit = profitability_owned.limits_pr + int(data['limit'])
            profitability_owned.end_limit = end_limit
            for i in project_site[
                     profitability_owned.limits_pr: int(data['limit'])]:
                prof_rep = {}
                prof_rep.update({
                    'project': i['name'],
                    'company_id': profitability_owned.company_id.id,

                })
                projects = self.env['account.move.line'].search(
                    [('project_site_id', '=', i['id']),
                     ('move_id.date', '<=', data['to']),
                     ('move_id.date', '>=', data['from']),
                     ('parent_state', '=', 'posted'),
                     ('company_id', '=', profitability_owned.company_id.id)])

                service_revenue = projects.filtered(
                    lambda x: x.account_id.id in data[
                        'service_revenue_ids'])
                total = sum(service_revenue.mapped('debit')) - sum(
                    service_revenue.mapped('credit'))
                prof_rep.update({
                    'service_revenue': total,
                })

                colocation = projects.filtered(
                    lambda x: x.account_id.id in data['colocation_ids'])
                total = sum(colocation.mapped('debit')) - sum(
                    colocation.mapped('credit'))
                prof_rep.update({
                    'colocation': total,
                })

                investment_revenue = projects.filtered(
                    lambda x: x.account_id.id in data[
                        'investment_revenue_ids'])
                total = sum(investment_revenue.mapped('debit')) - sum(
                    investment_revenue.mapped('credit'))
                prof_rep.update({
                    'investment_revenue': total,
                })

                pass_through_energy = projects.filtered(
                    lambda x: x.account_id.id in data[
                        'pass_through_energy_ids'])
                total = sum(pass_through_energy.mapped('debit')) - sum(
                    pass_through_energy.mapped('credit'))
                prof_rep.update({
                    'pass_through_energy': total,
                })

                discount = projects.filtered(
                    lambda x: x.account_id.id in data['discount_ids'])
                total = sum(discount.mapped('debit')) - sum(
                    discount.mapped('credit'))
                prof_rep.update({
                    'discount': total,
                })

                active_sharing_fees = projects.filtered(
                    lambda x: x.account_id.id in data[
                        'active_sharing_fees_ids'])
                total = sum(active_sharing_fees.mapped('debit')) - sum(
                    active_sharing_fees.mapped('credit'))
                prof_rep.update({
                    'active_sharing_fees': total,
                })

                total_revenue = prof_rep['service_revenue'] + prof_rep[
                    'investment_revenue'] + prof_rep['colocation'] + \
                                prof_rep[
                                    'pass_through_energy'] + prof_rep[
                                    'active_sharing_fees'] + prof_rep[
                                    'discount']
                prof_rep.update({
                    'total_revenue': total_revenue,
                })

                site_maintenance = projects.filtered(
                    lambda x: x.account_id.id in data[
                        'site_maintenance_ids'])
                total = sum(site_maintenance.mapped('debit')) - sum(
                    site_maintenance.mapped('credit'))
                prof_rep.update({
                    'site_maintenance': total,
                })

                insurance = projects.filtered(
                    lambda x: x.account_id.id in data['insurance_ids'])
                total = sum(insurance.mapped('debit')) - sum(
                    insurance.mapped('credit'))
                prof_rep.update({
                    'insurance': total,
                })

                energy_cost = projects.filtered(
                    lambda x: x.account_id.id in data['energy_cost_ids'])
                total = sum(energy_cost.mapped('debit')) - sum(
                    energy_cost.mapped('credit'))
                prof_rep.update({
                    'energy_cost': total,
                })

                service_level_credit = projects.filtered(
                    lambda x: x.account_id.id in data[
                        'service_level_credit_ids'])
                total = sum(service_level_credit.mapped('debit')) - sum(
                    service_level_credit.mapped('credit'))
                prof_rep.update({
                    'service_level_credit': total,
                })

                security = projects.filtered(
                    lambda x: x.account_id.id in data['security_ids'])
                total = sum(security.mapped('debit')) - sum(
                    security.mapped('credit'))
                prof_rep.update({
                    'security': total,
                })

                total_cost = prof_rep['site_maintenance'] + prof_rep[
                    'insurance'] + \
                             prof_rep['energy_cost'] + prof_rep[
                                 'security'] + \
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

                rou_depreciation = projects.filtered(
                    lambda x: x.account_id.id in data[
                        'rou_depreciation_ids'])
                total = sum(rou_depreciation.mapped('debit')) - sum(
                    rou_depreciation.mapped('credit'))
                prof_rep.update({
                    'rou_depreciation': total,
                })

                fa_depreciation = projects.filtered(
                    lambda
                        x: x.account_id.id in account_fa_depreciation_ids if
                    account_fa_depreciation_ids else None)
                total = sum(fa_depreciation.mapped('debit')) - sum(
                    fa_depreciation.mapped('credit'))
                prof_rep.update({
                    'fa_depreciation': total,
                })

                lease_finance_cost = projects.filtered(
                    lambda x: x.account_id.id in data[
                        'lease_finance_cost_ids'])
                total = sum(lease_finance_cost.mapped('debit')) - sum(
                    lease_finance_cost.mapped('credit'))
                prof_rep.update({
                    'lease_finance_cost': total,
                })
                dummy_prof_list.append(prof_rep)
            profitability_owned.limits_pr = end_limit
            if end_limit <= len(project_site):
                date = fields.Datetime.now()
                xml_id = profitability_owned.cron_id.get_xml_id()
                if xml_id.get(
                        profitability_owned.cron_id.id) == 'profitability_report_xlsx.action_profitability_owned_cron':
                    schedule = self.env.ref(
                        'profitability_report_xlsx.action_profitability_owned_cron_update')
                    schedule.update({
                        'nextcall': date + timedelta(seconds=10),
                    })
                elif xml_id.get(
                        profitability_owned.cron_id.id) == 'profitability_report_xlsx.action_profitability_owned_cron_baghdad':
                    schedule = self.env.ref(
                        'profitability_report_xlsx.action_profitability_owned_cron_update_baghdad')
                    schedule.update({
                        'nextcall': date + timedelta(seconds=10),
                    })
                elif xml_id.get(
                        profitability_owned.cron_id.id) == 'profitability_report_xlsx.action_profitability_owned_cron_erbill':
                    schedule = self.env.ref(
                        'profitability_report_xlsx.action_profitability_owned_cron_update_erbill')
                    schedule.update({
                        'nextcall': date + timedelta(seconds=10),
                    })
                elif xml_id.get(
                        profitability_owned.cron_id.id) == 'profitability_report_xlsx.action_profitability_owned_cron_general':
                    schedule = self.env.ref(
                        'profitability_report_xlsx.action_profitability_owned_cron_update_general')
                    schedule.update({
                        'nextcall': date + timedelta(seconds=10),
                    })
                else:
                    pass
            return dummy_prof_list

    def action_get_report(self):
        return {
            'type': 'ir.actions.report',
            'data': {'model': 'profitability.report.owned',
                     'options': json.dumps(self.json_report_values,
                                           default=date_utils.json_default),
                     'output_format': 'xlsx',
                     'report_name': 'Profitability Owned Report',
                     },
            'report_type': 'xlsx'
        }

    def get_xlsx(self, data, response):
        profitability_owned_report = json.loads(data)
        profitability_object = self.env['profitability.report.owned'].search(
            [('company_id', '=', profitability_owned_report[0]['company_id'])])
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
        sheet.merge_range('B2:S2', profitability_object.current_filter,
                          main_head)
        sheet.merge_range('U2:W2', '', main_head)
        sheet.merge_range('D3:J3', 'Revenues', head)
        sheet.merge_range('K3:Q3', 'Costs', head)
        sheet.merge_range('R3:S3', 'Gross Profit', head)
        sheet.merge_range('U3:W3', '', head)

        row_num = 3
        col_num = 1
        sln_no = 1

        for i in profitability_owned_report:
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

    def profitability_owned_cron_update_general(self):
        date = fields.Datetime.now()
        schedule = self.env.ref(
            'profitability_report_xlsx.action_profitability_owned_cron_general')
        schedule.update({
            'nextcall': date + timedelta(seconds=10)
        })

    def profitability_owned_cron_update(self):
        date = fields.Datetime.now()
        schedule = self.env.ref(
            'profitability_report_xlsx.action_profitability_owned_cron')
        schedule.update({
            'nextcall': date + timedelta(seconds=10)
        })

    def profitability_owned_cron_update_baghdad(self):
        date = fields.Datetime.now()
        schedule = self.env.ref(
            'profitability_report_xlsx.action_profitability_owned_cron_baghdad')
        schedule.update({
            'nextcall': date + timedelta(seconds=10)
        })

    def profitability_owned_cron_update_erbill(self):
        date = fields.Datetime.now()
        schedule = self.env.ref(
            'profitability_report_xlsx.action_profitability_owned_cron_erbill')
        schedule.update({
            'nextcall': date + timedelta(seconds=10)
        })

    def schedule_owned_cron(self):
        date = fields.Datetime.now()
        schedule_action = self.cron_id
        schedule_action.update({
            'nextcall': date + timedelta(seconds=1)
        })
        self.update({
            'limits_pr': 0,
            'end_limit': 0,
            'json_report_values': ''
        })
