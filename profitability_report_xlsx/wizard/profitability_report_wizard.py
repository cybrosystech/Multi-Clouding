import io
from email.policy import default
from odoo.tools import date_utils, get_lang
from dateutil.relativedelta import relativedelta

from odoo import fields, models
from odoo.exceptions import UserError
from odoo.tools import date_utils, xlsxwriter
from odoo.tools.safe_eval import datetime, json
import calendar


class ProfitabilityReportWizard(models.TransientModel):
    _name = "profitability.report.wizard"

    def default_service_revenue(self):
        profitability = self.env['profitability.report.owned'].search([])
        if profitability.service_revenue:
            return profitability.service_revenue
        return self.env['account.account'].search([('code', '=',
                                                    '411201'),
                                                   ('company_id',
                                                    '=',
                                                    self.env.company.id)])

    def default_site_rent(self):
        profitability_managed = self.env['profitability.report.managed'].search(
            [])
        if profitability_managed:
            return profitability_managed.site_rent.ids
        else:
            return []

    def default_investment_revenue(self):
        profitability = self.env['profitability.report.owned'].search([])
        if profitability.investment_revenue:
            return profitability.investment_revenue
        return self.env['account.account'].search([('code', '=',
                                                    '411101'),
                                                   ('company_id',
                                                    '=',
                                                    self.env.company.id)])

    def default_colocation(self):
        profitability = self.env['profitability.report.owned'].search([])
        if profitability.colocation:
            return profitability.colocation
        return self.env['account.account'].search([('code', '=',
                                                    '411501'),
                                                   ('company_id',
                                                    '=',
                                                    self.env.company.id)])

    def default_pass_through_energy(self):
        profitability = self.env['profitability.report.owned'].search([])
        if profitability.pass_through_energy:
            return profitability.pass_through_energy

    def default_active_sharing_fees(self):
        profitability = self.env['profitability.report.owned'].search([])
        if profitability.active_sharing_fees:
            return profitability.active_sharing_fees

    def default_discount(self):
        profitability = self.env['profitability.report.owned'].search([])
        if profitability.discount:
            return profitability.discount

    def default_site_maintenance(self):
        profitability = self.env['profitability.report.owned'].search([])
        if profitability.site_maintenance:
            return profitability.site_maintenance

    def default_insurance(self):
        profitability = self.env['profitability.report.owned'].search([])
        if profitability.insurance:
            return profitability.insurance
        return self.env['account.account'].search([('code', '=',
                                                    '422701'),
                                                   ('company_id',
                                                    '=',
                                                    self.env.company.id)])

    def default_energy_cost(self):
        profitability = self.env['profitability.report.owned'].search([])
        if profitability.energy_cost:
            return profitability.energy_cost
        return self.env['account.account'].search([('code', 'in',
                                                    ['422401', '422401']),
                                                   ('company_id',
                                                    '=',
                                                    self.env.company.id)])

    def default_security(self):
        profitability = self.env['profitability.report.owned'].search([])
        if profitability.security:
            return profitability.security
        return self.env['account.account'].search([('code', '=',
                                                    '422301'),
                                                   ('company_id',
                                                    '=',
                                                    self.env.company.id)])

    def default_service_level_credit(self):
        profitability = self.env['profitability.report.owned'].search([])
        if profitability.service_level_credit:
            return profitability.service_level_credit

    def default_rou_depreciation(self):
        profitability = self.env['profitability.report.owned'].search([])
        if profitability.rou_depreciation:
            return profitability.rou_depreciation
        return self.env['account.account'].search([('code', '=',
                                                    '554101'),
                                                   ('company_id',
                                                    '=',
                                                    self.env.company.id)])

    def default_fa_depreciation(self):
        profitability = self.env['profitability.report.owned'].search([])
        if profitability.fa_depreciation:
            return profitability.fa_depreciation

    def default_fa_depreciation_lim(self):
        profitability = self.env['profitability.report.owned'].search([])
        if profitability.fa_depreciation_lim:
            return profitability.fa_depreciation_lim

    def default_lease_finance_cost(self):
        profitability = self.env['profitability.report.owned'].search([])
        if profitability.lease_finance_cost:
            return profitability.lease_finance_cost

    service_revenue = fields.Many2many('account.account', 'service_revenue_rel',
                                       string='Service Revenue',
                                       default=default_service_revenue)
    site_rent_ids = fields.Many2many('account.account',
                                     'site_rent_ids_relation',
                                     string='Site Rent',
                                     default=default_site_rent)
    investment_revenue = fields.Many2many('account.account',
                                          'investment_revenue_rel',
                                          string='Investment Revenue',
                                          default=default_investment_revenue)

    colocation = fields.Many2many('account.account', 'colocation_rel',
                                  string='Colocation',
                                  default=default_colocation)
    pass_through_energy = fields.Many2many('account.account',
                                           'pass_through_energy',
                                           string='Pass Through Energy',
                                           default=default_pass_through_energy)
    active_sharing_fees = fields.Many2many('account.account',
                                           'active_sharing_fees',
                                           string='Active Sharing Fees',
                                           default=default_active_sharing_fees)
    discount = fields.Many2many('account.account', 'disc',
                                string='Discount',
                                default=default_discount)
    site_maintenance = fields.Many2many('account.account', 'site_maintenance',
                                        default=default_site_maintenance)

    insurance = fields.Many2many('account.account', 'insurance',
                                 string="Insurance", default=default_insurance)
    energy_cost = fields.Many2many('account.account', 'energy_cost',
                                   string='Energy Cost',
                                   default=default_energy_cost)
    security = fields.Many2many('account.account', 'security',
                                string='Security', default=default_security)
    service_level_credit = fields.Many2many('account.account',
                                            'service_level_credit',
                                            string='Service Level Credit',
                                            default=default_service_level_credit)
    rou_depreciation = fields.Many2many('account.account',
                                        'rou_depreciation_rels',
                                        string='ROU Depreciation',
                                        default=default_rou_depreciation)
    fa_depreciation = fields.Many2many('account.account',
                                       'fa_depreciation_rels',
                                       string='FA Depreciation',
                                       default=default_fa_depreciation)
    fa_depreciation_lim = fields.Many2many('account.account',
                                           'fa_depreciation_lim_rels',
                                           string='FA Depreciation',
                                           default=default_fa_depreciation_lim)
    lease_finance_cost = fields.Many2many('account.account',
                                          'lease_finance_cost_rels',
                                          string='Leases Finance Cost',
                                          default=default_lease_finance_cost)

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

    group = fields.Selection([
        ('managed', 'Managed'),
        ('owned', 'Owned')], 'Group', default='owned')
    from_date = fields.Date('From')
    to_date = fields.Date('To')
    company_id = fields.Many2one('res.company', 'Company',
                                 default=lambda self: self.env.company)

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

        if self.fa_depreciation and self.fa_depreciation_lim:
            if not self.fa_depreciation.code < self.fa_depreciation_lim.code:
                raise UserError("Please set the limit of Fa depreciation "
                                "correctly")
        profitability = self.env['profitability.report.owned'].search([])

        if not profitability:
            self.env['profitability.report.owned'].create({
                'service_revenue': self.service_revenue,
                'site_rent_ids': self.site_rent_ids,
                'investment_revenue': self.investment_revenue,
                'colocation': self.colocation,
                'pass_through_energy': self.pass_through_energy,
                'active_sharing_fees': self.active_sharing_fees,
                'discount': self.discount,
                'site_maintenance': self.site_maintenance,
                # 'site_maintenance_lim': self.site_maintenance_lim,
                'insurance': self.insurance,
                'energy_cost': self.energy_cost,
                'security': self.security,
                'service_level_credit': self.service_level_credit,
                'rou_depreciation': self.rou_depreciation,
                'fa_depreciation_lim': self.fa_depreciation_lim,
                'fa_depreciation': self.fa_depreciation,
                'lease_finance_cost': self.lease_finance_cost
            })

        profitability.update({
            'service_revenue': self.service_revenue,
            'site_rent_ids': self.site_rent_ids,
            'investment_revenue': self.investment_revenue,
            'colocation': self.colocation,
            'pass_through_energy': self.pass_through_energy,
            'active_sharing_fees': self.active_sharing_fees,
            'discount': self.discount,
            'site_maintenance': self.site_maintenance,
            # 'site_maintenance_lim': self.site_maintenance_lim,
            'insurance': self.insurance,
            'energy_cost': self.energy_cost,
            'security': self.security,
            'service_level_credit': self.service_level_credit,
            'rou_depreciation': self.rou_depreciation,
            'fa_depreciation': self.fa_depreciation,
            'fa_depreciation_lim': self.fa_depreciation_lim,
            'lease_finance_cost': self.lease_finance_cost,
        })
        data = {
            'ids': self.ids,
            'model': self._name,
            'service_revenue_ids': self.service_revenue.ids,
            'site_rent_ids': self.site_rent_ids.ids,
            'investment_revenue_ids': self.investment_revenue.ids,
            'colocation_ids': self.colocation.ids,
            'pass_through_energy_ids': self.pass_through_energy.ids,
            'active_sharing_fees_ids': self.active_sharing_fees.ids,
            'discount_ids': self.discount.ids,
            'site_maintenance_ids': self.site_maintenance.ids,
            # 'site_maintenance_lim_code': self.site_maintenance_lim.code,
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
            'company_id': self.company_id.id,
            'group': self.group,
            'Current_months': Current_months
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

    def get_xlsx(self, data, response):
        total_site = 0
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        account_ids = ''
        account_fa_depreciation_ids = ''
        lang = self.env.user.lang or get_lang(self.env).code
        cr = self._cr
        name = f"COALESCE(analatyc_account.name->>'{lang}', analatyc_account.name->>'en_US')" if \
            self.pool[
                'account.analytic.account'].name.translate else 'analatyc_account.name'

        query = f'''
                    SELECT id, {name} AS name 
                    FROM account_analytic_account AS analatyc_account 
                    WHERE analatyc_account.analytic_account_type = %(type)s
                    AND analatyc_account.company_id = %(company_id)s
                    AND analatyc_account.group_id = %(group)s
                '''
        params = {
            'company_id': data["company_id"],
            'type': 'project_site',
            'group': data["group"],
        }

        cr.execute(query, params)
        project_site = cr.dictfetchall()

        if data['fa_depreciation_code'] and data['fa_depreciation_lim_code']:
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

        profitability_report = []
        for i in project_site:
            prof_rep = {}
            prof_rep.update({
                'project': i['name'],
            })

            service_revenue_qry = """WITH filtered_projects AS (
                                        SELECT
                                            aml.debit,
                                            aml.credit
                                        FROM
                                            account_move_line aml
                                        JOIN
                                            account_move am ON aml.move_id = am.id
                                        WHERE
                                            aml.project_site_id = %(project_site_id)s
                                            AND am.date >= %(date_from)s
                                            AND am.date <= %(date_to)s
                                            AND am.state = 'posted'
                                            AND aml.company_id = %(company_id)s
                                            AND aml.account_id IN %(service_revenue_ids)s
                                    )
                                    SELECT
                                        COALESCE(SUM(fp.debit), 0) - COALESCE(SUM(fp.credit), 0) AS total_service_revenue
                                    FROM
                                        filtered_projects fp;
                                    """

            cr.execute(service_revenue_qry, {
                'company_id': data["company_id"],
                'service_revenue_ids': tuple(data['service_revenue_ids']),
                'date_from': data["from"],
                'date_to': data["to"],
                'project_site_id': i['id'],
            })
            service_revenue_res = cr.dictfetchall()
            prof_rep.update({
                'service_revenue': service_revenue_res[0][
                    'total_service_revenue'],
            })

            site_rents_qry = """WITH filtered_projects AS (
                                                    SELECT
                                                        aml.debit,
                                                        aml.credit
                                                    FROM
                                                        account_move_line aml
                                                    JOIN
                                                        account_move am ON aml.move_id = am.id
                                                    WHERE
                                                        aml.project_site_id = %(project_site_id)s
                                                        AND am.date >= %(date_from)s
                                                        AND am.date <= %(date_to)s
                                                        AND am.state = 'posted'
                                                        AND aml.company_id = %(company_id)s
                                                        AND aml.account_id IN %(site_rent_ids)s
                                                )
                                                SELECT
                                                    COALESCE(SUM(fp.debit), 0) - COALESCE(SUM(fp.credit), 0) AS total_site_rents
                                                FROM
                                                    filtered_projects fp;
                                                """

            cr.execute(site_rents_qry, {
                'company_id': data["company_id"],
                'site_rent_ids': tuple(data['site_rent_ids']),
                'date_from': data["from"],
                'date_to': data["to"],
                'project_site_id': i['id'],
            })
            site_rents_res = cr.dictfetchall()
            prof_rep.update({
                'site_rent': site_rents_res[0][
                    'total_site_rents'],
            })

            colocation_qry = """WITH filtered_projects AS (
                                    SELECT
                                        aml.debit,
                                        aml.credit,
                                        aml.account_id
                                    FROM
                                        account_move_line aml
                                    JOIN
                                        account_move am ON aml.move_id = am.id
                                    WHERE
                                        aml.project_site_id = %(project_site_id)s
                                        AND am.date <= %(date_to)s
                                        AND am.date >= %(date_from)s
                                        AND am.state = 'posted'
                                        AND aml.company_id = %(company_id)s
                                ),
                                colocation AS (
                                    SELECT
                                        fp.debit,
                                        fp.credit
                                    FROM
                                        filtered_projects fp
                                    WHERE
                                        fp.account_id IN %(colocation_ids)s
                                )
                                SELECT
                                    COALESCE(SUM(c.debit), 0) - COALESCE(SUM(c.credit), 0) AS total_colocation
                                FROM
                                    colocation c;
                                """

            cr.execute(colocation_qry, {
                'company_id': data["company_id"],
                'colocation_ids': tuple(data['colocation_ids']),
                'date_from': data["from"],
                'date_to': data["to"],
                'project_site_id': i['id'],
            })
            colocation_res = cr.dictfetchall()

            prof_rep.update({
                'colocation': colocation_res[0]['total_colocation'],
            })

            investment_revenue_qry = """
                                       WITH filtered_projects AS (
                                        SELECT
                                            aml.debit,
                                            aml.credit,
                                            aml.account_id
                                        FROM
                                            account_move_line aml
                                        JOIN
                                            account_move am ON aml.move_id = am.id
                                        WHERE
                                            aml.project_site_id = %(project_site_id)s
                                            AND am.date <= %(date_to)s
                                            AND am.date >= %(date_from)s
                                            AND am.state = 'posted'
                                            AND aml.company_id = %(company_id)s
                                    ),
                                    investment_revenue AS (
                                        SELECT
                                            fp.debit,
                                            fp.credit
                                        FROM
                                            filtered_projects fp
                                        WHERE
                                            fp.account_id IN %(investment_revenue_ids)s
                                    )
                                    SELECT
                                        COALESCE(SUM(c.debit), 0) - COALESCE(SUM(c.credit), 0) AS total_investment_revenue
                                    FROM
                                    investment_revenue c;
                                    """
            cr.execute(investment_revenue_qry, {
                'company_id': data["company_id"],
                'investment_revenue_ids': tuple(data['investment_revenue_ids']),
                'date_from': data["from"],
                'date_to': data["to"],
                'project_site_id': i['id'],
            })
            investment_revenue_res = cr.dictfetchall()

            prof_rep.update({
                'investment_revenue': investment_revenue_res[0][
                    "total_investment_revenue"],
            })

            pass_through_energy_qry = """
                                       WITH filtered_projects AS (
                                        SELECT
                                            aml.debit,
                                            aml.credit,
                                            aml.account_id
                                        FROM
                                            account_move_line aml
                                        JOIN
                                            account_move am ON aml.move_id = am.id
                                        WHERE
                                            aml.project_site_id = %(project_site_id)s
                                            AND am.date <= %(date_to)s
                                            AND am.date >= %(date_from)s
                                            AND am.state = 'posted'
                                            AND aml.company_id = %(company_id)s
                                    ),
                                    pass_through_energy AS (
                                        SELECT
                                            fp.debit,
                                            fp.credit
                                        FROM
                                            filtered_projects fp
                                        WHERE
                                            fp.account_id IN %(pass_through_energy_ids)s
                                    )
                                    SELECT
                                        COALESCE(SUM(c.debit), 0) - COALESCE(SUM(c.credit), 0) AS total_pass_through_energy
                                    FROM
                                    pass_through_energy c;
                                    """
            cr.execute(pass_through_energy_qry, {
                'company_id': data["company_id"],
                'pass_through_energy_ids': tuple(
                    data['pass_through_energy_ids']),
                'date_from': data["from"],
                'date_to': data["to"],
                'project_site_id': i['id'],
            })
            pass_through_energy_res = cr.dictfetchall()
            prof_rep.update({
                'pass_through_energy': pass_through_energy_res[0][
                    "total_pass_through_energy"],
            })

            discount_qry = """
                                       WITH filtered_projects AS (
                                        SELECT
                                            aml.debit,
                                            aml.credit,
                                            aml.account_id
                                        FROM
                                            account_move_line aml
                                        JOIN
                                            account_move am ON aml.move_id = am.id
                                        WHERE
                                            aml.project_site_id = %(project_site_id)s
                                            AND am.date <= %(date_to)s
                                            AND am.date >= %(date_from)s
                                            AND am.state = 'posted'
                                            AND aml.company_id = %(company_id)s
                                    ),
                                    discount AS (
                                        SELECT
                                            fp.debit,
                                            fp.credit
                                        FROM
                                            filtered_projects fp
                                        WHERE
                                            fp.account_id IN %(discount_ids)s
                                    )
                                    SELECT
                                        COALESCE(SUM(c.debit), 0) - COALESCE(SUM(c.credit), 0) AS total_discount
                                    FROM
                                    discount c;
                                    """
            cr.execute(discount_qry, {
                'company_id': data["company_id"],
                'discount_ids': tuple(data['discount_ids']),
                'date_from': data["from"],
                'date_to': data["to"],
                'project_site_id': i['id'],
            })
            discount_res = cr.dictfetchall()

            prof_rep.update({
                'discount': discount_res[0]['total_discount'],
            })

            active_sharing_fees_qry = """
                                       WITH filtered_projects AS (
                                        SELECT
                                            aml.debit,
                                            aml.credit,
                                            aml.account_id
                                        FROM
                                            account_move_line aml
                                        JOIN
                                            account_move am ON aml.move_id = am.id
                                        WHERE
                                            aml.project_site_id = %(project_site_id)s
                                            AND am.date <= %(date_to)s
                                            AND am.date >= %(date_from)s
                                            AND am.state = 'posted'
                                            AND aml.company_id = %(company_id)s
                                    ),
                                    active_sharing_fees AS (
                                        SELECT
                                            fp.debit,
                                            fp.credit
                                        FROM
                                            filtered_projects fp
                                        WHERE
                                            fp.account_id IN %(active_sharing_fees_ids)s
                                    )
                                    SELECT
                                        COALESCE(SUM(c.debit), 0) - COALESCE(SUM(c.credit), 0) AS total_active_sharing_fees
                                    FROM
                                    active_sharing_fees c;
                                    """
            cr.execute(active_sharing_fees_qry, {
                'company_id': data["company_id"],
                'active_sharing_fees_ids': tuple(
                    data['active_sharing_fees_ids']),
                'date_from': data["from"],
                'date_to': data["to"],
                'project_site_id': i['id'],
            })
            active_sharing_fees_res = cr.dictfetchall()
            prof_rep.update({
                'active_sharing_fees': active_sharing_fees_res[0][
                    "total_active_sharing_fees"],
            })

            total_revenue = prof_rep['service_revenue'] + prof_rep[
                'investment_revenue'] + prof_rep['colocation'] + prof_rep[
                                'pass_through_energy'] + prof_rep[
                                'active_sharing_fees'] + prof_rep['discount']
            prof_rep.update({
                'total_revenue': total_revenue,
            })

            site_maintenance_qry = """
                                                   WITH filtered_projects AS (
                                                    SELECT
                                                        aml.debit,
                                                        aml.credit,
                                                        aml.account_id
                                                    FROM
                                                        account_move_line aml
                                                    JOIN
                                                        account_move am ON aml.move_id = am.id
                                                    WHERE
                                                        aml.project_site_id = %(project_site_id)s
                                                        AND am.date <= %(date_to)s
                                                        AND am.date >= %(date_from)s
                                                        AND am.state = 'posted'
                                                        AND aml.company_id = %(company_id)s
                                                ),
                                                site_maintenance AS (
                                                    SELECT
                                                        fp.debit,
                                                        fp.credit
                                                    FROM
                                                        filtered_projects fp
                                                    WHERE
                                                        fp.account_id IN %(site_maintenance_ids)s
                                                )
                                                SELECT
                                                    COALESCE(SUM(c.debit), 0) - COALESCE(SUM(c.credit), 0) AS total_site_maintenance
                                                FROM
                                                site_maintenance c;
                                                """
            cr.execute(site_maintenance_qry, {
                'company_id': data["company_id"],
                'site_maintenance_ids': tuple(
                    data['site_maintenance_ids']),
                'date_from': data["from"],
                'date_to': data["to"],
                'project_site_id': i['id'],
            })
            site_maintenance_res = cr.dictfetchall()
            prof_rep.update({
                'site_maintenance': site_maintenance_res[0][
                    "total_site_maintenance"],
            })

            insurance_qry = """
                                                   WITH filtered_projects AS (
                                                    SELECT
                                                        aml.debit,
                                                        aml.credit,
                                                        aml.account_id
                                                    FROM
                                                        account_move_line aml
                                                    JOIN
                                                        account_move am ON aml.move_id = am.id
                                                    WHERE
                                                        aml.project_site_id = %(project_site_id)s
                                                        AND am.date <= %(date_to)s
                                                        AND am.date >= %(date_from)s
                                                        AND am.state = 'posted'
                                                        AND aml.company_id = %(company_id)s
                                                ),
                                                insurance AS (
                                                    SELECT
                                                        fp.debit,
                                                        fp.credit
                                                    FROM
                                                        filtered_projects fp
                                                    WHERE
                                                        fp.account_id IN %(insurance_ids)s
                                                )
                                                SELECT
                                                    COALESCE(SUM(c.debit), 0) - COALESCE(SUM(c.credit), 0) AS total_insurance
                                                FROM
                                                insurance c;
                                                """
            cr.execute(insurance_qry, {
                'company_id': data["company_id"],
                'insurance_ids': tuple(
                    data['insurance_ids']),
                'date_from': data["from"],
                'date_to': data["to"],
                'project_site_id': i['id'],
            })
            insurance_res = cr.dictfetchall()
            prof_rep.update({
                'insurance': insurance_res[0]["total_insurance"],
            })

            energy_cost_qry = """
                                                   WITH filtered_projects AS (
                                                    SELECT
                                                        aml.debit,
                                                        aml.credit,
                                                        aml.account_id
                                                    FROM
                                                        account_move_line aml
                                                    JOIN
                                                        account_move am ON aml.move_id = am.id
                                                    WHERE
                                                        aml.project_site_id = %(project_site_id)s
                                                        AND am.date <= %(date_to)s
                                                        AND am.date >= %(date_from)s
                                                        AND am.state = 'posted'
                                                        AND aml.company_id = %(company_id)s
                                                ),
                                                energy_cost AS (
                                                    SELECT
                                                        fp.debit,
                                                        fp.credit
                                                    FROM
                                                        filtered_projects fp
                                                    WHERE
                                                        fp.account_id IN %(energy_cost_ids)s
                                                )
                                                SELECT
                                                    COALESCE(SUM(c.debit), 0) - COALESCE(SUM(c.credit), 0) AS total_energy_cost
                                                FROM
                                                energy_cost c;
                                                """
            cr.execute(energy_cost_qry, {
                'company_id': data["company_id"],
                'energy_cost_ids': tuple(
                    data['energy_cost_ids']),
                'date_from': data["from"],
                'date_to': data["to"],
                'project_site_id': i['id'],
            })
            energy_cost_res = cr.dictfetchall()

            prof_rep.update({
                'energy_cost': energy_cost_res[0]["total_energy_cost"],
            })

            service_level_credit_qry = """
                                                   WITH filtered_projects AS (
                                                    SELECT
                                                        aml.debit,
                                                        aml.credit,
                                                        aml.account_id
                                                    FROM
                                                        account_move_line aml
                                                    JOIN
                                                        account_move am ON aml.move_id = am.id
                                                    WHERE
                                                        aml.project_site_id = %(project_site_id)s
                                                        AND am.date <= %(date_to)s
                                                        AND am.date >= %(date_from)s
                                                        AND am.state = 'posted'
                                                        AND aml.company_id = %(company_id)s
                                                ),
                                                service_level_credit AS (
                                                    SELECT
                                                        fp.debit,
                                                        fp.credit
                                                    FROM
                                                        filtered_projects fp
                                                    WHERE
                                                        fp.account_id IN %(service_level_credit_ids)s
                                                )
                                                SELECT
                                                    COALESCE(SUM(c.debit), 0) - COALESCE(SUM(c.credit), 0) AS total_service_level_credit
                                                FROM
                                                service_level_credit c;
                                                """
            cr.execute(service_level_credit_qry, {
                'company_id': data["company_id"],
                'service_level_credit_ids': tuple(
                    data['service_level_credit_ids']),
                'date_from': data["from"],
                'date_to': data["to"],
                'project_site_id': i['id'],
            })
            service_level_credit_res = cr.dictfetchall()

            prof_rep.update({
                'service_level_credit': service_level_credit_res[0][
                    "total_service_level_credit"],
            })

            security_qry = """
                                                   WITH filtered_projects AS (
                                                    SELECT
                                                        aml.debit,
                                                        aml.credit,
                                                        aml.account_id
                                                    FROM
                                                        account_move_line aml
                                                    JOIN
                                                        account_move am ON aml.move_id = am.id
                                                    WHERE
                                                        aml.project_site_id = %(project_site_id)s
                                                        AND am.date <= %(date_to)s
                                                        AND am.date >= %(date_from)s
                                                        AND am.state = 'posted'
                                                        AND aml.company_id = %(company_id)s
                                                ),
                                                security AS (
                                                    SELECT
                                                        fp.debit,
                                                        fp.credit
                                                    FROM
                                                        filtered_projects fp
                                                    WHERE
                                                        fp.account_id IN %(security_ids)s
                                                )
                                                SELECT
                                                    COALESCE(SUM(c.debit), 0) - COALESCE(SUM(c.credit), 0) AS total_security
                                                FROM
                                                security c;
                                                """
            cr.execute(security_qry, {
                'company_id': data["company_id"],
                'security_ids': tuple(
                    data['security_ids']),
                'date_from': data["from"],
                'date_to': data["to"],
                'project_site_id': i['id'],
            })
            security_res = cr.dictfetchall()

            prof_rep.update({
                'security': security_res[0]["total_security"],
            })

            total_cost = prof_rep['site_rent'] + prof_rep['site_maintenance'] + \
                         prof_rep['insurance'] + \
                         prof_rep['energy_cost'] + prof_rep['security'] + \
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

            # rou_depreciation = projects.filtered(
            #     lambda x: x.account_id.id in data['rou_depreciation_ids'])
            # total = sum(rou_depreciation.mapped('debit')) - sum(
            #     rou_depreciation.mapped('credit'))

            rou_depreciation_qry = """
                                                   WITH filtered_projects AS (
                                                    SELECT
                                                        aml.debit,
                                                        aml.credit,
                                                        aml.account_id
                                                    FROM
                                                        account_move_line aml
                                                    JOIN
                                                        account_move am ON aml.move_id = am.id
                                                    WHERE
                                                        aml.project_site_id = %(project_site_id)s
                                                        AND am.date <= %(date_to)s
                                                        AND am.date >= %(date_from)s
                                                        AND am.state = 'posted'
                                                        AND aml.company_id = %(company_id)s
                                                ),
                                                rou_depreciation AS (
                                                    SELECT
                                                        fp.debit,
                                                        fp.credit
                                                    FROM
                                                        filtered_projects fp
                                                    WHERE
                                                        fp.account_id IN %(rou_depreciation_ids)s
                                                )
                                                SELECT
                                                    COALESCE(SUM(c.debit), 0) - COALESCE(SUM(c.credit), 0) AS total_rou_depreciation
                                                FROM
                                                rou_depreciation c;
                                                """
            cr.execute(rou_depreciation_qry, {
                'company_id': data["company_id"],
                'rou_depreciation_ids': tuple(
                    data['rou_depreciation_ids']),
                'date_from': data["from"],
                'date_to': data["to"],
                'project_site_id': i['id'],
            })
            rou_depreciation_res = cr.dictfetchall()
            prof_rep.update({
                'rou_depreciation': rou_depreciation_res[0][
                    "total_rou_depreciation"],
            })

            prof_rep.update({
                'fa_depreciation': '',
            })

            lease_finance_cost_qry = """
                                                   WITH filtered_projects AS (
                                                    SELECT
                                                        aml.debit,
                                                        aml.credit,
                                                        aml.account_id
                                                    FROM
                                                        account_move_line aml
                                                    JOIN
                                                        account_move am ON aml.move_id = am.id
                                                    WHERE
                                                        aml.project_site_id = %(project_site_id)s
                                                        AND am.date <= %(date_to)s
                                                        AND am.date >= %(date_from)s
                                                        AND am.state = 'posted'
                                                        AND aml.company_id = %(company_id)s
                                                ),
                                                lease_finance_cost AS (
                                                    SELECT
                                                        fp.debit,
                                                        fp.credit
                                                    FROM
                                                        filtered_projects fp
                                                    WHERE
                                                        fp.account_id IN %(lease_finance_cost_ids)s
                                                )
                                                SELECT
                                                    COALESCE(SUM(c.debit), 0) - COALESCE(SUM(c.credit), 0) AS total_lease_finance_cost
                                                FROM
                                                lease_finance_cost c;
                                                """
            cr.execute(lease_finance_cost_qry, {
                'company_id': data["company_id"],
                'lease_finance_cost_ids': tuple(
                    data['lease_finance_cost_ids']),
                'date_from': data["from"],
                'date_to': data["to"],
                'project_site_id': i['id'],
            })
            lease_finance_cost_res = cr.dictfetchall()
            prof_rep.update({
                'lease_finance_cost': lease_finance_cost_res[0][
                    "total_lease_finance_cost"],
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

        sheet.merge_range('B2:S2', data['Current_months'], main_head)
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
            sheet.write(row_num + 1, col_num + 10, i.get('site_rent'))
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
