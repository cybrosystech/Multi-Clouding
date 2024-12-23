from odoo import fields, models, api
import json
import calendar
import io
from odoo.exceptions import UserError
from odoo.tools import date_utils, get_lang
from odoo.tools.safe_eval import datetime
import xlsxwriter
from collections import defaultdict


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
    from_date = fields.Date('From')
    to_date = fields.Date('To')
    current_filter = fields.Char('Selected Filter')

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

    @api.constrains('from_date','to_date')
    def onsave_period(self):
        if self.from_date and self.to_date:
            if self.from_date > self.to_date:
                raise UserError("Start date should be less than end date")

    def action_get_report(self):
        data = {
            'lease_anchor_tenant_ids': self.lease_anchor_tenant.ids,
            'lease_colo_tenant_ids': self.lease_colo_tenant.ids,
            'additional_space_revenue_ids': self.additional_space_revenue.ids,
            'bts_revenue_ids': self.bts_revenue.ids,
            'active_sharing_fees_ids': self.active_sharing_fees.ids,
            'discount_ids': self.discount.ids,
            'rou_depreciation_ids': self.rou_depreciation.ids,
            'fa_depreciation_ids': self.fa_depreciation.ids,
            'lease_finance_cost_ids': self.lease_finance_cost.ids,
            'site_maintenance_ids': self.site_maintenance_managed.ids,
            'site_rent_ids': self.site_rent.ids,
            'security_ids': self.security.ids,
            'service_level_credit_ids': self.service_level_credits.ids,
            'from': self.from_date if self.from_date else fields.Date.today(),
            'to': self.to_date if self.to_date else fields.Date.today(),
            'company_id': self.company_id.id,
            'Current_months': self.current_filter,
        }
        return {
            'type': 'ir.actions.report',
            'data': {'model': 'profitability.report.managed',
                     'options': json.dumps(data,
                                           default=date_utils.json_default),
                     'output_format': 'xlsx',
                     'report_name': 'Profitability Managed Report',
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

        sheet.merge_range('B2:T2', self.current_filter,
                          main_head)
        sheet.merge_range('D3:J3', 'Revenues', head)
        sheet.merge_range('K3:R3', 'Costs', head)
        sheet.merge_range('S3:T3', 'Gross Profit', head)

        row_num = 3
        sln_no = 1
        lang = self.env.user.lang or get_lang(self.env).code
        project_site_name = f"COALESCE(ac.name->>'{lang}', ac.name->>'en_US')" if \
            self.pool[
                'account.analytic.account'].name.translate else 'ac.name'
        account_name = f"COALESCE(act.name->>'{lang}', act.name->>'en_US')" if \
            self.pool[
                'account.analytic.account'].name.translate else 'act.name'

        lease_anchor_tenant_ids =  data["lease_anchor_tenant_ids"]
        if len(lease_anchor_tenant_ids) == 1:
            lease_anchor_tenant_ids = f"({lease_anchor_tenant_ids[0]})"  # Single-element tuple for SQL
        else:
            lease_anchor_tenant_ids = str(tuple(lease_anchor_tenant_ids))

        lease_colo_tenant_ids = data["lease_colo_tenant_ids"]
        if len(lease_colo_tenant_ids) == 1:
            lease_colo_tenant_ids = f"({lease_colo_tenant_ids[0]})"  # Single-element tuple for SQL
        else:
            lease_colo_tenant_ids = str(tuple(lease_colo_tenant_ids))

        additional_space_revenue_ids = data["additional_space_revenue_ids"]
        if len(additional_space_revenue_ids) == 1:
            additional_space_revenue_ids = f"({additional_space_revenue_ids[0]})"  # Single-element tuple for SQL
        else:
            additional_space_revenue_ids = str(tuple(additional_space_revenue_ids))

        bts_revenue_ids =data["bts_revenue_ids"]
        if len(bts_revenue_ids) == 1:
            bts_revenue_ids = f"({bts_revenue_ids[0]})"  # Single-element tuple for SQL
        else:
            bts_revenue_ids = str(tuple(bts_revenue_ids))

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

        rou_depreciation_ids = data["rou_depreciation_ids"]
        if len(rou_depreciation_ids) == 1:
            rou_depreciation_ids = f"({rou_depreciation_ids[0]})"  # Single-element tuple for SQL
        else:
            rou_depreciation_ids = str(tuple(rou_depreciation_ids))

        fa_depreciation_ids = data["fa_depreciation_ids"]
        if len(fa_depreciation_ids) == 1:
            fa_depreciation_ids = f"({fa_depreciation_ids[0]})"  # Single-element tuple for SQL
        else:
            fa_depreciation_ids = str(tuple(fa_depreciation_ids))

        lease_finance_cost_ids = data["lease_finance_cost_ids"]
        if len(lease_finance_cost_ids) == 1:
            lease_finance_cost_ids = f"({lease_finance_cost_ids[0]})"  # Single-element tuple for SQL
        else:
            lease_finance_cost_ids = str(tuple(lease_finance_cost_ids))

        site_maintenance_ids = data["site_maintenance_ids"]
        if len(site_maintenance_ids) == 1:
            site_maintenance_ids = f"({site_maintenance_ids[0]})"  # Single-element tuple for SQL
        else:
            site_maintenance_ids = str(tuple(site_maintenance_ids))

        site_rent_ids = data["site_rent_ids"]
        if len(site_rent_ids) == 1:
            site_rent_ids = f"({site_rent_ids[0]})"  # Single-element tuple for SQL
        else:
            site_rent_ids = str(tuple(site_rent_ids))

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

        from_date = data["from"]
        to_date = data["to"]
        company_id_str = str(data["company_id"])
        combined_query = ""

        if len(data["lease_anchor_tenant_ids"])>0:
            lease_anchor_tenant_query = f'''SELECT 
                        'lease_anchor_tenant'                                       AS key,
                        SUM(COALESCE(l.debit, 0)) - SUM(COALESCE(l.credit, 0)) AS balance,{account_name} as account_name,{project_site_name} as project_site_name,ac.id as project_site_id from account_move_line l 
                        LEFT JOIN account_analytic_account ac ON l.project_site_id = ac.id 
                        LEFT JOIN account_account act ON l.account_id=act.id
                        where ac.analytic_account_type='project_site' and ac.group_id='managed' and
                        l.date>='{str(from_date)}' and l.date<='{str(to_date)}' and l.company_id= ({company_id_str}) and l.parent_state='posted' and l.account_id in {lease_anchor_tenant_ids}
                        group by l.company_id,ac.id, act.id'''
            combined_query += f"{lease_anchor_tenant_query} UNION ALL "
        if len(data["lease_colo_tenant_ids"])>0:
            lease_colo_tenant_query = f'''SELECT 
                                'lease_colo_tenant'                                       AS key,
                                SUM(COALESCE(l.debit, 0)) - SUM(COALESCE(l.credit, 0)) AS balance,{account_name} as account_name,{project_site_name} as project_site_name,ac.id as project_site_id from account_move_line l 
                                LEFT JOIN account_analytic_account ac ON l.project_site_id = ac.id 
                                LEFT JOIN account_account act ON l.account_id=act.id
                                where ac.analytic_account_type='project_site' and ac.group_id='managed' and
                                l.date>='{str(from_date)}' and l.date<='{str(to_date)}' and l.company_id= ({company_id_str}) and l.parent_state='posted' and l.account_id in {lease_colo_tenant_ids}
                                group by l.company_id,ac.id, act.id'''
            combined_query += f"{lease_colo_tenant_query} UNION ALL "
        if len(data["additional_space_revenue_ids"])>0:
            additional_space_revenue_query = f'''SELECT 
                                        'additional_space_revenue'                                       AS key,
                                        SUM(COALESCE(l.debit, 0)) - SUM(COALESCE(l.credit, 0)) AS balance,{account_name} as account_name,{project_site_name} as project_site_name,ac.id as project_site_id from account_move_line l 
                                        LEFT JOIN account_analytic_account ac ON l.project_site_id = ac.id 
                                        LEFT JOIN account_account act ON l.account_id=act.id
                                        where ac.analytic_account_type='project_site' and ac.group_id='managed' and
                                        l.date>='{str(from_date)}' and l.date<='{str(to_date)}' and l.company_id= ({company_id_str}) and l.parent_state='posted' and l.account_id in {additional_space_revenue_ids}
                                        group by l.company_id,ac.id, act.id'''
            combined_query += f"{additional_space_revenue_query} UNION ALL "

        if len(data["bts_revenue_ids"])>0:
            bts_revenue_query = f'''SELECT 
                        'bts_revenue'                                       AS key,
                        SUM(COALESCE(l.debit, 0)) - SUM(COALESCE(l.credit, 0)) AS balance,{account_name} as account_name,{project_site_name} as project_site_name,ac.id as project_site_id from account_move_line l 
                        LEFT JOIN account_analytic_account ac ON l.project_site_id = ac.id 
                        LEFT JOIN account_account act ON l.account_id=act.id
                        where ac.analytic_account_type='project_site' and ac.group_id='managed' and
                        l.date>='{str(from_date)}' and l.date<='{str(to_date)}' and l.company_id=({company_id_str}) and l.parent_state='posted' and l.account_id in {bts_revenue_ids}
                        group by l.company_id,ac.id, act.id'''
            combined_query += f"{bts_revenue_query} UNION ALL "
        if len(data["active_sharing_fees_ids"])>0:
            active_sharing_fees_query = f'''SELECT 
                                            'active_sharing_fees'                                       AS key,
                                            SUM(COALESCE(l.debit, 0)) - SUM(COALESCE(l.credit, 0)) AS balance,{account_name} as account_name,{project_site_name} as project_site_name,ac.id as project_site_id from account_move_line l 
                                            LEFT JOIN account_analytic_account ac ON l.project_site_id = ac.id 
                                            LEFT JOIN account_account act ON l.account_id=act.id
                                            where ac.analytic_account_type='project_site' and ac.group_id='managed' and
                                            l.date>='{str(from_date)}' and l.date<='{str(to_date)}' and l.company_id= ({company_id_str}) and l.parent_state='posted' and l.account_id in {active_sharing_fees_ids}
                                            group by l.company_id,ac.id, act.id'''
            combined_query += f"{active_sharing_fees_query} UNION ALL "
        if len(data["discount_ids"])>0:
            discount_query = f'''SELECT 
                                        'discount'                                       AS key,
                                        SUM(COALESCE(l.debit, 0)) - SUM(COALESCE(l.credit, 0)) AS balance,{account_name} as account_name,{project_site_name} as project_site_name,ac.id as project_site_id from account_move_line l 
                                        LEFT JOIN account_analytic_account ac ON l.project_site_id = ac.id 
                                        LEFT JOIN account_account act ON l.account_id=act.id
                                        where ac.analytic_account_type='project_site' and ac.group_id='managed' and
                                        l.date>='{str(from_date)}' and l.date<='{str(to_date)}' and l.company_id= ({company_id_str}) and l.parent_state='posted' and l.account_id in {discount_ids}
                                        group by l.company_id,ac.id, act.id'''
            combined_query += f"{discount_query} UNION ALL "
        if len(data["rou_depreciation_ids"])>0:
            rou_depreciation_query = f'''SELECT 
                                            'rou_depreciation'                                       AS key,
                                            SUM(COALESCE(l.debit, 0)) - SUM(COALESCE(l.credit, 0)) AS balance,{account_name} as account_name,{project_site_name} as project_site_name,ac.id as project_site_id from account_move_line l 
                                            LEFT JOIN account_analytic_account ac ON l.project_site_id = ac.id 
                                            LEFT JOIN account_account act ON l.account_id=act.id
                                            where ac.analytic_account_type='project_site' and ac.group_id='managed' and
                                            l.date>='{str(from_date)}' and l.date<='{str(to_date)}' and l.company_id= ({company_id_str}) and l.parent_state='posted' and l.account_id in {rou_depreciation_ids}
                                            group by l.company_id,ac.id, act.id'''
            combined_query += f"{rou_depreciation_query} UNION ALL "
        if len(data["fa_depreciation_ids"])>0:
            fa_depreciation_query = f'''SELECT 
                                            'fa_depreciation'                                       AS key,
                                            SUM(COALESCE(l.debit, 0)) - SUM(COALESCE(l.credit, 0)) AS balance,{account_name} as account_name,{project_site_name} as project_site_name,ac.id as project_site_id from account_move_line l 
                                            LEFT JOIN account_analytic_account ac ON l.project_site_id = ac.id 
                                            LEFT JOIN account_account act ON l.account_id=act.id
                                            where ac.analytic_account_type='project_site' and ac.group_id='managed' and
                                            l.date>='{str(from_date)}' and l.date<='{str(to_date)}' and l.company_id= ({company_id_str}) and l.parent_state='posted' and l.account_id in {fa_depreciation_ids}
                                            group by l.company_id,ac.id, act.id'''
            combined_query += f"{fa_depreciation_query} UNION ALL "
        if len(data["lease_finance_cost_ids"])>0:
            lease_finance_cost_query = f'''SELECT 
                                                'lease_finance_cost'                                       AS key,
                                                SUM(COALESCE(l.debit, 0)) - SUM(COALESCE(l.credit, 0)) AS balance,{account_name} as account_name,{project_site_name} as project_site_name,ac.id as project_site_id from account_move_line l 
                                                LEFT JOIN account_analytic_account ac ON l.project_site_id = ac.id 
                                                LEFT JOIN account_account act ON l.account_id=act.id
                                                where ac.analytic_account_type='project_site' and ac.group_id='managed' and
                                                l.date>='{str(from_date)}' and l.date<='{str(to_date)}' and l.company_id= ({company_id_str}) and l.parent_state='posted' and l.account_id in {lease_finance_cost_ids}
                                                group by l.company_id,ac.id, act.id'''
            combined_query += f"{lease_finance_cost_query} UNION ALL "
        if len(data["site_maintenance_ids"])>0:
            site_maintenance_query = f'''SELECT 
                                            'site_maintenance'                                       AS key,
                                            SUM(COALESCE(l.debit, 0)) - SUM(COALESCE(l.credit, 0)) AS balance,{account_name} as account_name,{project_site_name} as project_site_name,ac.id as project_site_id from account_move_line l 
                                            LEFT JOIN account_analytic_account ac ON l.project_site_id = ac.id 
                                            LEFT JOIN account_account act ON l.account_id=act.id
                                            where ac.analytic_account_type='project_site' and ac.group_id='managed' and
                                            l.date>='{str(from_date)}' and l.date<='{str(to_date)}' and l.company_id= ({company_id_str}) and l.parent_state='posted' and l.account_id in {site_maintenance_ids}
                                            group by l.company_id,ac.id, act.id'''
            combined_query += f"{site_maintenance_query} UNION ALL "
        if len(data["site_rent_ids"])>0:
            site_rent_query = f'''SELECT 
                                        'site_rent'                                       AS key,
                                        SUM(COALESCE(l.debit, 0)) - SUM(COALESCE(l.credit, 0)) AS balance,{account_name} as account_name,{project_site_name} as project_site_name,ac.id as project_site_id from account_move_line l 
                                        LEFT JOIN account_analytic_account ac ON l.project_site_id = ac.id 
                                        LEFT JOIN account_account act ON l.account_id=act.id
                                        where ac.analytic_account_type='project_site' and ac.group_id='managed' and
                                        l.date>='{str(from_date)}' and l.date<='{str(to_date)}' and l.company_id= ({company_id_str}) and l.parent_state='posted' and l.account_id in {site_rent_ids}
                                        group by l.company_id,ac.id, act.id'''
            combined_query += f"{site_rent_query} UNION ALL "
        if len(data["security_ids"])>0:
            security_query = f'''SELECT 
                                        'security'                                       AS key,
                                        SUM(COALESCE(l.debit, 0)) - SUM(COALESCE(l.credit, 0)) AS balance,{account_name} as account_name,{project_site_name} as project_site_name,ac.id as project_site_id from account_move_line l 
                                        LEFT JOIN account_analytic_account ac ON l.project_site_id = ac.id 
                                        LEFT JOIN account_account act ON l.account_id=act.id
                                        where ac.analytic_account_type='project_site' and ac.group_id='managed' and
                                        l.date>='{str(from_date)}' and l.date<='{str(to_date)}' and l.company_id= ({company_id_str}) and l.parent_state='posted' and l.account_id in {security_ids}
                                        group by l.company_id,ac.id, act.id'''
            combined_query += f"{security_query} UNION ALL "

        if len(data["service_level_credit_ids"])>0:
            service_level_credit_query = f'''SELECT 
                                            'service_level_credit'                                       AS key,
                                            SUM(COALESCE(l.debit, 0)) - SUM(COALESCE(l.credit, 0)) AS balance,{account_name} as account_name,{project_site_name} as project_site_name,ac.id as project_site_id from account_move_line l 
                                            LEFT JOIN account_analytic_account ac ON l.project_site_id = ac.id 
                                            LEFT JOIN account_account act ON l.account_id=act.id
                                            where ac.analytic_account_type='project_site' and ac.group_id='managed' and
                                            l.date>='{str(from_date)}' and l.date<='{str(to_date)}' and l.company_id= ({company_id_str}) and l.parent_state='posted' and l.account_id in {service_level_credit_ids}
                                            group by l.company_id,ac.id, act.id'''
            combined_query += f"{service_level_credit_query} UNION ALL "

        # Remove the last 'UNION ALL' if it exists
        if combined_query.endswith(" UNION ALL "):
            combined_query = combined_query[:-11]

        self._cr.execute(combined_query)
        res = self._cr.dictfetchall()
        grouped_data = defaultdict(
            lambda: {'lease_anchor_tenant': 0, 'lease_colo_tenant':0,
                     'additional_space_revenue':0,
                     'active_sharing_fees':0,'discount':0,
                     'rou_depreciation':0,'fa_depreciation':0,
                     'bts_revenue': 0,'lease_finance_cost':0,
                     'site_maintenance':0,'site_rent':0,
                     'security':0,'service_level_credit':0,
                     'project_site_name': '', 'account_name': ''})

        for record in res:
            site_code = record['project_site_id']
            project_site_name = record['project_site_name']
            account_name = record['account_name']

            grouped_data[site_code][
                'project_site_name'] = project_site_name  # Set project site name
            grouped_data[site_code]['account_name'] = account_name
            grouped_data[site_code][record['key']] += record['balance']
        row_num+=1
        analytic_accounts = self.env['account.analytic.account'].search(
            [('group_id', '=', 'managed'),
             ('analytic_account_type', '=', 'project_site'),
             ('company_id', '=', data["company_id"])])
        for psite in analytic_accounts:
            col_num = 1
            if  psite.id in grouped_data:
                values = grouped_data[psite.id]
                site_name = values.get('project_site_name', '')
                lease_anchor_tenant = values.get('lease_anchor_tenant', 0)
                lease_colo_tenant = values.get('lease_colo_tenant', 0)
                additional_space_revenue = values.get(
                    'additional_space_revenue', 0)
                active_sharing_fees = values.get('active_sharing_fees', 0)
                discount = values.get('discount', 0)
                rou_depreciation = values.get('rou_depreciation', 0)
                fa_depreciation = values.get('fa_depreciation', 0)
                lease_finance_cost = values.get('lease_finance_cost', 0)
                site_maintenance = values.get('site_maintenance', 0)
                site_rent = values.get('site_rent', 0)
                security = values.get('security', 0)
                service_level_credit = values.get('service_level_credit', 0)
                bts_revenue = values.get('bts_revenue', 0)
                total_revenue = lease_anchor_tenant + lease_colo_tenant + additional_space_revenue + bts_revenue + active_sharing_fees + discount
                total_cost = rou_depreciation + fa_depreciation + lease_finance_cost + site_maintenance + site_rent + security + service_level_credit
                jdo = total_revenue - total_cost
                total_percent = ''
                if total_revenue != 0:
                    total_percent = (abs(jdo) / total_revenue) * 100

                sheet.write(row_num, col_num, sln_no)
                col_num += 1
                sheet.write(row_num, col_num, site_name)
                col_num += 1
                sheet.write(row_num, col_num, lease_anchor_tenant)
                col_num += 1
                sheet.write(row_num, col_num, lease_colo_tenant)
                col_num += 1
                sheet.write(row_num, col_num, additional_space_revenue)
                col_num += 1
                sheet.write(row_num, col_num, bts_revenue)
                col_num += 1
                sheet.write(row_num, col_num, active_sharing_fees)
                col_num += 1
                sheet.write(row_num, col_num, discount)
                col_num += 1
                sheet.write(row_num, col_num, total_revenue)
                col_num += 1
                sheet.write(row_num, col_num, rou_depreciation)
                col_num += 1
                sheet.write(row_num, col_num, fa_depreciation)
                col_num += 1
                sheet.write(row_num, col_num, lease_finance_cost)
                col_num += 1
                sheet.write(row_num, col_num, site_maintenance)
                col_num += 1
                sheet.write(row_num, col_num, site_rent)
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
                sheet.write(row_num, col_num, 0)
                col_num += 1
                sheet.write(row_num, col_num,0)
                col_num += 1
                sheet.write(row_num, col_num,0)
                col_num += 1
                sheet.write(row_num, col_num,0)
                col_num += 1
            row_num += 1
            sln_no = sln_no + 1

        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()
