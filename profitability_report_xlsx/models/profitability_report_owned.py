import calendar
import io
import xlsxwriter
from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.tools.safe_eval import datetime, json
from odoo.tools import get_lang
from odoo.tools import date_utils
from collections import defaultdict


class ProfitabilityReportOwned(models.Model):
    _name = 'profitability.report.owned'



    service_revenue = fields.Many2many('account.account',
                                       'service_revenue_owned_rel',
                                       string='Service Revenue')
    site_rent_ids = fields.Many2many('account.account',
                                       'site_rent_owned_rel',
                                       string='Site Rent')
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
    fa_depreciation_from = fields.Many2one('account.account',
                                                string="FA Depreciation",
                                                help="From code for FA Depreciation")
    fa_depreciation_to = fields.Many2one('account.account', string="To",
                                              help="To code for FA Depreciation")

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
    current_filter = fields.Char('Selected Filter')

    @api.constrains('fa_depreciation_from', 'fa_depreciation_to')
    def onsave_fa_depreciation_period(self):
        if self.fa_depreciation_from and self.fa_depreciation_to:
            if self.fa_depreciation_from.code > self.fa_depreciation_to.code:
                raise UserError("FA Depreciation From Account Code should be "
                                "less than To Account Code")

    @api.onchange('period')
    def onchange_period(self):
        current_date = fields.Date.today()
        from_date = ''
        to_date = ''
        Current_months = ''
        if self.period == 'this_financial_year':
            first, last = calendar.monthrange(current_date.year,
                                              12)
            from_date = datetime.date(current_date.year, 1, 1)
            to_date = datetime.date(current_date.year, 12, last)
            Current_months = from_date.year
        if self.period == 'last_financial_year':
            last_financial_year = current_date.year - 1
            first, last = calendar.monthrange(last_financial_year,
                                              12)
            from_date = datetime.date(last_financial_year, 1, 1)
            to_date = datetime.date(last_financial_year, 12, last)
            Current_months = from_date.year
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

        self.from_date = False
        self.to_date = False
        self.from_date = from_date
        self.to_date = to_date
        self.current_filter = Current_months

    @api.constrains('from_date', 'to_date')
    def onsave_period(self):
        if self.from_date and self.to_date:
            if self.from_date > self.to_date:
                raise UserError("Start date should be less than end date")

    def action_get_report(self):
        data = {
            'service_revenue_ids': self.service_revenue.ids,
            'site_rent_ids': self.site_rent_ids.ids,
            'investment_revenue_ids': self.investment_revenue.ids,
            'colocation_ids': self.colocation.ids,
            'pass_through_energy_ids': self.pass_through_energy.ids,
            'active_sharing_fees_ids': self.active_sharing_fees.ids,
            'discount_ids': self.discount.ids,
            'site_maintenance_ids': self.site_maintenance.ids,
            'insurance_ids': self.insurance.ids,
            'energy_cost_ids': self.energy_cost.ids,
            'security_ids': self.security.ids,
            'service_level_credit_ids': self.service_level_credit.ids,
            'rou_depreciation_ids': self.rou_depreciation.ids,
            'fa_depreciation_from': self.fa_depreciation_from.code_num,
            'fa_depreciation_to': self.fa_depreciation_to.code_num,
            'lease_finance_cost_ids': self.lease_finance_cost.ids,
             'from': self.from_date if self.from_date else fields.Date.today(),
            'to': self.to_date if self.to_date else fields.Date.today(),
            'company_id': self.company_id.id,
            'Current_months': self.current_filter,
        }
        return {
            'type': 'ir.actions.report',
            'data': {'model': 'profitability.report.owned',
                     'options': json.dumps(data,
                                           default=date_utils.json_default),
                     'output_format': 'xlsx',
                     'report_name': 'Profitability Owned Report',
                     },
            'report_type': 'xlsx'
        }

    def get_xlsx(self, data, response):
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
        sheet.write('T4', 'ROU Depreciation', sub_heading1)
        sheet.write('U4', 'FA Depreciation', sub_heading1)
        sheet.write('V4', 'Leases Finance Cost', sub_heading1)
        sheet.merge_range('B2:S2', self.current_filter,
                          main_head)
        sheet.merge_range('T2:V2', '', main_head)
        sheet.merge_range('D3:J3', 'Revenues', head)
        sheet.merge_range('K3:Q3', 'Costs', head)
        sheet.merge_range('R3:S3', 'Gross Profit', head)

        row_num = 3
        sln_no = 1

        lang = self.env.user.lang or get_lang(self.env).code
        project_site_name = f"COALESCE(ac.name->>'{lang}', ac.name->>'en_US')" if \
            self.pool[
                'account.analytic.account'].name.translate else 'ac.name'
        account_name = f"COALESCE(act.name->>'{lang}', act.name->>'en_US')" if \
            self.pool[
                'account.analytic.account'].name.translate else 'act.name'

        service_revenue_ids = data["service_revenue_ids"]
        if len(service_revenue_ids) == 1:
            service_revenue_ids = f"({service_revenue_ids[0]})"  # Single-element tuple for SQL
        else:
            service_revenue_ids = str(tuple(service_revenue_ids))

        site_rent_ids = data["site_rent_ids"]
        if len(site_rent_ids) == 1:
            site_rent_ids = f"({site_rent_ids[0]})"  # Single-element tuple for SQL
        else:
            site_rent_ids = str(tuple(site_rent_ids))

        investment_revenue_ids = data["investment_revenue_ids"]
        if len(investment_revenue_ids) == 1:
            investment_revenue_ids = f"({investment_revenue_ids[0]})"  # Single-element tuple for SQL
        else:
            investment_revenue_ids = str(tuple(investment_revenue_ids))

        colocation_ids = data["colocation_ids"]
        if len(colocation_ids) == 1:
            colocation_ids = f"({colocation_ids[0]})"  # Single-element tuple for SQL
        else:
            colocation_ids = str(
                tuple(colocation_ids))

        pass_through_energy_ids = data["pass_through_energy_ids"]
        if len(pass_through_energy_ids) == 1:
            pass_through_energy_ids = f"({pass_through_energy_ids[0]})"  # Single-element tuple for SQL
        else:
            pass_through_energy_ids = str(tuple(pass_through_energy_ids))

        active_sharing_fees_ids = data["active_sharing_fees_ids"]
        if len(active_sharing_fees_ids) == 1:
            active_sharing_fees_ids = f"({active_sharing_fees_ids[0]})"  # Single-element tuple for SQL
        else:
            active_sharing_fees_ids = str(tuple(active_sharing_fees_ids))

        discount_ids = data["discount_ids"]
        if len(discount_ids) == 1:
            discount_ids = f"({discount_ids[0]})"  # Single-element tuple for SQL
        else:
            discount_ids = str(tuple(discount_ids))

        site_maintenance_ids = data["site_maintenance_ids"]
        if len(site_maintenance_ids) == 1:
            site_maintenance_ids = f"({site_maintenance_ids[0]})"  # Single-element tuple for SQL
        else:
            site_maintenance_ids = str(tuple(site_maintenance_ids))

        insurance_ids = data["insurance_ids"]
        if len(insurance_ids) == 1:
            insurance_ids = f"({insurance_ids[0]})"  # Single-element tuple for SQL
        else:
            insurance_ids = str(tuple(insurance_ids))

        energy_cost_ids = data["energy_cost_ids"]
        if len(energy_cost_ids) == 1:
            energy_cost_ids = f"({energy_cost_ids[0]})"  # Single-element tuple for SQL
        else:
            energy_cost_ids = str(tuple(energy_cost_ids))

        security_ids = data["security_ids"]
        if len(security_ids) == 1:
            security_ids = f"({security_ids[0]})"  # Single-element tuple for SQL
        else:
            security_ids = str(tuple(security_ids))

        service_level_credit_ids = data["service_level_credit_ids"]
        if len(service_level_credit_ids) == 1:
            service_level_credit_ids = f"({service_level_credit_ids[0]})"  # Single-element tuple for SQL
        else:
            service_level_credit_ids = str(tuple(service_level_credit_ids))

        rou_depreciation_ids = data["rou_depreciation_ids"]
        if len(rou_depreciation_ids) == 1:
            rou_depreciation_ids = f"({rou_depreciation_ids[0]})"  # Single-element tuple for SQL
        else:
            rou_depreciation_ids = str(tuple(rou_depreciation_ids))

        fa_depreciation_from = data["fa_depreciation_from"]
        fa_depreciation_to = data["fa_depreciation_to"]

        lease_finance_cost_ids = data["lease_finance_cost_ids"]
        if len(lease_finance_cost_ids) == 1:
            lease_finance_cost_ids = f"({lease_finance_cost_ids[0]})"  # Single-element tuple for SQL
        else:
            lease_finance_cost_ids = str(tuple(lease_finance_cost_ids))

        from_date = data["from"]
        to_date = data["to"]
        company_id_str = str(data["company_id"])
        combined_query = ""

        if len(data["service_revenue_ids"]) > 0:
            service_revenue_query = f'''SELECT 
                                'service_revenue'                                       AS key,
                                SUM(COALESCE(l.debit, 0)) - SUM(COALESCE(l.credit, 0)) AS balance,{account_name} as account_name,{project_site_name} as project_site_name,ac.id as project_site_id from account_move_line l 
                                LEFT JOIN account_analytic_account ac ON l.project_site_id = ac.id 
                                LEFT JOIN account_account act ON l.account_id=act.id
                                where ac.analytic_account_type='project_site' and ac.group_id='owned' and
                                l.date>='{str(from_date)}' and l.date<='{str(to_date)}' and l.company_id= ({company_id_str}) and l.parent_state='posted' and l.account_id in {service_revenue_ids}
                                group by l.company_id,ac.id, act.id'''
            combined_query += f"{service_revenue_query} UNION ALL "
        if len(data["investment_revenue_ids"]) > 0:
            investment_revenue_query = f'''SELECT 
                                        'investment_revenue'                                       AS key,
                                        SUM(COALESCE(l.debit, 0)) - SUM(COALESCE(l.credit, 0)) AS balance,{account_name} as account_name,{project_site_name} as project_site_name,ac.id as project_site_id from account_move_line l 
                                        LEFT JOIN account_analytic_account ac ON l.project_site_id = ac.id 
                                        LEFT JOIN account_account act ON l.account_id=act.id
                                        where ac.analytic_account_type='project_site' and ac.group_id='owned' and
                                        l.date>='{str(from_date)}' and l.date<='{str(to_date)}' and l.company_id= ({company_id_str}) and l.parent_state='posted' and l.account_id in {investment_revenue_ids}
                                        group by l.company_id,ac.id, act.id'''
            combined_query += f"{investment_revenue_query} UNION ALL "
        if len(data["colocation_ids"]) > 0:
            colocation_query = f'''SELECT 
                                    'colocation'                                       AS key,
                                    SUM(COALESCE(l.debit, 0)) - SUM(COALESCE(l.credit, 0)) AS balance,{account_name} as account_name,{project_site_name} as project_site_name,ac.id as project_site_id from account_move_line l 
                                    LEFT JOIN account_analytic_account ac ON l.project_site_id = ac.id 
                                    LEFT JOIN account_account act ON l.account_id=act.id
                                    where ac.analytic_account_type='project_site' and ac.group_id='owned' and
                                    l.date>='{str(from_date)}' and l.date<='{str(to_date)}' and l.company_id= ({company_id_str}) and l.parent_state='posted' and l.account_id in {colocation_ids}
                                    group by l.company_id,ac.id, act.id'''
            combined_query += f"{colocation_query} UNION ALL "

        if len(data["pass_through_energy_ids"]) > 0:
            pass_through_energy_query = f'''SELECT 
                                'pass_through_energy'                                       AS key,
                                SUM(COALESCE(l.debit, 0)) - SUM(COALESCE(l.credit, 0)) AS balance,{account_name} as account_name,{project_site_name} as project_site_name,ac.id as project_site_id from account_move_line l 
                                LEFT JOIN account_analytic_account ac ON l.project_site_id = ac.id 
                                LEFT JOIN account_account act ON l.account_id=act.id
                                where ac.analytic_account_type='project_site' and ac.group_id='owned' and
                                l.date>='{str(from_date)}' and l.date<='{str(to_date)}' and l.company_id=({company_id_str}) and l.parent_state='posted' and l.account_id in {pass_through_energy_ids}
                                group by l.company_id,ac.id, act.id'''
            combined_query += f"{pass_through_energy_query} UNION ALL "

        if len(data["active_sharing_fees_ids"]) > 0:
            active_sharing_fees_query = f'''SELECT 
                                            'active_sharing_fees'                                       AS key,
                                            SUM(COALESCE(l.debit, 0)) - SUM(COALESCE(l.credit, 0)) AS balance,{account_name} as account_name,{project_site_name} as project_site_name,ac.id as project_site_id from account_move_line l 
                                            LEFT JOIN account_analytic_account ac ON l.project_site_id = ac.id 
                                            LEFT JOIN account_account act ON l.account_id=act.id
                                            where ac.analytic_account_type='project_site' and ac.group_id='owned' and
                                            l.date>='{str(from_date)}' and l.date<='{str(to_date)}' and l.company_id= ({company_id_str}) and l.parent_state='posted' and l.account_id in {active_sharing_fees_ids}
                                            group by l.company_id,ac.id, act.id'''
            combined_query += f"{active_sharing_fees_query} UNION ALL "
        if len(data["discount_ids"]) > 0:
            discount_query = f'''SELECT 
                                    'discount'                                       AS key,
                                    SUM(COALESCE(l.debit, 0)) - SUM(COALESCE(l.credit, 0)) AS balance,{account_name} as account_name,{project_site_name} as project_site_name,ac.id as project_site_id from account_move_line l 
                                    LEFT JOIN account_analytic_account ac ON l.project_site_id = ac.id 
                                    LEFT JOIN account_account act ON l.account_id=act.id
                                    where ac.analytic_account_type='project_site' and ac.group_id='owned' and
                                    l.date>='{str(from_date)}' and l.date<='{str(to_date)}' and l.company_id= ({company_id_str}) and l.parent_state='posted' and l.account_id in {discount_ids}
                                    group by l.company_id,ac.id, act.id'''
            combined_query += f"{discount_query} UNION ALL "
        if len(data["rou_depreciation_ids"]) > 0:
            rou_depreciation_query = f'''SELECT 
                                            'rou_depreciation'                                       AS key,
                                            SUM(COALESCE(l.debit, 0)) - SUM(COALESCE(l.credit, 0)) AS balance,{account_name} as account_name,{project_site_name} as project_site_name,ac.id as project_site_id from account_move_line l 
                                            LEFT JOIN account_analytic_account ac ON l.project_site_id = ac.id 
                                            LEFT JOIN account_account act ON l.account_id=act.id
                                            where ac.analytic_account_type='project_site' and ac.group_id='owned' and
                                            l.date>='{str(from_date)}' and l.date<='{str(to_date)}' and l.company_id= ({company_id_str}) and l.parent_state='posted' and l.account_id in {rou_depreciation_ids}
                                            group by l.company_id,ac.id, act.id'''
            combined_query += f"{rou_depreciation_query} UNION ALL "
        if fa_depreciation_from >0 and fa_depreciation_to>0:
            fa_depreciation_query = f'''SELECT 
                                        'fa_depreciation'                                       AS key,
                                        SUM(COALESCE(l.debit, 0)) - SUM(COALESCE(l.credit, 0)) AS balance,{account_name} as account_name,{project_site_name} as project_site_name,ac.id as project_site_id from account_move_line l 
                                        LEFT JOIN account_analytic_account ac ON l.project_site_id = ac.id 
                                        LEFT JOIN account_account act ON l.account_id=act.id
                                        where ac.analytic_account_type='project_site' and ac.group_id='owned' and
                                        l.date>='{str(from_date)}' and l.date<='{str(to_date)}' and l.company_id= ({company_id_str}) and l.parent_state='posted' and act.code_num BETWEEN {fa_depreciation_from} AND {fa_depreciation_to} 
                                        group by l.company_id,ac.id, act.id'''
            combined_query += f"{fa_depreciation_query} UNION ALL "

        if len(data["lease_finance_cost_ids"]) > 0:
            lease_finance_cost_query = f'''SELECT 
                                            'lease_finance_cost'                                       AS key,
                                            SUM(COALESCE(l.debit, 0)) - SUM(COALESCE(l.credit, 0)) AS balance,{account_name} as account_name,{project_site_name} as project_site_name,ac.id as project_site_id from account_move_line l 
                                            LEFT JOIN account_analytic_account ac ON l.project_site_id = ac.id 
                                            LEFT JOIN account_account act ON l.account_id=act.id
                                            where ac.analytic_account_type='project_site' and ac.group_id='owned' and
                                            l.date>='{str(from_date)}' and l.date<='{str(to_date)}' and l.company_id= ({company_id_str}) and l.parent_state='posted' and l.account_id in {lease_finance_cost_ids}
                                            group by l.company_id,ac.id, act.id'''
            combined_query += f"{lease_finance_cost_query} UNION ALL "
        if len(data["site_maintenance_ids"]) > 0:
            site_maintenance_query = f'''SELECT 
                                            'site_maintenance'                                       AS key,
                                            SUM(COALESCE(l.debit, 0)) - SUM(COALESCE(l.credit, 0)) AS balance,{account_name} as account_name,{project_site_name} as project_site_name,ac.id as project_site_id from account_move_line l 
                                            LEFT JOIN account_analytic_account ac ON l.project_site_id = ac.id 
                                            LEFT JOIN account_account act ON l.account_id=act.id
                                            where ac.analytic_account_type='project_site' and ac.group_id='owned' and
                                            l.date>='{str(from_date)}' and l.date<='{str(to_date)}' and l.company_id= ({company_id_str}) and l.parent_state='posted' and l.account_id in {site_maintenance_ids}
                                            group by l.company_id,ac.id, act.id'''
            combined_query += f"{site_maintenance_query} UNION ALL "

        if len(data["insurance_ids"]) > 0:
            insurance_query = f'''SELECT 
                                   'insurance'                                       AS key,
                                   SUM(COALESCE(l.debit, 0)) - SUM(COALESCE(l.credit, 0)) AS balance,{account_name} as account_name,{project_site_name} as project_site_name,ac.id as project_site_id from account_move_line l 
                                   LEFT JOIN account_analytic_account ac ON l.project_site_id = ac.id 
                                   LEFT JOIN account_account act ON l.account_id=act.id
                                   where ac.analytic_account_type='project_site' and ac.group_id='owned' and
                                   l.date>='{str(from_date)}' and l.date<='{str(to_date)}' and l.company_id= ({company_id_str}) and l.parent_state='posted' and l.account_id in {insurance_ids}
                                   group by l.company_id,ac.id, act.id'''
            combined_query += f"{insurance_query} UNION ALL "

        if len(data["energy_cost_ids"]) > 0:
            energy_cost_query = f'''SELECT 
                                       'energy_cost'                                       AS key,
                                       SUM(COALESCE(l.debit, 0)) - SUM(COALESCE(l.credit, 0)) AS balance,{account_name} as account_name,{project_site_name} as project_site_name,ac.id as project_site_id from account_move_line l 
                                       LEFT JOIN account_analytic_account ac ON l.project_site_id = ac.id 
                                       LEFT JOIN account_account act ON l.account_id=act.id
                                       where ac.analytic_account_type='project_site' and ac.group_id='owned' and
                                       l.date>='{str(from_date)}' and l.date<='{str(to_date)}' and l.company_id= ({company_id_str}) and l.parent_state='posted' and l.account_id in {energy_cost_ids}
                                       group by l.company_id,ac.id, act.id'''
            combined_query += f"{energy_cost_query} UNION ALL "
        if len(data["site_rent_ids"]) > 0:
            site_rent_query = f'''SELECT 
                                    'site_rent'                                       AS key,
                                    SUM(COALESCE(l.debit, 0)) - SUM(COALESCE(l.credit, 0)) AS balance,{account_name} as account_name,{project_site_name} as project_site_name,ac.id as project_site_id from account_move_line l 
                                    LEFT JOIN account_analytic_account ac ON l.project_site_id = ac.id 
                                    LEFT JOIN account_account act ON l.account_id=act.id
                                    where ac.analytic_account_type='project_site' and ac.group_id='owned' and
                                    l.date>='{str(from_date)}' and l.date<='{str(to_date)}' and l.company_id= ({company_id_str}) and l.parent_state='posted' and l.account_id in {site_rent_ids}
                                    group by l.company_id,ac.id, act.id'''
            combined_query += f"{site_rent_query} UNION ALL "
        if len(data["security_ids"]) > 0:
            security_query = f'''SELECT 
                                    'security'                                       AS key,
                                    SUM(COALESCE(l.debit, 0)) - SUM(COALESCE(l.credit, 0)) AS balance,{account_name} as account_name,{project_site_name} as project_site_name,ac.id as project_site_id from account_move_line l 
                                    LEFT JOIN account_analytic_account ac ON l.project_site_id = ac.id 
                                    LEFT JOIN account_account act ON l.account_id=act.id
                                    where ac.analytic_account_type='project_site' and ac.group_id='owned' and
                                    l.date>='{str(from_date)}' and l.date<='{str(to_date)}' and l.company_id= ({company_id_str}) and l.parent_state='posted' and l.account_id in {security_ids}
                                    group by l.company_id,ac.id, act.id'''
            combined_query += f"{security_query} UNION ALL "

        if len(data["service_level_credit_ids"]) > 0:
            service_level_credit_query = f'''SELECT 
                                                'service_level_credit'                                       AS key,
                                                SUM(COALESCE(l.debit, 0)) - SUM(COALESCE(l.credit, 0)) AS balance,{account_name} as account_name,{project_site_name} as project_site_name,ac.id as project_site_id from account_move_line l 
                                                LEFT JOIN account_analytic_account ac ON l.project_site_id = ac.id 
                                                LEFT JOIN account_account act ON l.account_id=act.id
                                                where ac.analytic_account_type='project_site' and ac.group_id='owned' and
                                                l.date>='{str(from_date)}' and l.date<='{str(to_date)}' and l.company_id= ({company_id_str}) and l.parent_state='posted' and l.account_id in {service_level_credit_ids}
                                                group by l.company_id,ac.id, act.id'''
            combined_query += f"{service_level_credit_query} UNION ALL "

        # Remove the last 'UNION ALL' if it exists
        if combined_query.endswith(" UNION ALL "):
            combined_query = combined_query[:-11]

        self._cr.execute(combined_query)
        res = self._cr.dictfetchall()
        grouped_data = defaultdict(
            lambda: {'service_revenue': 0, 'site_rent': 0,
                     'investment_revenue':0,
                     'colocation':0,'pass_through_energy':0,
                     'active_sharing_fees': 0,'discount': 0,
                     'site_maintenance': 0,'insurance':0,
                     'energy_cost':0,'security': 0,'service_level_credit': 0,
                     'rou_depreciation': 0, 'fa_depreciation': 0,
                     'lease_finance_cost': 0, 'project_site_name': '',
                     'account_name': ''})

        for record in res:
            site_code = record['project_site_id']
            project_site_name = record['project_site_name']
            account_name = record['account_name']
            grouped_data[site_code][
                'project_site_name'] = project_site_name  # Set project site name
            grouped_data[site_code]['account_name'] = account_name
            grouped_data[site_code][record['key']] += record['balance']

        row_num += 1
        analytic_accounts = self.env['account.analytic.account'].search(
            [('group_id', '=', 'owned'),
             ('analytic_account_type', '=', 'project_site'),
             ('company_id', '=', data["company_id"])])
        for psite in analytic_accounts:
            col_num = 1
            if  psite.id in grouped_data:
                values = grouped_data[psite.id]
                site_name = values.get('project_site_name', '')
                service_revenue = values.get('service_revenue', 0)
                investment_revenue = values.get('investment_revenue', 0)
                colocation = values.get('colocation', 0)
                site_rent = values.get('site_rent', 0)
                pass_through_energy = values.get('pass_through_energy')
                active_sharing_fees = values.get('active_sharing_fees')
                discount = values.get('discount', 0)
                site_maintenance = values.get('site_maintenance', 0)
                insurance = values.get('insurance', 0)
                energy_cost = values.get('energy_cost', 0)
                security = values.get('security', 0)
                service_level_credit = values.get('service_level_credit', 0)
                rou_depreciation = values.get('rou_depreciation', 0)
                fa_depreciation = values.get('fa_depreciation', 0)
                lease_finance_cost = values.get('lease_finance_cost', 0)
                total_revenue = service_revenue + investment_revenue + colocation + pass_through_energy + active_sharing_fees + discount
                total_cost = site_rent + site_maintenance + insurance + energy_cost + security + service_level_credit
                jdo = total_revenue - total_cost
                total_percent = ''
                if total_revenue != 0:
                    total_percent = (abs(jdo) / total_revenue) * 100

                sheet.write(row_num, col_num, sln_no)
                col_num += 1
                sheet.write(row_num, col_num, site_name)
                col_num += 1
                sheet.write(row_num, col_num, service_revenue)
                col_num += 1
                sheet.write(row_num, col_num, investment_revenue)
                col_num += 1
                sheet.write(row_num, col_num, colocation)
                col_num += 1
                sheet.write(row_num, col_num, pass_through_energy)
                col_num += 1
                sheet.write(row_num, col_num, active_sharing_fees)
                col_num += 1
                sheet.write(row_num, col_num, discount)
                col_num += 1
                sheet.write(row_num, col_num, total_revenue)
                col_num += 1
                sheet.write(row_num, col_num, site_maintenance)
                col_num += 1
                sheet.write(row_num, col_num, site_rent)
                col_num += 1
                sheet.write(row_num, col_num, insurance)
                col_num += 1
                sheet.write(row_num, col_num, energy_cost)
                col_num += 1
                sheet.write(row_num, col_num, security)
                col_num += 1
                sheet.write(row_num, col_num, service_level_credit)
                col_num += 1
                sheet.write(row_num, col_num,
                            total_cost)
                col_num += 1
                sheet.write(row_num, col_num,
                            abs(jdo))
                col_num += 1
                sheet.write(row_num, col_num,
                            total_percent)
                col_num += 1
                sheet.write(row_num, col_num, rou_depreciation)
                col_num += 1
                sheet.write(row_num, col_num, fa_depreciation)
                col_num += 1
                sheet.write(row_num, col_num, lease_finance_cost)
                col_num += 1

            else:
                sheet.write(row_num, col_num, sln_no)
                col_num += 1
                sheet.write(row_num, col_num, psite.name)
                col_num += 1
                sheet.write(row_num, col_num, 0)
                col_num += 1
                sheet.write(row_num, col_num, 0)
                col_num += 1
                sheet.write(row_num, col_num, 0)
                col_num += 1
                sheet.write(row_num, col_num, 0)
                col_num += 1
                sheet.write(row_num, col_num, 0)
                col_num += 1
                sheet.write(row_num, col_num, 0)
                col_num += 1
                sheet.write(row_num, col_num, 0)
                col_num += 1
                sheet.write(row_num, col_num, 0)
                col_num += 1
                sheet.write(row_num, col_num, 0)
                col_num += 1
                sheet.write(row_num, col_num, 0)
                col_num += 1
                sheet.write(row_num, col_num, 0)
                col_num += 1
                sheet.write(row_num, col_num, 0)
                col_num += 1
                sheet.write(row_num, col_num, 0)
                col_num += 1
                sheet.write(row_num, col_num,0)
                col_num += 1
                sheet.write(row_num, col_num,0)
                col_num += 1
                sheet.write(row_num, col_num, 0)
                col_num += 1
                sheet.write(row_num, col_num, 0)
                col_num += 1
                sheet.write(row_num, col_num, 0)
                col_num += 1
                sheet.write(row_num, col_num, 0)
                col_num += 1
            row_num += 1
            sln_no = sln_no + 1

        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()
