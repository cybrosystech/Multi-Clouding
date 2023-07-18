import io

import xlsxwriter

from odoo import models, api, _
from odoo.tools import date_utils
from odoo.tools.safe_eval import json

gross_profit_revenue = []
gross_profit_budget = []
indirect_cost_sum = []
indirect_cost_budget = []
other_income_sum = []
other_income_budget = []
depreciation_amortization_sum = []
depreciation_amortization_budget = []
finance_cost_sum = []
finance_cost_budget_list = []
taxes_sum = []
taxes_budget_list = []
report_json_pl = []


class ProfitLossBalance(models.AbstractModel):
    _name = 'profit.loss.balance'

    def _get_templates(self):
        return {
            'main_template': 'tasc_pf_bs_report.tasc_pf_bs_html_content_view',
            'main_table_header_template': 'account_reports.main_table_header',
            'line_template': 'cash_flow_statement_report.line_template_cash_flow',
            'footnotes_template': 'account_reports.footnotes_template',
            'budget_analysis_search_view': 'tasc_pf_bs_report.tasc_pf_bs_search_view',
        }

    @api.model
    def get_button_profit_loss(self):
        return [
            {'name': _('Export (XLSX)'), 'sequence': 2,
             'action': 'print_xlsx_tasc_profit_loss',
             'file_export_type': _('XLSX')},
        ]

    def get_company_filter(self, options):
        if 'multi_company' not in list(options.keys()):
            options['multi-company'] = False
        else:
            if options['multi_company'] == 'all-companies':
                options['multi-company'] = True
            print('options', options)

    def get_cash_flow_information(self, filter):
        options = self.env['cash.flow.statement']._get_cashflow_options(filter)
        self.get_company_filter(options)
        info = {
            'options': options,
            'main_html': self.get_html_content(options),
            'searchview_html': self.env['ir.ui.view']._render_template(
                self._get_templates().get('budget_analysis_search_view', ),
                values={'options': options}),
            'buttons': self.get_button_profit_loss()
        }
        return info

    def _clear_list_values(self):
        gross_profit_revenue.clear()
        gross_profit_budget.clear()
        indirect_cost_sum.clear()
        indirect_cost_budget.clear()
        other_income_sum.clear()
        other_income_budget.clear()
        depreciation_amortization_sum.clear()
        depreciation_amortization_budget.clear()
        finance_cost_sum.clear()
        finance_cost_budget_list.clear()
        taxes_sum.clear()
        taxes_budget_list.clear()

    def get_html_content(self, options):
        self._clear_list_values()
        templates = self._get_templates()
        template = templates['main_template']
        values = {'model': self}
        header = self._get_header()
        lines = self._get_pf_bs_lines(options)
        report_json_pl.clear()
        report_json_pl.append(lines)
        values['lines'] = {'lines': lines, 'header': header}
        html = self.env.ref(template)._render(values)
        return html

    def _get_header(self):
        return ['Account', 'Balance', 'Budget', 'Variance']

    def _get_pf_bs_lines(self, options):
        test_child_lines = []
        states_args = """ parent_state = 'posted'"""
        if options['entry'] != 'posted':
            states_args = """ parent_state in ('posted', 'draft')"""
        query = '''select coalesce((sum(journal_item.debit) - sum(journal_item.credit)), 0) total,
                    account.name, account.code, account.id, account.group_id
                    from account_move_line as journal_item
                    left join account_account as account on journal_item.account_id = account.id
                    '''
        query_budget = '''select coalesce(sum(budget_line.planned_amount), 0) as planned,
                          account.name, account.code
                          from crossovered_budget_lines as budget_line
                          left join account_budget_post as budgetary on 
                          budget_line.general_budget_id = budgetary.id
                          left join account_budget_rel as rel on budgetary.id = rel.budget_id
                          left join account_account as account on rel.account_id = account.id
                        '''
        pf_lines = [
            {
                'id': 'operating_revenue_id',
                'name': 'Operating Revenue',
                'columns': [
                    {'name': round(operating_revenue, 2), 'class': 'number'} for
                    operating_revenue in
                    self._get_operating_revenue(
                        states_args, query,
                        query_budget,
                        options, test_child_lines,
                        dict_id='operating_revenue_id')],
                'child_lines': '',
                'account_lines': test_child_lines
            },
            {
                'id': 'direct_cost_id',
                'name': 'Direct Cost',
                'columns': [{'name': round(direct_cost, 2), 'class': 'number'}
                            for
                            direct_cost in
                            self._get_direct_cost(states_args, query,
                                                  query_budget,
                                                  options, test_child_lines,
                                                  dict_id='direct_cost_id')],
                'child_lines': '',
                'account_lines': test_child_lines
            },
            {
                'id': 'gross_profit',
                'name': 'Gross Profit',
                'columns': [{'name': abs(round(sum(gross_profit_revenue), 2)),
                             'class': 'number'},
                            {'name': round(sum(gross_profit_budget), 2),
                             'class': 'number'},
                            {'name': round(sum(gross_profit_revenue) - sum(
                                gross_profit_budget), 2),
                             'class': 'number'}],
                'child_lines': '',
                'account_lines': ''
            },
            {
                'id': 'indirect_cost',
                'name': 'Indirect Cost',
                'columns': '',
                'child_lines': [
                    {
                        'id': 'staff_cost',
                        'name': 'Staff Cost',
                        'columns': [
                            {'name': round(staff_cost, 2), 'class': 'number'}
                            for
                            staff_cost in
                            self._get_staff_cost(states_args, query,
                                                 query_budget, options,
                                                 test_child_lines,
                                                 dict_id='staff_cost')],
                        'account_lines': test_child_lines
                    },
                    {
                        'id': 'general_admin_expense',
                        'name': 'General Admin Expense',
                        'columns': [
                            {'name': round(general_admin_expense, 2),
                             'class': 'number'}
                            for
                            general_admin_expense in
                            self._get_general_admin_expense(states_args, query,
                                                            query_budget,
                                                            options,
                                                            test_child_lines,
                                                            dict_id='general_admin_expense')],
                        'account_lines': test_child_lines
                    },
                    {
                        'id': 'statutory_and_misc',
                        'name': 'Statutory and Misc',
                        'columns': [
                            {'name': round(statutory_and_misc, 2),
                             'class': 'number'} for
                            statutory_and_misc in
                            self._get_statutory_and_misc(states_args, query,
                                                         query_budget,
                                                         options,
                                                         test_child_lines,
                                                         dict_id='statutory_and_misc')],
                        'account_lines': test_child_lines
                    },
                    {
                        'id': 'bank_changes',
                        'name': 'Bank Charges',
                        'columns': [
                            {'name': round(bank_changes, 2), 'class': 'number'}
                            for
                            bank_changes in
                            self._get_bank_changes(states_args, query,
                                                   query_budget,
                                                   options, test_child_lines,
                                                   dict_id='bank_changes')],
                        'account_lines': test_child_lines
                    },
                ],
                'account_lines': ''
            },
            {
                'id': 'other_income',
                'name': 'Other Income',
                'columns': '',
                'child_lines': [
                    {
                        'id': 'disposal_gain_loss',
                        'name': 'Disposal Gain/Loss',
                        'columns': [
                            {'name': round(disposal_gain_loss, 2),
                             'class': 'number'} for
                            disposal_gain_loss in
                            self._get_disposal_gain_loss(states_args, query,
                                                         query_budget,
                                                         options,
                                                         test_child_lines,
                                                         dict_id='disposal_gain_loss')],
                        'account_lines': test_child_lines
                    },
                    {
                        'id': 'interest_income',
                        'name': 'Interest Income',
                        'columns': [{'name': round(interest_income, 2),
                                     'class': 'number'}
                                    for
                                    interest_income in
                                    self._get_interest_income(states_args,
                                                              query,
                                                              query_budget,
                                                              options,
                                                              test_child_lines,
                                                              dict_id='interest_income')],
                        'account_lines': test_child_lines
                    },
                    {
                        'id': 'intra_group_interest_income',
                        'name': 'Intra group - Interest income',
                        'columns': [
                            {'name': round(intra_group_interest_income, 2),
                             'class': 'number'} for
                            intra_group_interest_income in
                            self._get_intra_group_interest_income(states_args,
                                                                  query,
                                                                  query_budget,
                                                                  options,
                                                                  test_child_lines,
                                                                  dict_id='intra_group_interest_income')],
                        'account_lines': test_child_lines
                    },
                ],
                'account_lines': ''
            },
            {
                'id': 'ebitda',
                'name': 'EBITDA',
                'columns': [{'name': round(-abs(sum(
                    gross_profit_revenue + indirect_cost_sum + other_income_sum)), 2),
                    'class': 'number'},
                    {'name': round(sum(
                        gross_profit_budget + indirect_cost_budget + other_income_budget),
                        2),
                        'class': 'number'},
                    {'name': round(sum(
                        gross_profit_revenue + indirect_cost_sum + other_income_sum) - sum(
                        gross_profit_budget + indirect_cost_budget + other_income_budget),
                                   2),
                     'class': 'number'}],
                'child_lines': '',
                'account_lines': ''
            },
            {
                'id': 'depreciation_amortization',
                'name': 'Depreciation and Amortization',
                'columns': [
                    {'name': round(depreciation_amortization, 2),
                     'class': 'number'}
                    for depreciation_amortization in
                    self._get_depreciation_amortization(states_args, query,
                                                        query_budget,
                                                        options,
                                                        test_child_lines,
                                                        dict_id='depreciation_amortization')],
                'child_lines': '',
                'account_lines': test_child_lines
            },
            {
                'id': 'ebit',
                'name': 'EBIT',
                'columns': [{'name': round(-abs(sum(
                    gross_profit_revenue + indirect_cost_sum + other_income_sum + depreciation_amortization_sum)
                    ), 2),
                    'class': 'number'},
                    {'name': round(sum(
                        gross_profit_budget + indirect_cost_budget + other_income_budget + depreciation_amortization_budget),
                        2),
                        'class': 'number'},
                    {'name': round(sum(
                        gross_profit_revenue + indirect_cost_sum + other_income_sum + depreciation_amortization_sum) - sum(
                        gross_profit_budget + indirect_cost_budget + other_income_budget + depreciation_amortization_budget),
                                   2),
                     'class': 'number'}],
                'child_lines': '',
                'account_lines': ''
            },
            {
                'id': 'finance_cost',
                'name': 'Finance Cost',
                'columns': [
                    {'name': round(finance_cost, 2), 'class': 'number'}
                    for finance_cost in
                    self._get_finance_cost(states_args, query,
                                           query_budget,
                                           options, test_child_lines,
                                           dict_id='finance_cost')],
                'child_lines': '',
                'account_lines': test_child_lines
            },
            {
                'id': 'ebt',
                'name': 'EBT',
                'columns': [{'name': round(-abs(sum(
                    gross_profit_revenue + indirect_cost_sum + other_income_sum + depreciation_amortization_sum + finance_cost_sum)
                    ), 2),
                    'class': 'number'},
                    {'name': round(sum(
                        gross_profit_budget + indirect_cost_budget + other_income_budget + depreciation_amortization_budget + finance_cost_budget_list),
                        2),
                        'class': 'number'},
                    {'name': round(sum(
                        gross_profit_budget + indirect_cost_budget + other_income_budget + depreciation_amortization_budget + finance_cost_budget_list) - sum(
                        gross_profit_budget + indirect_cost_budget + other_income_budget + depreciation_amortization_budget + finance_cost_budget_list),
                                   2),
                     'class': 'number'}],
                'child_lines': '',
                'account_lines': ''
            },
            {
                'id': 'taxes',
                'name': 'Taxes',
                'columns': [{'name': round(taxes, 2), 'class': 'number'} for
                            taxes in
                            self._get_taxes(states_args, query,
                                            query_budget,
                                            options, test_child_lines,
                                            dict_id='taxes')],
                'child_lines': '',
                'account_lines': test_child_lines
            },
            {
                'id': 'net_profit_loss',
                'name': 'Net Profit - Loss',
                'columns': [{'name': round(-abs(sum(
                    gross_profit_revenue + indirect_cost_sum + other_income_sum + depreciation_amortization_sum + finance_cost_sum + taxes_sum)),
                    2),
                    'class': 'number'},
                    {'name': round(sum(
                        gross_profit_budget + indirect_cost_budget + other_income_budget + depreciation_amortization_budget + finance_cost_budget_list + taxes_budget_list),
                        2),
                        'class': 'number'},
                    {'name': round(sum(
                        gross_profit_revenue + indirect_cost_sum + other_income_sum + depreciation_amortization_sum + finance_cost_sum + taxes_sum) - sum(
                        gross_profit_budget + indirect_cost_budget + other_income_budget + depreciation_amortization_budget + finance_cost_budget_list + taxes_budget_list),
                                   2),
                     'class': 'number'}],
                'child_lines': '',
                'account_lines': ''
            },
        ]
        pf_lines[3]['columns'] = [{'name': round(-abs(sum(indirect_cost_sum)), 2),
                                   'class': 'number'},
                                  {'name': round(sum(indirect_cost_budget), 2),
                                   'class': 'number'},
                                  {'name': round(sum(indirect_cost_sum) - sum(
                                      indirect_cost_budget), 2),
                                   'class': 'number'}]
        pf_lines[4]['columns'] = [{'name': round(sum(other_income_sum), 2),
                                   'class': 'number'},
                                  {'name': round(sum(other_income_budget), 2),
                                   'class': 'number'},
                                  {'name': round(sum(other_income_sum) - sum(
                                      other_income_budget), 2),
                                   'class': 'number'}]
        return pf_lines

    def _get_operating_revenue(self, states_args, query, query_budget, options,
                               test_child_lines, dict_id):
        self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                    and journal_item.company_id in %(company_ids)s
                                    and journal_item.date >= %(from_date)s 
                                    and journal_item.date <= %(to_date)s
                                    and {states_args}
                                    group by account.name, account.code, account.id, account.group_id
                                    '''.format(states_args=states_args),
                            {'from_date': options['date']['date_from'],
                             'to_date': options['date']['date_to'],
                             'code_start': '410000', 'code_end': '419999',
                             'company_ids': tuple([self.env.company.id] if options['multi-company'] is False else self.env.companies.ids)})
        operating_revenue = self.env.cr.dictfetchall()
        self.env.cr.execute(query_budget + '''where account.code between %(code_start)s and %(code_end)s
                                            and budget_line.company_id in %(company_ids)s
                                            and budget_line.date_from >= %(from_date)s 
                                            and budget_line.date_to <= %(to_date)s
                                            group by account.name, account.code
                                            ''',
                            {'from_date': options['date']['date_from'],
                             'to_date': options['date']['date_to'],
                             'code_start': '410000', 'code_end': '419999',
                             'company_ids': tuple([self.env.company.id] if options['multi-company'] is False else self.env.companies.ids)})
        operating_revenue_budget = self.env.cr.dictfetchall()
        self._arrange_account_budget_line(test_child_lines,
                                          operating_revenue,
                                          operating_revenue_budget, dict_id,
                                          abs_of=True)
        operating_revenue_total = sum(
            list(map(lambda x: x['total'], operating_revenue)))
        operating_revenue_budget_total = sum(list(
            map(lambda x: x['planned'], operating_revenue_budget)))
        gross_profit_revenue.append(operating_revenue_total)
        gross_profit_budget.append(operating_revenue_budget_total)
        return [abs(operating_revenue_total), operating_revenue_budget_total,
                operating_revenue_total - operating_revenue_budget_total]

    def _get_direct_cost(self, states_args, query,
                         query_budget,
                         options, test_child_lines, dict_id):
        self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                            and journal_item.company_id in %(company_ids)s
                                            and journal_item.date >= %(from_date)s 
                                            and journal_item.date <= %(to_date)s
                                            and {states_args}
                                            group by account.name, account.code, account.id, account.group_id
                                            '''.format(states_args=states_args),
                            {'from_date': options['date']['date_from'],
                             'to_date': options['date']['date_to'],
                             'code_start': '420000', 'code_end': '429999',
                             'company_ids': tuple([self.env.company.id] if options['multi-company'] is False else self.env.companies.ids)})
        direct_cost = self.env.cr.dictfetchall()
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
        direct_cost_budget = self.env.cr.dictfetchall()
        self._arrange_account_budget_line(test_child_lines,
                                          direct_cost,
                                          direct_cost_budget, dict_id, abs_of=True)
        direct_cost_total = sum(
            list(map(lambda x: x['total'], direct_cost)))
        direct_cost_budget_total = sum(list(
            map(lambda x: x['planned'], direct_cost_budget)))
        gross_profit_revenue.append(direct_cost_total)
        gross_profit_budget.append(direct_cost_budget_total)
        return [abs(direct_cost_total), direct_cost_budget_total,
                direct_cost_total - direct_cost_budget_total]

    def _get_staff_cost(self, states_args, query, query_budget, options,
                        test_child_lines, dict_id):
        self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                    and journal_item.company_id in %(company_ids)s
                                                    and journal_item.date >= %(from_date)s 
                                                    and journal_item.date <= %(to_date)s
                                                    and {states_args}
                                                    group by account.name, account.code, account.id, account.group_id
                                                    '''.format(
            states_args=states_args),
                            {'from_date': options['date']['date_from'],
                             'to_date': options['date']['date_to'],
                             'code_start': '510000', 'code_end': '549999',
                             'company_ids': tuple([self.env.company.id] if options['multi-company'] is False else self.env.companies.ids)})
        staff_cost = self.env.cr.dictfetchall()
        self.env.cr.execute(query_budget + '''where account.code between %(code_start)s and %(code_end)s
                                                            and budget_line.company_id in %(company_ids)s
                                                            and budget_line.date_from >= %(from_date)s 
                                                            and budget_line.date_to <= %(to_date)s
                                                            group by account.name, account.code
                                                            ''',
                            {'from_date': options['date']['date_from'],
                             'to_date': options['date']['date_to'],
                             'code_start': '510000', 'code_end': '549999',
                             'company_ids': tuple([self.env.company.id] if options['multi-company'] is False else self.env.companies.ids)})
        staff_cost_budget = self.env.cr.dictfetchall()
        self._arrange_account_budget_line(test_child_lines,
                                          staff_cost,
                                          staff_cost_budget, dict_id, abs_of=False)
        staff_cost_total = sum(
            list(map(lambda x: x['total'], staff_cost)))
        staff_cost_budget_total = sum(list(
            map(lambda x: x['planned'], staff_cost_budget)))
        indirect_cost_sum.append(staff_cost_total)
        indirect_cost_budget.append(staff_cost_budget_total)
        return [-abs(staff_cost_total), staff_cost_budget_total,
                staff_cost_total - staff_cost_budget_total]

    def _get_general_admin_expense(self, states_args, query, query_budget,
                                   options, test_child_lines, dict_id):
        self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                    and journal_item.company_id in %(company_ids)s
                                                    and journal_item.date >= %(from_date)s 
                                                    and journal_item.date <= %(to_date)s
                                                    and {states_args}
                                                    group by account.name, account.code, account.id, account.group_id
                                                    '''.format(
            states_args=states_args),
                            {'from_date': options['date']['date_from'],
                             'to_date': options['date']['date_to'],
                             'code_start': '550000', 'code_end': '552999',
                             'company_ids': tuple([self.env.company.id] if options['multi-company'] is False else self.env.companies.ids)})
        general_admin_expense = self.env.cr.dictfetchall()
        self.env.cr.execute(query_budget + '''where account.code between %(code_start)s and %(code_end)s
                                                            and budget_line.company_id in %(company_ids)s
                                                            and budget_line.date_from >= %(from_date)s 
                                                            and budget_line.date_to <= %(to_date)s
                                                            group by account.name, account.code
                                                            ''',
                            {'from_date': options['date']['date_from'],
                             'to_date': options['date']['date_to'],
                             'code_start': '550000', 'code_end': '552999',
                             'company_ids': tuple([self.env.company.id] if options['multi-company'] is False else self.env.companies.ids)})
        general_admin_expense_budget = self.env.cr.dictfetchall()
        self._arrange_account_budget_line(test_child_lines,
                                          general_admin_expense,
                                          general_admin_expense_budget, dict_id,
                                          abs_of=False)
        general_admin_total = sum(
            list(map(lambda x: x['total'], general_admin_expense)))
        general_admin_budget_total = sum(list(
            map(lambda x: x['planned'], general_admin_expense_budget)))
        indirect_cost_sum.append(general_admin_total)
        indirect_cost_budget.append(general_admin_budget_total)
        return [-abs(general_admin_total),
                general_admin_budget_total, general_admin_total -
                general_admin_budget_total]

    def _get_statutory_and_misc(self, states_args, query, query_budget,
                                options, test_child_lines, dict_id):
        self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                    and journal_item.company_id in %(company_ids)s
                                                    and journal_item.date >= %(from_date)s 
                                                    and journal_item.date <= %(to_date)s
                                                    and {states_args}
                                                    group by account.name, account.code, account.id, account.group_id
                                                    '''.format(
            states_args=states_args),
                            {'from_date': options['date']['date_from'],
                             'to_date': options['date']['date_to'],
                             'code_start': '555000', 'code_end': '559999',
                             'company_ids': tuple([self.env.company.id] if options['multi-company'] is False else self.env.companies.ids)})
        statutory_and_misc = self.env.cr.dictfetchall()
        self.env.cr.execute(query_budget + '''where account.code between %(code_start)s and %(code_end)s
                                                            and budget_line.company_id in %(company_ids)s
                                                            and budget_line.date_from >= %(from_date)s 
                                                            and budget_line.date_to <= %(to_date)s
                                                            group by account.name, account.code
                                                            ''',
                            {'from_date': options['date']['date_from'],
                             'to_date': options['date']['date_to'],
                             'code_start': '555000', 'code_end': '559999',
                             'company_ids': tuple([self.env.company.id] if options['multi-company'] is False else self.env.companies.ids)})
        statutory_and_misc_budget = self.env.cr.dictfetchall()
        self._arrange_account_budget_line(test_child_lines,
                                          statutory_and_misc,
                                          statutory_and_misc_budget, dict_id,
                                          abs_of=False)
        statutory_and_misc_total = sum(
            list(map(lambda x: x['total'], statutory_and_misc)))
        statutory_and_misc_budget_total = sum(list(
            map(lambda x: x['planned'], statutory_and_misc_budget)))
        indirect_cost_sum.append(statutory_and_misc_total)
        indirect_cost_budget.append(statutory_and_misc_budget_total)
        return [-abs(statutory_and_misc_total), statutory_and_misc_budget_total,
                statutory_and_misc_total - statutory_and_misc_budget_total]

    def _get_bank_changes(self, states_args, query, query_budget,
                          options, test_child_lines, dict_id):
        self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                    and journal_item.company_id in %(company_ids)s
                                                    and journal_item.date >= %(from_date)s 
                                                    and journal_item.date <= %(to_date)s
                                                    and {states_args}
                                                    group by account.name, account.code, account.id, account.group_id
                                                    '''.format(
            states_args=states_args),
                            {'from_date': options['date']['date_from'],
                             'to_date': options['date']['date_to'],
                             'code_start': '582100', 'code_end': '582299',
                             'company_ids': tuple([self.env.company.id] if options['multi-company'] is False else self.env.companies.ids)})
        bank_changes = self.env.cr.dictfetchall()
        self.env.cr.execute(query_budget + '''where account.code between %(code_start)s and %(code_end)s
                                                            and budget_line.company_id in %(company_ids)s
                                                            and budget_line.date_from >= %(from_date)s 
                                                            and budget_line.date_to <= %(to_date)s
                                                            group by account.name, account.code
                                                            ''',
                            {'from_date': options['date']['date_from'],
                             'to_date': options['date']['date_to'],
                             'code_start': '582100', 'code_end': '582299',
                             'company_ids': tuple([self.env.company.id] if options['multi-company'] is False else self.env.companies.ids)})
        bank_changes_budget = self.env.cr.dictfetchall()
        self._arrange_account_budget_line(test_child_lines,
                                          bank_changes,
                                          bank_changes_budget, dict_id,
                                          abs_of=False)
        bank_changes_total = sum(
            list(map(lambda x: x['total'], bank_changes)))
        bank_changes_budget_total = sum(list(
            map(lambda x: x['planned'], bank_changes_budget)))
        indirect_cost_sum.append(bank_changes_total)
        indirect_cost_budget.append(bank_changes_budget_total)
        return [-abs(bank_changes_total), bank_changes_budget_total,
                bank_changes_total - bank_changes_budget_total]

    def _get_disposal_gain_loss(self, states_args, query, query_budget,
                                options, test_child_lines, dict_id):
        self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                        and journal_item.company_id in %(company_ids)s
                                                        and journal_item.date >= %(from_date)s 
                                                        and journal_item.date <= %(to_date)s
                                                        and {states_args}
                                                        group by account.name, account.code, account.id, account.group_id
                                                        '''.format(
            states_args=states_args),
                            {'from_date': options['date']['date_from'],
                             'to_date': options['date']['date_to'],
                             'code_start': '558100', 'code_end': '558199',
                             'company_ids': tuple([self.env.company.id] if options['multi-company'] is False else self.env.companies.ids)})
        disposal_gain_loss = self.env.cr.dictfetchall()
        self.env.cr.execute(query_budget + '''where account.code between %(code_start)s and %(code_end)s
                                                                and budget_line.company_id in %(company_ids)s
                                                                and budget_line.date_from >= %(from_date)s 
                                                                and budget_line.date_to <= %(to_date)s
                                                                group by account.name, account.code
                                                                ''',
                            {'from_date': options['date']['date_from'],
                             'to_date': options['date']['date_to'],
                             'code_start': '558100', 'code_end': '558199',
                             'company_ids': tuple([self.env.company.id] if options['multi-company'] is False else self.env.companies.ids)})
        disposal_gain_loss_budget = self.env.cr.dictfetchall()
        self._arrange_account_budget_line(test_child_lines,
                                          disposal_gain_loss,
                                          disposal_gain_loss_budget, dict_id)
        disposal_gain_loss_total = sum(
            list(map(lambda x: x['total'], disposal_gain_loss)))
        disposal_gain_loss_budget_total = sum(list(
            map(lambda x: x['planned'], disposal_gain_loss_budget)))
        other_income_sum.append(disposal_gain_loss_total)
        other_income_budget.append(disposal_gain_loss_budget_total)
        return [disposal_gain_loss_total, disposal_gain_loss_budget_total,
                disposal_gain_loss_total - disposal_gain_loss_budget_total]

    def _get_interest_income(self, states_args, query, query_budget,
                             options, test_child_lines, dict_id):
        self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                            and journal_item.company_id in %(company_ids)s
                                                            and journal_item.date >= %(from_date)s 
                                                            and journal_item.date <= %(to_date)s
                                                            and {states_args}
                                                            group by account.name, account.code, account.id, account.group_id
                                                            '''.format(
            states_args=states_args),
                            {'from_date': options['date']['date_from'],
                             'to_date': options['date']['date_to'],
                             'code_start': '581300', 'code_end': '581399',
                             'company_ids': tuple([self.env.company.id] if options['multi-company'] is False else self.env.companies.ids)})
        interest_income = self.env.cr.dictfetchall()
        self.env.cr.execute(query_budget + '''where account.code between %(code_start)s and %(code_end)s
                                                                    and budget_line.company_id in %(company_ids)s
                                                                    and budget_line.date_from >= %(from_date)s 
                                                                    and budget_line.date_to <= %(to_date)s
                                                                    group by account.name, account.code
                                                                    ''',
                            {'from_date': options['date']['date_from'],
                             'to_date': options['date']['date_to'],
                             'code_start': '581300', 'code_end': '581399',
                             'company_ids': tuple([self.env.company.id] if options['multi-company'] is False else self.env.companies.ids)})
        interest_income_budget = self.env.cr.dictfetchall()
        self._arrange_account_budget_line(test_child_lines,
                                          interest_income,
                                          interest_income_budget, dict_id)
        interest_income_total = sum(
            list(map(lambda x: x['total'], interest_income)))
        interest_income_budget_total = sum(list(
            map(lambda x: x['planned'], interest_income_budget)))
        other_income_sum.append(interest_income_total)
        other_income_budget.append(interest_income_budget_total)
        return [interest_income_total, interest_income_budget_total,
                interest_income_total - interest_income_budget_total]

    def _get_intra_group_interest_income(self, states_args, query, query_budget,
                                         options, test_child_lines, dict_id):
        self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                                and journal_item.company_id in %(company_ids)s
                                                                and journal_item.date >= %(from_date)s 
                                                                and journal_item.date <= %(to_date)s
                                                                and {states_args}
                                                                group by account.name, account.code, account.id, account.group_id
                                                                '''.format(
            states_args=states_args),
                            {'from_date': options['date']['date_from'],
                             'to_date': options['date']['date_to'],
                             'code_start': '570000', 'code_end': '579999',
                             'company_ids': tuple([self.env.company.id] if options['multi-company'] is False else self.env.companies.ids)})
        intra_group_interest_income = self.env.cr.dictfetchall()
        self.env.cr.execute(query_budget + '''where account.code between %(code_start)s and %(code_end)s
                                                                        and budget_line.company_id in %(company_ids)s
                                                                        and budget_line.date_from >= %(from_date)s 
                                                                        and budget_line.date_to <= %(to_date)s
                                                                        group by account.name, account.code
                                                                        ''',
                            {'from_date': options['date']['date_from'],
                             'to_date': options['date']['date_to'],
                             'code_start': '570000', 'code_end': '579999',
                             'company_ids': tuple([self.env.company.id] if options['multi-company'] is False else self.env.companies.ids)})
        intra_group_interest_income_budget = self.env.cr.dictfetchall()
        self._arrange_account_budget_line(test_child_lines,
                                          intra_group_interest_income,
                                          intra_group_interest_income_budget,
                                          dict_id)
        intra_group_interest_income_total = sum(
            list(map(lambda x: x['total'], intra_group_interest_income)))
        intra_group_interest_income_budget_total = sum(list(
            map(lambda x: x['planned'], intra_group_interest_income_budget)))
        other_income_sum.append(intra_group_interest_income_total)
        other_income_budget.append(intra_group_interest_income_budget_total)
        return [intra_group_interest_income_total,
                intra_group_interest_income_budget_total,
                intra_group_interest_income_total -
                intra_group_interest_income_budget_total]

    def _get_depreciation_amortization(self, states_args, query, query_budget,
                                       options, test_child_lines, dict_id):
        self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                                    and journal_item.company_id in %(company_ids)s
                                                                    and journal_item.date >= %(from_date)s 
                                                                    and journal_item.date <= %(to_date)s
                                                                    and {states_args}
                                                                    group by account.name,account.code, account.id, account.group_id
                                                                    '''.format(
            states_args=states_args),
                            {'from_date': options['date']['date_from'],
                             'to_date': options['date']['date_to'],
                             'code_start': '553000', 'code_end': '554999',
                             'company_ids': tuple([self.env.company.id] if options['multi-company'] is False else self.env.companies.ids)})
        depreciation_amortization = self.env.cr.dictfetchall()
        self.env.cr.execute(query_budget + '''where account.code between %(code_start)s and %(code_end)s
                                                                            and budget_line.company_id in %(company_ids)s
                                                                            and budget_line.date_from >= %(from_date)s 
                                                                            and budget_line.date_to <= %(to_date)s
                                                                            group by account.name, account.code
                                                                            ''',
                            {'from_date': options['date']['date_from'],
                             'to_date': options['date']['date_to'],
                             'code_start': '553000', 'code_end': '554999',
                             'company_ids': tuple([self.env.company.id] if options['multi-company'] is False else self.env.companies.ids)})
        depreciation_amortization_budget_val = self.env.cr.dictfetchall()
        self._arrange_account_budget_line(test_child_lines,
                                          depreciation_amortization,
                                          depreciation_amortization_budget_val,
                                          dict_id, abs_of=False)
        amortization_total = sum(
            list(map(lambda x: x['total'], depreciation_amortization)))
        amortization_budget_total = sum(list(
            map(lambda x: x['planned'], depreciation_amortization_budget_val)))
        depreciation_amortization_sum.append(amortization_total)
        depreciation_amortization_budget.append(amortization_budget_total)
        return [-abs(amortization_total),
                amortization_budget_total, amortization_total -
                amortization_budget_total]

    def _get_finance_cost(self, states_args, query, query_budget,
                          options, test_child_lines, dict_id):
        self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                                        and journal_item.company_id in %(company_ids)s
                                                                        and journal_item.date >= %(from_date)s 
                                                                        and journal_item.date <= %(to_date)s
                                                                        and {states_args}
                                                                        group by account.name,account.code, account.id, account.group_id
                                                                        '''.format(
            states_args=states_args),
                            {'from_date': options['date']['date_from'],
                             'to_date': options['date']['date_to'],
                             'code_start': '581100', 'code_end': '581299',
                             'company_ids': tuple([self.env.company.id] if options['multi-company'] is False else self.env.companies.ids)})
        finance_cost = self.env.cr.dictfetchall()
        self.env.cr.execute(query_budget + '''where account.code between %(code_start)s and %(code_end)s
                                                                                and budget_line.company_id in %(company_ids)s
                                                                                and budget_line.date_from >= %(from_date)s 
                                                                                and budget_line.date_to <= %(to_date)s
                                                                                group by account.name, account.code
                                                                                ''',
                            {'from_date': options['date']['date_from'],
                             'to_date': options['date']['date_to'],
                             'code_start': '581100', 'code_end': '581299',
                             'company_ids': tuple([self.env.company.id] if options['multi-company'] is False else self.env.companies.ids)})
        finance_cost_budget = self.env.cr.dictfetchall()
        self._arrange_account_budget_line(test_child_lines,
                                          finance_cost,
                                          finance_cost_budget, dict_id,
                                          abs_of=False)
        finance_cost_total = sum(list(map(lambda x: x['total'], finance_cost)))
        finance_cost_budget_total = sum(
            list(map(lambda x: x['planned'], finance_cost_budget)))
        finance_cost_sum.append(finance_cost_total)
        finance_cost_budget_list.append(finance_cost_budget_total)
        return [-abs(finance_cost_total),
                finance_cost_budget_total,
                finance_cost_total - finance_cost_budget_total]

    def _get_taxes(self, states_args, query, query_budget,
                   options, test_child_lines, dict_id):
        self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                                        and journal_item.company_id in %(company_ids)s
                                                                        and journal_item.date >= %(from_date)s 
                                                                        and journal_item.date <= %(to_date)s
                                                                        and {states_args}
                                                                        group by account.name,account.code, account.id, account.group_id
                                                                        '''.format(
            states_args=states_args),
                            {'from_date': options['date']['date_from'],
                             'to_date': options['date']['date_to'],
                             'code_start': '561100', 'code_end': '569999',
                             'company_ids': tuple([self.env.company.id] if options['multi-company'] is False else self.env.companies.ids)})
        taxes = self.env.cr.dictfetchall()
        self.env.cr.execute(query_budget + '''where account.code between %(code_start)s and %(code_end)s
                                                                                and budget_line.company_id in %(company_ids)s
                                                                                and budget_line.date_from >= %(from_date)s 
                                                                                and budget_line.date_to <= %(to_date)s
                                                                                group by account.name, account.code
                                                                                ''',
                            {'from_date': options['date']['date_from'],
                             'to_date': options['date']['date_to'],
                             'code_start': '561100', 'code_end': '569999',
                             'company_ids': tuple([self.env.company.id] if options['multi-company'] is False else self.env.companies.ids)})
        taxes_budget = self.env.cr.dictfetchall()
        self._arrange_account_budget_line(test_child_lines,
                                          taxes,
                                          taxes_budget, dict_id)
        taxes_total = sum(list(map(lambda x: x['total'], taxes)))
        taxes_budget_total = sum(
            list(map(lambda x: x['planned'], taxes_budget)))
        taxes_sum.append(taxes_total)
        taxes_budget_list.append(taxes_budget_total)
        return [taxes_total,
                taxes_budget_total, taxes_total - taxes_budget_total]

    def _arrange_account_budget_line(self, test_child_lines, account_lines,
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
        new_lines = self._arrange_account_groups(group_ids, account_lines, dict_id, abs_of)

        test_child_lines += new_lines

    def _arrange_account_groups(self, group_ids, account_lines, dict_id, abs_of):
        new_lines = []
        for group in group_ids:
            test_lines = list(
                filter(lambda x: x['group_id'] == group.id, account_lines))
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

    def print_xlsx_tasc_profit_loss(self, options, params):
        return {
            'type': 'ir.actions.report',
            'data': {'model': self.env.context.get('model'),
                     'options': json.dumps(options,
                                           default=date_utils.json_default),
                     'output_format': 'xlsx',
                     'financial_id': self.env.context.get('id'),
                     'allowed_company_ids': self.env.context.get(
                         'allowed_company_ids'),
                     'report_name': 'Tasc Profit and Loss Report',
                     },
            'report_type': 'xlsx'
        }

    @api.model
    def get_xlsx(self, options, response=None):
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
        for line in report_json_pl[0]:
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
                    print('child', child)
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
                            print('acc_ch_lines', acc_ch_lines)
                            row_head += 1
                            sheet.merge_range(row_head, col_head_24, row_head,
                                              col_head_sub_24,
                                              acc_ch_lines['name'],
                                              sub_line_style1 if acc_ch_lines[
                                                                     'group'] is True else sub_line_style2)
                            if acc_ch_lines['abs_of'] is True:
                                sheet.merge_range(row_head, col_head_24 + 3,
                                                  row_head,
                                                  col_head_sub_24 + 3,
                                                  abs(acc_ch_lines['total']),
                                                  sub_line_style)
                            elif acc_ch_lines['abs_of'] is False:
                                sheet.merge_range(row_head, col_head_24 + 3,
                                                  row_head,
                                                  col_head_sub_24 + 3,
                                                  abs(acc_ch_lines['total']),
                                                  sub_line_style)
                            else:
                                sheet.merge_range(row_head, col_head_24 + 3,
                                                  row_head,
                                                  col_head_sub_24 + 3,
                                                  acc_ch_lines['total'],
                                                  sub_line_style)
                            sheet.merge_range(row_head, col_head_24 + 6,
                                              row_head,
                                              col_head_sub_24 + 6,
                                              acc_ch_lines['planned'],
                                              sub_line_style)
                            sheet.merge_range(row_head, col_head_24 + 9,
                                              row_head,
                                              col_head_sub_24 + 9,
                                              acc_ch_lines['total'] -
                                              acc_ch_lines['planned'],
                                              sub_line_style)
            if line['account_lines']:
                col_head_24 = 1
                col_head_sub_24 = 3
                for acc_line in line['account_lines']:
                    row_head += 1
                    sheet.merge_range(row_head, col_head_24, row_head,
                                      col_head_sub_24,
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

            # col_head += 3
            # col_head_sub += 3

        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()
