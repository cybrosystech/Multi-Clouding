import io

import xlsxwriter

from odoo import models, api, _, fields
from odoo.tools import date_utils
from odoo.tools.safe_eval import json

assets_sum = []
assets_budget_sum = []
liabilities_sum = []
liabilities_budget = []
shareholders_equity_sum = []
shareholders_equity_budget = []
report_json_bs = []
from datetime import datetime, date, timedelta


class TascBalanceSheetReport(models.AbstractModel):
    _name = 'tasc.balance.sheet.report'

    def _get_templates(self):
        return {
            'main_template': 'tasc_pf_bs_report.tasc_pf_bs_html_content_view',
            'main_table_header_template': 'account_reports.main_table_header',
            'line_template': 'cash_flow_statement_report.line_template_cash_flow',
            'footnotes_template': 'account_reports.footnotes_template',
            'budget_analysis_search_view': 'tasc_pf_bs_report.tasc_pf_bs_search_view',
        }

    @api.model
    def get_button_balance_sheet(self):
        return [
            {'name': _('Export (XLSX)'), 'sequence': 2,
             'action': 'print_xlsx_tasc_balance_sheet',
             'file_export_type': _('XLSX')},
        ]

    def get_company_filter(self, options):
        if 'multi_company' not in list(options.keys()):
            options['multi-company'] = False
        else:
            if options['multi_company'] == 'all-companies':
                options['multi-company'] = True

    def get_cash_flow_information(self, filter):
        options = self.env['cash.flow.statement']._get_cashflow_options(filter)
        self.get_company_filter(options)
        info = {
            'options': options,
            'main_html': self.get_html_content(options),
            'searchview_html': self.env['ir.ui.view']._render_template(
                self._get_templates().get('budget_analysis_search_view', ),
                values={'options': options}),
            'buttons': self.get_button_balance_sheet()
        }
        return info

    def _clear_list_values(self):
        assets_sum.clear()
        assets_budget_sum.clear()
        liabilities_sum.clear()
        liabilities_budget.clear()
        shareholders_equity_sum.clear()
        shareholders_equity_budget.clear()

    def get_html_content(self, options):
        self._clear_list_values()
        templates = self._get_templates()
        template = templates['main_template']
        values = {'model': self}
        header = self._get_header()
        lines = self._get_balance_sheet_line(options)
        report_json_bs.clear()
        report_json_bs.append(lines)
        values['lines'] = {'lines': lines, 'header': header}
        html = self.env.ref(template)._render(values)
        return html

    def _get_header(self):
        return ['Account', 'Balance', 'Budget', 'Variance']

    def _get_balance_sheet_line(self, options):
        date_to_demo = fields.Date.to_date(options['date']['date_to'])
        budget_date = date(day=1, month=date_to_demo.month,
                           year=date_to_demo.year)
        balance_sheet_lines = []
        states_args = """ parent_state = 'posted'"""
        if options['entry'] != 'posted':
            states_args = """ parent_state in ('posted', 'draft')"""
        query = '''select coalesce((sum(journal_item.debit) - sum(journal_item.credit)), 0) total,
                            account.name, account.code, account.id, account.group_id
                            from account_move_line as journal_item
                            left join account_account as account on journal_item.account_id = account.id
                            '''
        query_budget = '''select coalesce(sum(budget_line.planned_amount), 0) as planned,
                                  account.name, account.code from crossovered_budget_lines as budget_line
                                  left join account_budget_post as budgetary on 
                                  budget_line.general_budget_id = budgetary.id
                                  left join account_budget_rel as rel on budgetary.id = rel.budget_id
                                  left join account_account as account on rel.account_id = account.id
                                '''
        bs_lines = [
            {
                'id': 'assets',
                'name': 'Assets',
                'columns': [],
                'child_lines': [
                    {
                        'id': 'current_assets',
                        'name': 'Current Assets',
                        'columns': [
                            {'name': round(current_assets, 2),
                             'class': 'number'}
                            for
                            current_assets in
                            self._get_current_assets(states_args, query,
                                                     query_budget,
                                                     options,
                                                     balance_sheet_lines,
                                                     budget_date,
                                                     dict_id='current_assets',
                                                     )],
                        'account_lines': balance_sheet_lines
                    },
                    {
                        'id': 'non_current_assets',
                        'name': 'Non Current Assets',
                        'columns': [
                            {'name': round(non_current_assets, 2),
                             'class': 'number'} for
                            non_current_assets in
                            self._get_non_current_assets(states_args, query,
                                                         query_budget,
                                                         options,
                                                         balance_sheet_lines,
                                                         budget_date,
                                                         dict_id='non_current_assets')],
                        'account_lines': balance_sheet_lines

                    }],
                'account_lines': ''
            },
            {
                'id': 'liabilities',
                'name': 'Liabilities',
                'columns': [],
                'child_lines': [
                    {
                        'id': 'current_liabilities',
                        'name': 'Current liabilities',
                        'columns': [
                            {'name': round(current_liabilities, 2),
                             'class': 'number'} for
                            current_liabilities in
                            self._get_current_liabilities(states_args, query,
                                                          query_budget,
                                                          options,
                                                          balance_sheet_lines,
                                                          budget_date,
                                                          dict_id='current_liabilities')],
                        'account_lines': balance_sheet_lines
                    },
                    {
                        'id': 'non_current_liabilities',
                        'name': 'Non-Current liabilities',
                        'columns': [
                            {'name': round(non_current_liabilities, 2),
                             'class': 'number'} for
                            non_current_liabilities in
                            self._get_non_current_liabilities(states_args,
                                                              query,
                                                              query_budget,
                                                              options,
                                                              balance_sheet_lines,
                                                              budget_date,
                                                              dict_id='non_current_liabilities')],
                        'account_lines': balance_sheet_lines
                    },
                ],
                'account_lines': ''
            },
            {
                'id': 'shareholders_equity',
                'name': 'Shareholders Equity',
                'columns': [],
                'child_lines': [
                    {
                        'id': 'equity',
                        'name': 'Equity',
                        'columns': [
                            {'name': round(equity, 2),
                             'class': 'number'} for
                            equity in
                            self._get_equity(states_args,
                                             query,
                                             query_budget,
                                             options, balance_sheet_lines,
                                             budget_date,
                                             dict_id='equity')],
                        'account_lines': balance_sheet_lines
                    },
                    {
                        'id': 'current_year_profit',
                        'name': 'Current Year Profit',
                        'columns': [
                            {'name': round(current_year_profit, 2),
                             'class': 'number'} for
                            current_year_profit in
                            self._get_current_year_profit(states_args,
                                                          query,
                                                          query_budget,
                                                          options,
                                                          balance_sheet_lines,
                                                          dict_id='current_year_profit')],
                        'account_lines': balance_sheet_lines
                    },
                    {
                        'id': 'unallocated_earning',
                        'name': 'Unallocated Earning',
                        'columns': [
                            {'name': round(unallocated_earning, 2),
                             'class': 'number'} for
                            unallocated_earning in
                            self._get_unallocated_earning(states_args,
                                                          query,
                                                          query_budget,
                                                          options,
                                                          balance_sheet_lines,
                                                          dict_id='unallocated_earning')],
                        'account_lines': balance_sheet_lines
                    },
                ],
                'account_lines': ''
            },
            {
                'id': 'total_shareholders_equity',
                'name': 'Total Shareholders Equity',
                'columns': [
                    {'name': round(abs(sum(shareholders_equity_sum)), 2),
                     'class': 'number'},
                    {'name': round(sum(shareholders_equity_budget), 2),
                     'class': 'number'},
                    {'name': round(
                        sum(shareholders_equity_sum) - sum(
                            shareholders_equity_budget),
                        2),
                        'class': 'number'}
                ],
                'child_lines': '',
                'account_lines': ''
            },
            {
                'id': 'total_tl_tse',
                'name': 'Total Liability & Shareholder Equity',
                'columns': [{'name': round(abs(
                    sum(liabilities_sum) + sum(shareholders_equity_sum)), 2),
                    'class': 'number'},
                    {'name': round(sum(liabilities_budget) + sum(
                        shareholders_equity_budget), 2),
                     'class': 'number'},
                    {'name': round(
                        (sum(liabilities_sum) + sum(
                            shareholders_equity_sum)) - (
                                sum(liabilities_budget) + sum(
                            shareholders_equity_budget)),
                        2),
                        'class': 'number'}],
                'child_lines': '',
                'account_lines': ''
            }
        ]
        bs_lines[0]['columns'] = [{'name': round(sum(assets_sum), 2),
                                   'class': 'number'},
                                  {'name': round(sum(assets_budget_sum), 2),
                                   'class': 'number'},
                                  {'name': round(
                                      sum(assets_sum) - sum(assets_budget_sum),
                                      2),
                                      'class': 'number'}]
        bs_lines[1]['columns'] = [{'name': abs(round(sum(liabilities_sum), 2)),
                                   'class': 'number'},
                                  {'name': round(sum(liabilities_budget), 2),
                                   'class': 'number'},
                                  {'name': round(
                                      sum(liabilities_sum) - sum(
                                          liabilities_budget),
                                      2),
                                      'class': 'number'}]
        bs_lines[2]['columns'] = [
            {'name': abs(round(sum(shareholders_equity_sum), 2)),
             'class': 'number'},
            {'name': round(sum(shareholders_equity_budget), 2),
             'class': 'number'},
            {'name': round(
                sum(shareholders_equity_sum) - sum(
                    shareholders_equity_budget),
                2),
                'class': 'number'}]
        return bs_lines

    def _get_current_assets(self, states_args, query, query_budget, options,
                            balance_sheet_lines, budget_date, dict_id):
        self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                    and journal_item.company_id in %(company_ids)s
                                                    and journal_item.date <= %(to_date)s
                                                    and {states_args}
                                                    group by account.name, account.code, account.id, account.group_id
                                                    '''.format(
            states_args=states_args),
                            {'to_date': options['date']['date_to'],
                             'code_start': '110000', 'code_end': '119999',
                             'company_ids': tuple([self.env.company.id] if options['multi-company'] is False else self.env.companies.ids)})
        current_assets = self.env.cr.dictfetchall()
        self.env.cr.execute(query_budget + '''where account.code between %(code_start)s and %(code_end)s
                                                            and budget_line.company_id in %(company_ids)s
                                                            and budget_line.date_from >= %(from_date)s 
                                                            and budget_line.date_to <= %(to_date)s
                                                            group by account.name, account.code
                                                            ''',
                            {'from_date': budget_date,
                             'to_date': options['date']['date_to'],
                             'code_start': '110000', 'code_end': '119999',
                             'company_ids': tuple([self.env.company.id] if options['multi-company'] is False else self.env.companies.ids)})
        current_assets_budget = self.env.cr.dictfetchall()
        self._arrange_account_budget_line(balance_sheet_lines,
                                          current_assets,
                                          current_assets_budget, dict_id)
        current_assets_total = sum(
            list(map(lambda x: x['total'], current_assets)))
        current_assets_budget_total = sum(list(
            map(lambda x: x['planned'], current_assets_budget)))
        assets_sum.append(current_assets_total)
        assets_budget_sum.append(current_assets_budget_total)
        return [current_assets_total, current_assets_budget_total,
                current_assets_total - current_assets_budget_total]

    def _get_non_current_assets(self, states_args, query, query_budget,
                                options, balance_sheet_lines, budget_date, dict_id):
        self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                    and journal_item.company_id in %(company_ids)s
                                                    and journal_item.date <= %(to_date)s
                                                    and {states_args}
                                                    group by account.name, account.code, account.id, account.group_id
                                                    '''.format(
            states_args=states_args),
                            {'to_date': options['date']['date_to'],
                             'code_start': '120000', 'code_end': '129999',
                             'company_ids': tuple([self.env.company.id] if options['multi-company'] is False else self.env.companies.ids)})
        non_current_assets = self.env.cr.dictfetchall()
        self.env.cr.execute(query_budget + '''where account.code between %(code_start)s and %(code_end)s
                                                            and budget_line.company_id in %(company_ids)s
                                                            and budget_line.date_from >= %(from_date)s 
                                                            and budget_line.date_to <= %(to_date)s
                                                            group by account.name, account.code
                                                            ''',
                            {'from_date': budget_date,
                             'to_date': options['date']['date_to'],
                             'code_start': '120000', 'code_end': '129999',
                             'company_ids': tuple([self.env.company.id] if options['multi-company'] is False else self.env.companies.ids)})
        non_current_assets_budget = self.env.cr.dictfetchall()
        self._arrange_account_budget_line(balance_sheet_lines,
                                          non_current_assets,
                                          non_current_assets_budget, dict_id)
        non_current_assets_total = sum(
            list(map(lambda x: x['total'], non_current_assets)))
        non_current_assets_budget_total = sum(list(
            map(lambda x: x['planned'], non_current_assets_budget)))
        assets_sum.append(non_current_assets_total)
        assets_budget_sum.append(non_current_assets_budget_total)
        return [non_current_assets_total, non_current_assets_budget_total,
                non_current_assets_total - non_current_assets_budget_total]

    def _get_current_liabilities(self, states_args, query, query_budget,
                                 options, balance_sheet_lines, budget_date, dict_id):
        self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                        and journal_item.company_id in %(company_ids)s
                                                        and journal_item.date <= %(to_date)s
                                                        and {states_args}
                                                        group by account.name, account.code, account.id, account.group_id
                                                        '''.format(
            states_args=states_args),
                            {'to_date': options['date']['date_to'],
                             'code_start': '210000', 'code_end': '219999',
                             'company_ids': tuple([self.env.company.id] if options['multi-company'] is False else self.env.companies.ids)})
        current_liabilities = self.env.cr.dictfetchall()
        self.env.cr.execute(query_budget + '''where account.code between %(code_start)s and %(code_end)s
                                                                and budget_line.company_id in %(company_ids)s
                                                                and budget_line.date_from >= %(from_date)s 
                                                                and budget_line.date_to <= %(to_date)s
                                                                group by account.name, account.code
                                                                ''',
                            {'from_date': budget_date,
                             'to_date': options['date']['date_to'],
                             'code_start': '210000', 'code_end': '219999',
                             'company_ids': tuple([self.env.company.id] if options['multi-company'] is False else self.env.companies.ids)})
        current_liabilities_budget = self.env.cr.dictfetchall()
        self._arrange_account_budget_line(balance_sheet_lines,
                                          current_liabilities,
                                          current_liabilities_budget, dict_id, abs_of=True)
        current_liabilities_total = sum(
            list(map(lambda x: x['total'], current_liabilities)))
        current_liabilities_budget_total = sum(list(
            map(lambda x: x['planned'], current_liabilities_budget)))
        liabilities_sum.append(current_liabilities_total)
        liabilities_budget.append(current_liabilities_budget_total)
        return [abs(current_liabilities_total),
                current_liabilities_budget_total,
                current_liabilities_total - current_liabilities_budget_total]

    def _get_non_current_liabilities(self, states_args, query, query_budget,
                                     options, balance_sheet_lines, budget_date, dict_id):
        self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                            and journal_item.company_id in %(company_ids)s
                                                            and journal_item.date <= %(to_date)s
                                                            and {states_args}
                                                            group by account.name, account.code, account.id, account.group_id
                                                            '''.format(
            states_args=states_args),
                            {'to_date': options['date']['date_to'],
                             'code_start': '220000', 'code_end': '299999',
                             'company_ids': tuple([self.env.company.id] if options['multi-company'] is False else self.env.companies.ids)})
        non_current_liabilities = self.env.cr.dictfetchall()
        self.env.cr.execute(query_budget + '''where account.code between %(code_start)s and %(code_end)s
                                                                    and budget_line.company_id in %(company_ids)s
                                                                    and budget_line.date_from >= %(from_date)s 
                                                                    and budget_line.date_to <= %(to_date)s
                                                                    group by account.name, account.code
                                                                    ''',
                            {'from_date': budget_date,
                             'to_date': options['date']['date_to'],
                             'code_start': '220000', 'code_end': '299999',
                             'company_ids': tuple([self.env.company.id] if options['multi-company'] is False else self.env.companies.ids)})
        non_current_liabilities_budget = self.env.cr.dictfetchall()
        self._arrange_account_budget_line(balance_sheet_lines,
                                          non_current_liabilities,
                                          non_current_liabilities_budget,
                                          dict_id, abs_of=True)
        non_current_liabilities_total = sum(
            list(map(lambda x: x['total'], non_current_liabilities)))
        non_current_liabilities_budget_total = sum(list(
            map(lambda x: x['planned'], non_current_liabilities_budget)))
        liabilities_sum.append(non_current_liabilities_total)
        liabilities_budget.append(non_current_liabilities_budget_total)
        return [abs(non_current_liabilities_total),
                non_current_liabilities_budget_total,
                non_current_liabilities_total -
                non_current_liabilities_budget_total]

    def _get_equity(self, states_args, query, query_budget,
                    options, balance_sheet_lines, budget_date, dict_id):
        self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                            and journal_item.company_id in %(company_ids)s
                                                            and journal_item.date <= %(to_date)s
                                                            and {states_args}
                                                            group by account.name, account.code, account.id, account.group_id
                                                            '''.format(
            states_args=states_args),
                            {'to_date': options['date']['date_to'],
                             'code_start': '310000', 'code_end': '399999',
                             'company_ids': tuple([self.env.company.id] if options['multi-company'] is False else self.env.companies.ids)})
        equity = self.env.cr.dictfetchall()
        self.env.cr.execute(query_budget + '''where account.code between %(code_start)s and %(code_end)s
                                                                    and budget_line.company_id in %(company_ids)s
                                                                    and budget_line.date_from >= %(from_date)s 
                                                                    and budget_line.date_to <= %(to_date)s
                                                                    group by account.name, account.code
                                                                    ''',
                            {'from_date': budget_date,
                             'to_date': options['date']['date_to'],
                             'code_start': '310000', 'code_end': '399999',
                             'company_ids': tuple([self.env.company.id] if options['multi-company'] is False else self.env.companies.ids)})
        equity_budget = self.env.cr.dictfetchall()
        self._arrange_account_budget_line(balance_sheet_lines,
                                          equity,
                                          equity_budget,
                                          dict_id, abs_of=True)
        equity_total = sum(
            list(map(lambda x: x['total'], equity)))
        equity_budget_budget_total = sum(list(
            map(lambda x: x['planned'], equity_budget)))
        shareholders_equity_sum.append(equity_total)
        shareholders_equity_budget.append(equity_budget_budget_total)
        return [abs(equity_total), equity_budget_budget_total,
                equity_total - equity_budget_budget_total]

    def _get_current_year_profit(self, states_args, query, query_budget,
                                 options, balance_sheet_lines, dict_id):

        date_from = datetime.strptime(options['date']['date_to'],
                                      "%Y-%m-%d")
        static_date = date(day=1, month=1, year=date_from.year)
        self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                            and journal_item.company_id in %(company_ids)s
                                                            and journal_item.date >= %(from_date)s
                                                            and journal_item.date <= %(to_date)s
                                                            and {states_args}
                                                            group by account.name, account.code, account.id, account.group_id
                                                            '''.format(
            states_args=states_args),
                            {'to_date': options['date']['date_to'],
                             'from_date': options['date']['date_from'],
                             'code_start': '400000', 'code_end': '899999',
                             'company_ids': tuple([self.env.company.id] if options['multi-company'] is False else self.env.companies.ids)})
        current_year_profit = self.env.cr.dictfetchall()
        # current_year_profit_account = self._get_current_year_profit_account(
        #     static_date,
        #     states_args, query, query_budget,
        #     options)
        self.env.cr.execute(query_budget + '''where account.code between %(code_start)s and %(code_end)s
                                                                    and budget_line.company_id in %(company_ids)s
                                                                    and budget_line.date_from >= %(from_date)s 
                                                                    and budget_line.date_to <= %(to_date)s
                                                                    group by account.name, account.code
                                                                    ''',
                            {'from_date': static_date,
                             'to_date': options['date']['date_to'],
                             'code_start': '400000', 'code_end': '899999',
                             'company_ids': tuple([self.env.company.id] if options['multi-company'] is False else self.env.companies.ids)})
        current_year_profit_budget = self.env.cr.dictfetchall()
        # current_year_profit += current_year_profit_account
        self._arrange_account_budget_line(balance_sheet_lines,
                                          current_year_profit,
                                          current_year_profit_budget,
                                          dict_id, abs_of='CU')
        current_year_profit_total = sum(
            list(map(lambda x: x['total'], current_year_profit)))
        current_year_profit_budget_total = sum(list(
            map(lambda x: x['planned'], current_year_profit_budget)))

        # current_year_profit[0].update({
        #     'total': current_year_profit[0]['total'] +
        #              current_year_profit_account[0]
        # })
        shareholders_equity_sum.append(current_year_profit_total)
        shareholders_equity_budget.append(current_year_profit_budget_total)
        return [-1 * current_year_profit_total, current_year_profit_budget_total,
                current_year_profit_total -
                current_year_profit_budget_total]

    def _get_unallocated_earning(self, states_args, query, query_budget,
                                 options, balance_sheet_lines, dict_id):
        date_to = datetime.strptime(options['date']['date_from'],
                                      "%Y-%m-%d") - timedelta(days=1)
        static_date = date(day=1, month=1, year=date_to.year)
        self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                            and journal_item.company_id in %(company_ids)s
                                                            and journal_item.date >= %(from_date)s
                                                            and journal_item.date <= %(to_date)s
                                                            and {states_args}
                                                            group by account.name, account.code, account.id, account.group_id
                                                            '''.format(
            states_args=states_args),
                            {'from_date': static_date,
                             'to_date': date_to,
                             'code_start': '400000', 'code_end': '899999',
                             'company_ids': tuple([self.env.company.id] if options['multi-company'] is False else self.env.companies.ids)})
        unallocated_earning = self.env.cr.dictfetchall()
        if options['date_filter'] in ['this_year', 'last_year']:
            for unallocated in unallocated_earning:
                unallocated['total'] = 0
        print('unallocated_earning', unallocated_earning)
        # unallocated_earning_account = self._get_unallocated_earning_account(
        #     static_date,
        #     states_args, query, query_budget,
        #     options)
        self.env.cr.execute(query_budget + '''where account.code between %(code_start)s and %(code_end)s
                                                                    and budget_line.company_id in %(company_ids)s
                                                                    and budget_line.date_from >= %(from_date)s 
                                                                    and budget_line.date_to <= %(to_date)s
                                                                    group by account.name, account.code
                                                                    ''',
                            {'from_date': options['date']['date_from'],
                             'to_date': options['date']['date_to'],
                             'code_start': '420000', 'code_end': '429999',
                             'company_ids': tuple([self.env.company.id] if options['multi-company'] is False else self.env.companies.ids)})
        unallocated_earning_budget = self.env.cr.dictfetchall()
        # unallocated_earning += unallocated_earning_account
        self._arrange_account_budget_line(balance_sheet_lines,
                                          unallocated_earning,
                                          unallocated_earning_budget,
                                          dict_id, abs_of='CU')
        unallocated_earning_total = sum(
            list(map(lambda x: x['total'], unallocated_earning)))
        unallocated_earning_budget_total = sum(list(
            map(lambda x: x['planned'], unallocated_earning_budget)))
        # unallocated_earning[0].update({
        #     'total': unallocated_earning[0]['total'] +
        #              unallocated_earning_account[0]
        # })
        shareholders_equity_sum.append(unallocated_earning_total)
        shareholders_equity_budget.append(unallocated_earning_budget_total)
        return [-1 * unallocated_earning_total,
                unallocated_earning_budget_total,
                unallocated_earning_total -
                unallocated_earning_budget_total]

    def _get_current_year_profit_account(self, static_date, states_args, query,
                                         query_budget,
                                         options):
        self.env.cr.execute(query + '''where account.code = %(code)s
                                                                    and journal_item.company_id in %(company_ids)s
                                                                    and journal_item.date >= %(from_date)s
                                                                    and journal_item.date <= %(to_date)s
                                                                    and {states_args}
                                                                    group by account.name, account.code, account.id, account.group_id
                                                                    '''.format(
            states_args=states_args),
                            {'to_date': options['date']['date_to'],
                             'from_date': static_date,
                             'code': '999999',
                             'company_ids': tuple([self.env.company.id] if options['multi-company'] is False else self.env.companies.ids)})
        current_year_profit_account = self.env.cr.dictfetchall()
        return current_year_profit_account

    def _get_unallocated_earning_account(self, static_date, states_args, query,
                                         query_budget,
                                         options):
        self.env.cr.execute(query + '''where account.code = %(code)s
                                                                    and journal_item.company_id in %(company_ids)s
                                                                    and journal_item.date <= %(to_date)s
                                                                    and {states_args}
                                                                    group by account.name, account.code, account.id, account.group_id
                                                                    '''.format(
            states_args=states_args),
                            {'to_date': static_date,
                             'code': '999999',
                             'company_ids': tuple([self.env.company.id] if options['multi-company'] is False else self.env.companies.ids)})
        unallocated_earning_account = self.env.cr.dictfetchall()
        return unallocated_earning_account

    def _arrange_account_budget_line(self, balance_sheet_lines, account_lines,
                                     budget_lines, dict_id, abs_of=None):
        group_ids = self.env['account.group'].search(
            [('id', 'in', list(map(lambda x: x['group_id'], account_lines)))])
        for lines in account_lines:
            if budget_lines:
                budget_line = list(
                    filter(lambda x: x['code'] == lines['code'], budget_lines))
                if len(budget_line) > 0:
                    lines['planned'] = budget_line[0]['planned']
                else:
                    lines['planned'] = 0
                lines['dict_id'] = dict_id
                lines['group'] = False
                lines['parent_id'] = ''
                lines['count'] = 25
            else:
                lines['planned'] = 0
                lines['dict_id'] = dict_id
                lines['group'] = False
                lines['parent_id'] = ''
                lines['count'] = 25
            lines['abs_of'] = abs_of
        new_lines = self._arrange_account_groups(group_ids, account_lines,
                                                 dict_id, abs_of)
        balance_sheet_lines += new_lines

    def _arrange_account_groups(self, group_ids, account_lines, dict_id, abs_of):
        new_lines = []
        for group in group_ids:
            test_lines = list(filter(lambda x: x['group_id'] == group.id,
                                     account_lines))
            if group.parent_id:
                if len(new_lines) != 0:
                    parent_line = list(filter(
                        lambda x: x['id'] == str(group.parent_id.id) + dict_id,
                        new_lines))
                    if parent_line:
                        parent_line[0].update({
                            'total': parent_line[0]['total'] + sum(
                                list(map(lambda x: x['total'], test_lines))),
                            'planned': parent_line[0]['planned'] + sum(
                                list(map(lambda x: x['planned'], test_lines))),
                            'abs_of': abs_of
                        })
                        new_lines.append({
                            'id': str(group.id) + dict_id,
                            'code': '',
                            'group': True,
                            'name': group.display_name,
                            'total': sum(
                                list(map(lambda x: x['total'], test_lines))),
                            'planned': sum(
                                list(map(lambda x: x['planned'], test_lines))),
                            'dict_id': dict_id,
                            'parent_id': parent_line[0]['id'],
                            'count': 20,
                            'abs_of': abs_of
                        })
                    else:
                        new_lines.append({
                            'id': str(group.parent_id.id) + dict_id,
                            'code': '',
                            'group': True,
                            'name': group.parent_id.display_name,
                            'total': sum(
                                list(map(lambda x: x['total'], test_lines))),
                            'planned': sum(
                                list(map(lambda x: x['planned'], test_lines))),
                            'dict_id': dict_id,
                            'parent_id': dict_id,
                            'count': 15,
                            'abs_of': abs_of
                        })
                        new_lines.append({
                            'id': str(group.id) + dict_id,
                            'code': '',
                            'group': True,
                            'name': group.display_name,
                            'total': sum(
                                list(map(lambda x: x['total'], test_lines))),
                            'planned': sum(
                                list(map(lambda x: x['planned'], test_lines))),
                            'dict_id': dict_id,
                            'parent_id': str(group.parent_id.id) + dict_id,
                            'count': 20,
                            'abs_of': abs_of
                        })
                else:
                    new_lines.append({
                        'id': str(group.parent_id.id) + dict_id,
                        'code': '',
                        'group': True,
                        'name': group.parent_id.display_name,
                        'total': sum(
                            list(map(lambda x: x['total'], test_lines))),
                        'planned': sum(
                            list(map(lambda x: x['planned'], test_lines))),
                        'dict_id': dict_id,
                        'parent_id': dict_id,
                        'count': 15,
                        'abs_of': abs_of
                    })
                    new_lines.append({
                        'id': str(group.id) + dict_id,
                        'code': '',
                        'group': True,
                        'name': group.display_name,
                        'total': sum(
                            list(map(lambda x: x['total'], test_lines))),
                        'planned': sum(
                            list(map(lambda x: x['planned'], test_lines))),
                        'dict_id': dict_id,
                        'parent_id': str(group.parent_id.id) + dict_id,
                        'count': 20,
                        'abs_of': abs_of
                    })
            else:
                new_lines.append({
                    'id': str(group.id) + dict_id,
                    'code': '',
                    'group': True,
                    'name': group.display_name,
                    'total': sum(list(map(lambda x: x['total'], test_lines))),
                    'planned': sum(
                        list(map(lambda x: x['planned'], test_lines))),
                    'dict_id': dict_id,
                    'parent_id': dict_id,
                    'count': 15,
                    'abs_of': abs_of
                })
            new_lines += test_lines
        no_group_lines = list(
            filter(lambda x: x['group_id'] is None, account_lines))
        if no_group_lines:
            new_lines.append({
                'id': 'None' + dict_id,
                'code': '',
                'group': True,
                'name': 'no group',
                'total': sum(list(map(lambda x: x['total'], no_group_lines))),
                'planned': sum(
                    list(map(lambda x: x['planned'], no_group_lines))),
                'dict_id': dict_id,
                'parent_id': dict_id,
                'count': 15,
                'abs_of': abs_of
            })
            new_lines += no_group_lines
        return new_lines

    def print_xlsx_tasc_balance_sheet(self, options, params):
        return {
            'type': 'ir.actions.report',
            'data': {'model': self.env.context.get('model'),
                     'options': json.dumps(options,
                                           default=date_utils.json_default),
                     'output_format': 'xlsx',
                     'financial_id': self.env.context.get('id'),
                     'allowed_company_ids': self.env.context.get(
                         'allowed_company_ids'),
                     'report_name': 'Tasc Balance Sheet Report',
                     },
            'report_type': 'xlsx'
        }

    @api.model
    def get_xlsx(self, options, response=None):
        print('report_json_bs', report_json_bs)
        headers = self._get_header()
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet()
        main_head = workbook.add_format(
            {'font_size': 13, 'align': 'center', 'border': 1,
             'bg_color': '#fcd15b'})
        line_style = workbook.add_format(
            {'font_size': 12, 'bold': True})
        line_style_sub = workbook.add_format(
            {'font_size': 12, 'bold': True})
        line_style_sub.set_indent(1)
        sub_line_style = workbook.add_format(
            {'font_size': 12, })
        sub_line_style1 = workbook.add_format(
            {'font_size': 12, 'bold': True})
        sub_line_style1.set_indent(2)
        sub_line_style2 = workbook.add_format(
            {'font_size': 12, })
        sub_line_style2.set_indent(3)
        row_head = 3
        col_head = 1
        col_head_sub = 3
        for header in headers:
            sheet.merge_range(row_head, col_head, row_head, col_head_sub,
                              header, main_head)
            col_head += 3
            col_head_sub += 3
        row_head = 4
        col_head = 1
        col_head_sub = 3
        for line in report_json_bs[0]:
            print('line', line)
            sheet.merge_range(row_head, col_head, row_head, col_head_sub,
                              line['name'], line_style)
            col_head_1 = 4
            col_head_2 = 6
            for column in line['columns']:
                sheet.merge_range(row_head, col_head_1, row_head, col_head_2,
                                  column['name'], line_style)
                col_head_1 += 3
                col_head_2 += 3
            if line['child_lines']:
                col_head_23 = 1
                col_head_sub_23 = 3
                for child in line['child_lines']:
                    row_head += 1
                    sheet.merge_range(row_head, col_head_23, row_head,
                                      col_head_sub_23,
                                      child['name'], line_style_sub)
                    col_head_11 = 4
                    col_head_22 = 6
                    for column in child['columns']:
                        sheet.merge_range(row_head, col_head_11, row_head,
                                          col_head_22,
                                          column['name'], line_style)
                        col_head_11 += 3
                        col_head_22 += 3
                    if child['account_lines']:
                        col_head_24 = 1
                        col_head_sub_24 = 3
                        for acc_ch_lines in child['account_lines']:
                            if acc_ch_lines['dict_id'] == child['id']:
                                row_head += 1
                                sheet.merge_range(row_head, col_head_24, row_head,
                                                  col_head_sub_24,
                                                  acc_ch_lines['code'] + ' ' +
                                                  acc_ch_lines['name'], sub_line_style1 if acc_ch_lines['group'] is True else sub_line_style2)
                                if acc_ch_lines['abs_of'] is True:
                                    sheet.merge_range(row_head, col_head_24 + 3, row_head,
                                                      col_head_sub_24 + 3,
                                                      abs(acc_ch_lines['total']), sub_line_style)
                                elif acc_ch_lines['abs_of'] is False:
                                    sheet.merge_range(row_head, col_head_24 + 3,
                                                      row_head,
                                                      col_head_sub_24 + 3,
                                                      -abs(acc_ch_lines[
                                                              'total']),
                                                      sub_line_style)
                                elif acc_ch_lines['abs_of'] == 'CU':
                                    sheet.merge_range(row_head, col_head_24 + 3,
                                                      row_head,
                                                      col_head_sub_24 + 3,
                                                      -1 * (acc_ch_lines[
                                                              'total']),
                                                      sub_line_style)
                                else:
                                    sheet.merge_range(row_head, col_head_24 + 3,
                                                      row_head,
                                                      col_head_sub_24 + 3,
                                                      acc_ch_lines['total'],
                                                      sub_line_style)
                                sheet.merge_range(row_head, col_head_24 + 6, row_head,
                                                  col_head_sub_24 + 6,
                                                  acc_ch_lines['planned'], sub_line_style)
                                sheet.merge_range(row_head, col_head_24 + 9, row_head,
                                                  col_head_sub_24 + 9,
                                                  acc_ch_lines['total'] - acc_ch_lines['planned'], sub_line_style)
            if line['account_lines']:
                col_head_24 = 1
                col_head_sub_24 = 3
                for acc_line in line['account_lines']:
                    if acc_line['dict_id'] == line['id']:
                        row_head += 1
                        sheet.merge_range(row_head, col_head_24, row_head,
                                          col_head_sub_24,
                                          acc_line['code'] + ' ' +
                                          acc_line['name'],
                                          sub_line_style1 if acc_line[
                                                                 'group'] is True else sub_line_style2)
                        if acc_line['abs_of'] is True:
                            sheet.merge_range(row_head, col_head_24 + 3,
                                              row_head,
                                              col_head_sub_24 + 3,
                                              abs(acc_line['total']),
                                              sub_line_style)
                        elif acc_line['abs_of'] is False:
                            sheet.merge_range(row_head, col_head_24 + 3,
                                              row_head,
                                              col_head_sub_24 + 3,
                                              -abs(acc_line['total']),
                                              sub_line_style)
                        elif acc_line['abs_of'] == 'CU':
                            sheet.merge_range(row_head, col_head_24 + 3,
                                              row_head,
                                              col_head_sub_24 + 3,
                                              -1 * (acc_line['total']),
                                              sub_line_style)
                        else:
                            sheet.merge_range(row_head, col_head_24 + 3,
                                              row_head,
                                              col_head_sub_24 + 3,
                                              acc_line['total'],
                                              sub_line_style)
                        sheet.merge_range(row_head, col_head_24 + 6,
                                          row_head,
                                          col_head_sub_24 + 6,
                                          acc_line['planned'],
                                          sub_line_style)
                        sheet.merge_range(row_head, col_head_24 + 9,
                                          row_head,
                                          col_head_sub_24 + 9,
                                          acc_line['total'] -
                                          acc_line['planned'],
                                          sub_line_style)
            row_head += 1

        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()
