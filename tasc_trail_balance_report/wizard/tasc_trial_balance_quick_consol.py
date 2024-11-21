import re
import base64
import io
import xlsxwriter
import calendar
from datetime import datetime, timedelta
from collections import defaultdict
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.misc import get_lang


class TascTrialBalanceQuickConsolReporttWizard(models.TransientModel):
    """ Class for TASC Trial Balance - Quick Consol Report xlsx """
    _name = 'tasc.trial.balance.quick.consol.report.wizard'
    _description = 'TASC Trial Balance - Quick Consol Report '

    date_filter = fields.Selection([('this_month', 'This Month'),
                                    ('this_quarter', 'This Quarter'),
                                    ('this_year', 'This Financial Year'),
                                    ('last_month', 'Last Month'),
                                    ('last_quarter', 'Last Quarter'),
                                    ('last_year', 'Last Financial Year'),
                                    ('custom', 'Custom')
                                    ],
                                   required=True, default='this_month')
    state = fields.Selection([('only_posted', 'Posted Entries Only'),
                              ('include_draft', 'Include Draft'),
                              ],
                             required=True, default='only_posted')

    start_date = fields.Date(string="From Date",
                             default=datetime.today(), required=True)
    end_date = fields.Date(string="To Date",
                           default=datetime.today(), required=True)
    company_id = fields.Many2one('res.company', 'Company',
                                 default=lambda self: self.env.company,
                                 required=True)
    excel_sheet = fields.Binary('Download Report')
    excel_sheet_name = fields.Char(string='Name', size=64)

    def clean_ref(self, ref):
        return re.sub(r'\s*\(.*?\)\s*', '', ref).strip()

    @api.constrains('end_date')
    def onsave_end_date(self):
        if self.end_date < self.start_date:
            raise UserError(
                "The end date should be greater than or equal to start date.")

    def print_report_xlsx(self):
        """ Method for print Cash Burn xlsx report"""
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
            'align': 'left',
            'valign': 'vcenter',
            'font_color': 'black',
            'bg_color': '#c3c6c5',
        })

        TABLE_HEADER_Data = TABLE_HEADER
        TABLE_HEADER_Data.num_format_str = '#,##0.00_);(#,##0.00)'
        STYLE_LINE = workbook.add_format({
            'border': 0,
            'align': 'left',
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
        date_format = workbook.add_format({
            'border': 0,
            'align': 'left',
            'valign': 'vcenter',
            'num_format': 'dd/mm/yyyy'})

        TABLE_data_tolal_line.num_format_str = '#,##0.00'
        STYLE_LINE_Data = STYLE_LINE
        STYLE_LINE_Data.num_format_str = '#,##0.00_);(#,##0.00)'

        if report_data:
            self.add_xlsx_sheet(report_data, workbook, STYLE_LINE_Data,
                                header_format, STYLE_LINE_HEADER, date_format)

        self.excel_sheet_name = 'TASC Trial Balance - Quick Consol Report '
        workbook.close()
        output.seek(0)
        self.excel_sheet = base64.b64encode(output.read())
        self.excel_sheet_name = str(self.excel_sheet_name) + '.xlsx'
        return {
            'type': 'ir.actions.act_url',
            'name': 'TASC Trial Balance - Quick Consol Report ',
            'url': '/web/content/%s/%s/excel_sheet/%s?download=true' % (
                self._name, self.id, self.excel_sheet_name),
            'target': 'new'
        }

    def get_report_data(self):
        """Method to compute TASC Trial Balance - Quick Consol Report """

        company_ids = self.env.companies.ids
        if self.pool['account.account'].name.translate:
            lang = self.env.user.lang or get_lang(self.env).code
            account_name = f"COALESCE(account_account.name->>'{lang}', account_account.name->>'en_US')"
        else:
            account_name = 'account_account.name'

        if self.pool['account.analytic.account'].name.translate:
            lang = self.env.user.lang or get_lang(self.env).code
            cc_name = f"COALESCE(cc.name->>'{lang}', cc.name->>'en_US')"
        else:
            cc_name = 'cc.name'

        conversion_date = self.end_date
        ct_query = self.env['res.currency']._get_query_currency_table(
            company_ids,
            conversion_date)
        if self.state == 'only_posted':
            states = ('posted',)
        else:
            states = ('posted', 'draft', 'to_approve')
        states_str = ','.join(f"'{state}'" for state in states)

        if self.date_filter == 'this_month':
            current_period_start_date = datetime.today().replace(day=1).date()
            _, last_day_of_month = calendar.monthrange(
                current_period_start_date.year, current_period_start_date.month)
            last_date_of_current_period = current_period_start_date.replace(
                day=last_day_of_month)
            initial_balance_end_date = current_period_start_date - timedelta(
                days=1)
            ending_balance_end_date = last_date_of_current_period
            heading_str = 'This Month'
        elif self.date_filter == 'last_month':
            heading_str = 'Last Month'
            current_month_start_date = datetime.today().replace(day=1).date()
            previous_month = (
                    current_month_start_date.month - 1) if current_month_start_date.month > 1 else 12
            previous_year = current_month_start_date.year if current_month_start_date.month > 1 else current_month_start_date.year - 1
            current_period_start_date = current_month_start_date.replace(
                month=previous_month, year=previous_year, day=1)
            # Get the last day of the previous month using monthrange
            _, last_day_of_previous_month = calendar.monthrange(
                current_period_start_date.year, current_period_start_date.month)
            last_date_of_current_period = current_period_start_date.replace(
                day=last_day_of_previous_month)
            initial_balance_end_date = current_period_start_date - timedelta(
                days=1)
            ending_balance_end_date = last_date_of_current_period
        elif self.date_filter == 'this_year':
            heading_str = 'This Year'
            current_year = datetime.today().year
            # Start date of the current year (January 1st)
            current_period_start_date = datetime(current_year, 1, 1).date()
            # End date of the current year (December 31st)
            last_date_of_current_period = datetime(current_year, 12, 31).date()
            initial_balance_end_date = current_period_start_date - timedelta(
                days=1)
            ending_balance_end_date = last_date_of_current_period
        elif self.date_filter == 'last_year':
            heading_str = 'Last Year'
            # Get the previous year
            previous_year = datetime.today().year - 1
            # Start date of the previous year (January 1st)
            current_period_start_date = datetime(previous_year, 1, 1).date()
            # End date of the previous year (December 31st)
            last_date_of_current_period = datetime(previous_year, 12, 31).date()
            initial_balance_end_date = current_period_start_date - timedelta(
                days=1)
            ending_balance_end_date = last_date_of_current_period

        elif self.date_filter == 'this_quarter':
            heading_str = 'This Quarter'

            # Get the current month and year
            current_date = datetime.today().date()
            current_year = current_date.year
            current_month = current_date.month

            # Determine the current quarter's start and end months
            if current_month in [1, 2, 3]:
                quarter_start_month = 1  # Q1
                quarter_end_month = 3
            elif current_month in [4, 5, 6]:
                quarter_start_month = 4  # Q2
                quarter_end_month = 6
            elif current_month in [7, 8, 9]:
                quarter_start_month = 7  # Q3
                quarter_end_month = 9
            else:
                quarter_start_month = 10  # Q4
                quarter_end_month = 12

            # Start date of the current quarter
            current_period_start_date = datetime(current_year,
                                                 quarter_start_month, 1).date()

            # Calculate the last day of the end month of the quarter
            if quarter_end_month == 12:
                # If the quarter ends in December, we need to go to January of the next year
                last_date_of_current_period = datetime(current_year + 1, 1,
                                                       1) - timedelta(days=1)
            else:
                # Otherwise, calculate the last day of the end month normally
                last_date_of_current_period = datetime(current_year,
                                                       quarter_end_month + 1,
                                                       1) - timedelta(days=1)
            last_date_of_current_period = last_date_of_current_period.date()
            initial_balance_end_date = current_period_start_date - timedelta(
                days=1)
            ending_balance_end_date = last_date_of_current_period
        elif self.date_filter == 'last_quarter':
            heading_str = 'Last Quarter'
            # Get the current date
            current_date = datetime.today()
            # Get the current month and year
            current_month = current_date.month
            current_year = current_date.year
            # Determine the previous quarter's start and end months
            if current_month in [1, 2, 3]:
                # Previous quarter is Q4 of the previous year
                previous_quarter_start_month = 10  # October
                previous_quarter_end_month = 12  # December
                previous_year = current_year - 1
            else:
                if current_month in [4, 5, 6]:
                    # Previous quarter is Q1 of the current year
                    previous_quarter_start_month = 1  # January
                    previous_quarter_end_month = 3  # March
                    previous_year = current_year
                elif current_month in [7, 8, 9]:
                    # Previous quarter is Q2 of the current year
                    previous_quarter_start_month = 4  # April
                    previous_quarter_end_month = 6  # June
                    previous_year = current_year
                else:
                    # Previous quarter is Q3 of the current year
                    previous_quarter_start_month = 7  # July
                    previous_quarter_end_month = 9  # September
                    previous_year = current_year
            # Start date of the previous quarter
            current_period_start_date = datetime(previous_year,
                                                 previous_quarter_start_month,
                                                 1).date()

            # Calculate the last day of the previous quarter
            if previous_quarter_end_month == 12:
                last_date_of_current_period = datetime(previous_year + 1, 1,
                                                       1).date() - timedelta(
                    days=1)
            else:
                last_date_of_current_period = datetime(previous_year,
                                                       previous_quarter_end_month + 1,
                                                       1).date() - timedelta(
                    days=1)
            last_date_of_current_period = last_date_of_current_period
            initial_balance_end_date = current_period_start_date - timedelta(
                days=1)
            ending_balance_end_date = last_date_of_current_period
        else:
            current_period_start_date = self.start_date
            last_date_of_current_period = self.end_date
            heading_str = "From : " + str(
                current_period_start_date) + " To : " + str(
                last_date_of_current_period)
            initial_balance_end_date = current_period_start_date - timedelta(
                days=1)
            ending_balance_end_date = last_date_of_current_period
        company_id_str = str(self.company_id.id)
        cost_center = self.env['account.analytic.account'].search([('name','ilike','No Cost Center'),('company_id','=',self.env.company.id)],limit=1)
        if cost_center.code:
            cost_center_code = cost_center.code
        else:
            cost_center_code = ''

        qry = f'''SELECT
                   account_account.id                            AS account_id,
                    {account_name}                               AS account_name,
                    COALESCE({cc_name}, '{cost_center.name}') AS cc_name,
                    account_account.code                            AS code,
                (CASE 
                            WHEN (cc.code IS NULL OR cc.code = '') AND ({cc_name} IS NULL OR {cc_name} = '') THEN '{cost_center_code}'
                            ELSE cc.code
                        END)
                     AS cc_code,
                    'sum'                                                   AS key,
                   MAX(account_move_line.date)                             AS max_date,
                   COALESCE(SUM(account_move_line.amount_currency), 0.0)   AS amount_currency,
                   SUM(ROUND(account_move_line.debit * currency_table.rate, currency_table.precision))   AS debit,
                   SUM(ROUND(account_move_line.credit * currency_table.rate, currency_table.precision))  AS credit,
                   SUM(ROUND(account_move_line.balance * currency_table.rate, currency_table.precision)) AS balance
                   FROM account_move_line
                   LEFT JOIN {ct_query} ON currency_table.company_id = account_move_line.company_id
                   LEFT JOIN account_account ON account_account.id = account_move_line.account_id
                   LEFT JOIN account_analytic_account cc ON cc.id = account_move_line.analytic_account_id
                   WHERE account_move_line.company_id IN ({company_id_str}) AND account_account.account_type != 'equity_unaffected' AND
                   account_move_line.parent_state IN ({states_str}) AND 
                    (
                        CASE 
                            WHEN account_account.code LIKE '4%' OR account_account.code LIKE '5%' THEN 
                                account_move_line.date >= DATE_TRUNC('year', '{str(current_period_start_date)}'::DATE) AND  account_move_line.date >= '{str(current_period_start_date)}' AND 
                         account_move_line.date <= '{str(last_date_of_current_period)}'
                            ELSE 
                                 account_move_line.date >= '{current_period_start_date}' AND 
                         account_move_line.date <= '{str(last_date_of_current_period)}'
                        END
                    )
                   GROUP BY account_account.id,cc.name,cc.code

                '''

        qry2 = f'''SELECT
                       account_account.id                               AS account_id,
                       {account_name}                                   AS account_name,
                    COALESCE({cc_name}, '{cost_center.name}')        AS cc_name,
                       account_account.code                            AS code,
                    (CASE 
                            WHEN (cc.code IS NULL OR cc.code = '') AND ({cc_name} IS NULL OR {cc_name} = '') THEN '{cost_center_code}'
                            ELSE cc.code
                        END)
                     AS cc_code,
                           'initial_balance'                                       AS key,
                      MAX(account_move_line.date)                             AS max_date,
                      COALESCE(SUM(account_move_line.amount_currency), 0.0)   AS amount_currency,
                      SUM(ROUND(account_move_line.debit * currency_table.rate, currency_table.precision))   AS debit,
                      SUM(ROUND(account_move_line.credit * currency_table.rate, currency_table.precision))  AS credit,
                      SUM(ROUND(account_move_line.balance * currency_table.rate, currency_table.precision)) AS balance
                      FROM account_move_line
                      LEFT JOIN {ct_query} ON currency_table.company_id = account_move_line.company_id
                      LEFT JOIN account_account ON account_account.id = account_move_line.account_id
                      LEFT JOIN account_analytic_account cc ON cc.id = account_move_line.analytic_account_id
                      WHERE account_move_line.company_id IN ({company_id_str}) AND 
                      account_account.account_type != 'equity_unaffected' AND
                        account_move_line.parent_state IN ({states_str}) AND
                        (
                        CASE 
                            WHEN account_account.code LIKE '4%' OR account_account.code LIKE '5%' THEN 
                                account_move_line.date >=  DATE_TRUNC('year', '{str(current_period_start_date)}'::DATE) AND  account_move_line.date <= '{str(initial_balance_end_date)}'

                            ELSE 
                                account_move_line.date <= '{str(initial_balance_end_date)}'
                        END
                    )
                      GROUP BY account_account.id,cc.name,cc.code'''

        qry3 = f'''SELECT
                       account_account.id                            AS account_id,
                     {account_name}                                  AS account_name,
                    COALESCE({cc_name}, '{cost_center.name}')        AS cc_name,
                     account_account.code                            AS code,
                      (CASE 
                            WHEN (cc.code IS NULL OR cc.code = '') AND ({cc_name} IS NULL OR {cc_name} = '') THEN '{cost_center_code}'
                            ELSE cc.code
                        END)
                     AS cc_code,
                      'ending_balance'                                       AS key,
                      MAX(account_move_line.date)                             AS max_date,
                      COALESCE(SUM(account_move_line.amount_currency), 0.0)   AS amount_currency,
                      SUM(ROUND(account_move_line.debit * currency_table.rate, currency_table.precision))   AS debit,
                      SUM(ROUND(account_move_line.credit * currency_table.rate, currency_table.precision))  AS credit,
                      SUM(ROUND(account_move_line.balance * currency_table.rate, currency_table.precision)) AS balance
                      FROM account_move_line
                      LEFT JOIN {ct_query} ON currency_table.company_id = account_move_line.company_id
                      LEFT JOIN account_account ON account_account.id = account_move_line.account_id
                      LEFT JOIN account_analytic_account cc ON cc.id = account_move_line.analytic_account_id
                      WHERE account_move_line.company_id IN ({company_id_str}) AND 
                      account_account.account_type != 'equity_unaffected' AND
                    account_move_line.parent_state  IN ({states_str}) AND
                     (
                        CASE 
                            WHEN account_account.code LIKE '4%' OR account_account.code LIKE '5%' THEN 
                                account_move_line.date >=  DATE_TRUNC('year', '{str(current_period_start_date)}'::DATE) AND  account_move_line.date <= '{str(ending_balance_end_date)}'

                            ELSE 
                                account_move_line.date <= '{str(ending_balance_end_date)}'
                        END
                    )
                    GROUP BY account_account.id,cc.name,cc.code'''

        qry_u1 = f'''SELECT
                           'sum'                                                   AS key,
                           MAX(account_move_line.date)                             AS max_date,
                           COALESCE(SUM(account_move_line.amount_currency), 0.0)   AS amount_currency,
                           SUM(ROUND(account_move_line.debit * currency_table.rate, currency_table.precision))   AS debit,
                           SUM(ROUND(account_move_line.credit * currency_table.rate, currency_table.precision))  AS credit,
                           SUM(ROUND(account_move_line.balance * currency_table.rate, currency_table.precision)) AS balance
                           FROM account_move_line
                           LEFT JOIN {ct_query} ON currency_table.company_id = account_move_line.company_id
                           LEFT JOIN account_account ON account_account.id = account_move_line.account_id
                           WHERE account_move_line.company_id IN ({company_id_str}) AND account_account.account_type != 'equity_unaffected' AND
                           account_move_line.parent_state IN ({states_str}) AND 
                            (
                                CASE 
                                    WHEN account_account.code LIKE '4%' OR account_account.code LIKE '5%' THEN 
                                        account_move_line.date >= DATE_TRUNC('year', '{str(current_period_start_date)}'::DATE) AND  account_move_line.date >= '{str(current_period_start_date)}' AND 
                                 account_move_line.date <= '{str(last_date_of_current_period)}'
                                    ELSE 
                                         account_move_line.date >= '{current_period_start_date}' AND 
                                 account_move_line.date <= '{str(last_date_of_current_period)}'
                                END
                            )
                        '''

        qry2_u = f'''SELECT

                               'initial_balance'                                       AS key,
                              MAX(account_move_line.date)                             AS max_date,
                              COALESCE(SUM(account_move_line.amount_currency), 0.0)   AS amount_currency,
                              SUM(ROUND(account_move_line.debit * currency_table.rate, currency_table.precision))   AS debit,
                              SUM(ROUND(account_move_line.credit * currency_table.rate, currency_table.precision))  AS credit,
                              SUM(ROUND(account_move_line.balance * currency_table.rate, currency_table.precision)) AS balance
                              FROM account_move_line
                              LEFT JOIN {ct_query} ON currency_table.company_id = account_move_line.company_id
                              LEFT JOIN account_account ON account_account.id = account_move_line.account_id

                              WHERE account_move_line.company_id IN ({company_id_str}) AND 
                              account_account.account_type != 'equity_unaffected' AND
                                account_move_line.parent_state IN ({states_str}) AND
                                (
                                CASE 
                                    WHEN account_account.code LIKE '4%' OR account_account.code LIKE '5%' THEN 
                                        account_move_line.date >=  DATE_TRUNC('year', '{str(current_period_start_date)}'::DATE) AND  account_move_line.date <= '{str(initial_balance_end_date)}'

                                    ELSE 
                                        account_move_line.date <= '{str(initial_balance_end_date)}'
                                END
                            )
                            '''

        qry3_u = f'''SELECT

                              'ending_balance'                                       AS key,
                              MAX(account_move_line.date)                             AS max_date,
                              COALESCE(SUM(account_move_line.amount_currency), 0.0)   AS amount_currency,
                              SUM(ROUND(account_move_line.debit * currency_table.rate, currency_table.precision))   AS debit,
                              SUM(ROUND(account_move_line.credit * currency_table.rate, currency_table.precision))  AS credit,
                              SUM(ROUND(account_move_line.balance * currency_table.rate, currency_table.precision)) AS balance
                              FROM account_move_line
                              LEFT JOIN {ct_query} ON currency_table.company_id = account_move_line.company_id
                              LEFT JOIN account_account ON account_account.id = account_move_line.account_id
                              WHERE account_move_line.company_id IN ({company_id_str}) AND 
                              account_account.account_type != 'equity_unaffected' AND
                            account_move_line.parent_state  IN ({states_str}) AND
                             (
                                CASE 
                                    WHEN account_account.code LIKE '4%' OR account_account.code LIKE '5%' THEN 
                                        account_move_line.date >=  DATE_TRUNC('year', '{str(current_period_start_date)}'::DATE) AND  account_move_line.date <= '{str(ending_balance_end_date)}'

                                    ELSE 
                                        account_move_line.date <= '{str(ending_balance_end_date)}'
                                END
                            )
                           '''
        combined_query_u = f'''{qry_u1} 
                                 UNION ALL 
                                 {qry2_u}
                                 UNION ALL 
                                 {qry3_u}   
                                 '''
        self._cr.execute(combined_query_u)
        res_u = self._cr.dictfetchall()
        combined_query = f'''{qry} 
                             UNION ALL 
                             {qry2}
                             UNION ALL 
                             {qry3}   
                             ORDER BY
                             code'''
        self._cr.execute(combined_query)
        res = self._cr.dictfetchall()
        grouped_data = defaultdict(lambda: {'total_initial_amount': 0.0,'total_current_amount': 0.0,'total_ending_amount': 0.0,'cost_center_code':''})
        for entry in res:
            key = (entry['account_id'], entry['account_name'], entry['cc_name'],
                   entry['code'])

            grouped_data[key]['cost_center_code'] = entry["cc_code"]

            if key in grouped_data:
                if 'balance' in entry and entry['balance'] is not None:
                    if entry.get('key') == 'initial_balance':
                        grouped_data[key]['total_initial_amount'] += entry['balance']
                    elif entry.get('key') == 'ending_balance':
                        grouped_data[key]['total_ending_amount'] += entry[
                            'balance']
                    else:
                        grouped_data[key]['total_current_amount'] += entry[
                            'balance']
            else:
                # Key does not exist: Add the entry and initialize total_amount
                if entry.get('key') == 'initial_balance':
                    grouped_data[key]['total_initial_amount'] = entry[
                        'balance'] if 'balance' in entry and entry[
                        'balance'] is not None else 0.0
                elif entry.get('key') == 'ending_balance':
                    grouped_data[key]['total_ending_amount'] = entry[
                        'balance'] if 'balance' in entry and entry[
                        'balance'] is not None else 0.0
                else:
                    grouped_data[key]['total_current_amount'] = entry[
                        'balance'] if 'balance' in entry and entry[
                        'balance'] is not None else 0.0

        grouped_data = dict(grouped_data)
        data = {'report_data': grouped_data,
                'res_u': res_u,
                'heading_str': heading_str,
                'cost_center_id':cost_center}

        return data

    def add_xlsx_sheet(self, data, workbook, STYLE_LINE_Data,
                       header_format, STYLE_LINE_HEADER, date_format):
        """ Method to add datas to the TASC Trial Balance - Quick Consol Report """
        self.ensure_one()
        worksheet = workbook.add_worksheet(
            _('TASC Trial Balance - Quick Consol Report '))
        lang = self.env.user.lang
        if lang.startswith('ar_'):
            worksheet.right_to_left()

        row = 0
        col = 0
        heading = data["heading_str"]

        worksheet.merge_range(row, row, col, col + 7,
                              _('TASC Trial Balance - Quick Consol Report '),
                              STYLE_LINE_HEADER)
        row += 1
        col = 0
        worksheet.write(row, col, _('Account Code'), header_format)
        col += 1
        worksheet.write(row, col, _('Account'), header_format)
        col += 1
        worksheet.write(row, col, _('Cost Center'), header_format)
        col += 1
        worksheet.write(row, col, _('Cost Center Description'), header_format)
        col += 1
        worksheet.write(row, col, _('Initial Balance'), header_format)
        col += 1
        worksheet.write(row, col, _(heading), header_format)
        col += 1
        worksheet.write(row, col, _('End Balance'), header_format)
        col+=1
        worksheet.write(row, col, _('Combination'), header_format)
        row += 1
        report_data = data["report_data"]
        cost_center_id = data["cost_center_id"]
        candidates_account_ids = self.env['account.account'].search(
            [('account_type', '=', 'equity_unaffected'),
             ('company_id', '=', self.company_id.id)])
        project_site = self.env['account.analytic.account'].search([('name','ilike','No Project'),('company_id','=',self.env.company.id)],limit=1)
        for (account_id, account_name, cc_name,
              code), entries in report_data.items():
            col = 0
            worksheet.write(row, col, (account_id, account_name, cc_name,
                                        code)[3],
                            STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, (account_id, account_name, cc_name,
                                        code)[1],
                            STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, (account_id, account_name, cc_name,
                                        code)[2],
                            STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, entries["cost_center_code"] if  entries["cost_center_code"] else '',
                            STYLE_LINE_Data)
            if  entries["total_initial_amount"]:
                col = 4
                worksheet.write(row, col, entries["total_initial_amount"],
                                STYLE_LINE_Data)
            if entries["total_current_amount"]:
                col = 5
                worksheet.write(row, col,  entries["total_current_amount"],
                                STYLE_LINE_Data)
            if entries["total_ending_amount"]:
                col = 6
                worksheet.write(row, col,  entries["total_ending_amount"],
                                STYLE_LINE_Data)
            col=7
            code = (account_id, account_name, cc_name,
                                        code)[3]
            worksheet.write(row, col,(account_id, account_name, cc_name,
                                        code)[3]+"|"+(account_id, account_name, cc_name,
                                        code)[2]+"|"+ project_site.name ,
                            STYLE_LINE_Data)
            row += 1
        res_u = data["res_u"]
        balances = {}

        for entry in res_u:
            if entry['key'] in ['ending_balance', 'initial_balance', 'sum']:
                balances[entry['key']] = entry['balance']

        for c_account in candidates_account_ids:
            col = 0
            worksheet.write(row, col, c_account.code,
                            STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, c_account.name,
                            STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, cost_center_id.name if cost_center_id else '',
                            STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, cost_center_id.code if cost_center_id else '',
                            STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, balances["initial_balance"] * -1,
                            STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, balances['sum'] * -1,
                            STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, balances['ending_balance'] * -1,
                            STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, c_account.code +"|"+cost_center_id.name+"|"+project_site.name,
                            STYLE_LINE_Data)
        row += 1