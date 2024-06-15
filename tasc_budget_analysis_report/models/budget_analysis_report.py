# -*- coding: utf-8 -*-
from odoo import api, models, _
from odoo.tools import format_date, date_utils, get_lang
from collections import defaultdict
from odoo.exceptions import UserError, RedirectWarning

import json
import datetime


class TascCashFlowReportCustomHandler(models.AbstractModel):
    _name = 'account.tasc.budget.analysis.report.handler'
    _inherit = 'account.report.custom.handler'
    _description = 'Budget Analysis Report Custom Handler'

    def _get_custom_display_config(self):
        return {
            'css_custom_class': 'journal_report',
            'components': {
                'AccountReportLine': 'tasc_budget_analysis_report.BudgetAnalysisReportLine',
            },
            'templates': {
                'AccountReportHeader': 'tasc_budget_analysis_report.BudgetAnalysisReportHeader',
                'AccountReportLineName': 'tasc_budget_analysis_report.BudgetAnalysisReportLineName',
            },
            'pdf_export': {
                'pdf_export_main_table_header': 'tasc_budget_analysis_report.budget_analysis_report_pdf_export_main_table_header',
                'pdf_export_filters': 'tasc_budget_analysis_report.budget_analysis_report_pdf_export_filters',
                'pdf_export_main_table_body': 'tasc_budget_analysis_report.budget_analysis_report_pdf_export_main_table_body',
            },
        }

    def _dynamic_lines_generator(self, report, options,
                                 all_column_groups_expression_totals,
                                 warnings=None):
        """ Returns the first level of the report, journal lines. """
        journal_query_res = self._query_budget(options)

        # Set the options with the journals that should be unfolded by default.
        lines = []
        unfolded_budgets = []
        for budget_index, (budget_id, budget_vals) in enumerate(
                journal_query_res.items()):
            budget_key = report._get_generic_line_id('crossovered.budget',
                                                     budget_id)
            unfolded = budget_key in options.get(
                'unfolded_lines') or options.get(
                'unfold_all')
            if unfolded:
                unfolded_budgets.append(unfolded)
            lines.append(
                self._get_budget_line(options, budget_key, budget_vals,
                                      unfolded,
                                      is_first_budget=len(
                                          unfolded_budgets) == 1))

        return [(0, line) for line in lines]

    #
    def _query_budget(self, options):
        params = []
        queries = []
        report = self.env.ref(
            'tasc_budget_analysis_report.tasc_budget_analysis_report')

        for column_group_key, options_group in report._split_options_per_column_group(
                options).items():
            tables, where_clause, where_params = report._query_get(
                options_group, 'strict_range')
            params.append(column_group_key)
            params += where_params
            queries.append(f"""
                SELECT
                    %s as column_group_key,
                    cb.id,
                    cb.name,
                    cp.currency_id as company_currency
                FROM {tables} 
                JOIN crossovered_budget cb ON cb.id = "crossovered_budget_lines".crossovered_budget_id
                JOIN res_company cp ON cp.id = "crossovered_budget_lines".company_id 
                WHERE {where_clause}
            """)

        rslt = {}
        self._cr.execute(" UNION ALL ".join(queries), params)
        for budget_res in self._cr.dictfetchall():
            if budget_res['id'] not in rslt:
                rslt[budget_res['id']] = {col_group_key: {} for col_group_key in
                                          options['column_groups']}
            rslt[budget_res['id']][budget_res['column_group_key']] = budget_res
        return rslt

    #
    def _get_budget_line(self, options, line_id, eval_dict, unfolded,
                         is_first_budget):
        """ returns the line that is representing a journal in the report.

        :param options: The report options
        :param line_id: The line id for this journal
        :param eval_dict: The values for this journal
        :param is_first_journal: If this is the first journal in the report or not. Additional journals will have a page break used when printing in PDF.
        """
        # The column group does not matter for these values: any group will share the same journal.
        budget_vals = next(
            col_group_val for col_group_val in eval_dict.values())
        # has_foreign_currency = journal_vals['currency_id'] and journal_vals['currency_id'] != journal_vals['company_currency']
        return {
            'id': line_id,
            'name': f"{budget_vals['name']}",
            'level': 0,
            'columns': [],
            'unfoldable': True,
            'unfolded': unfolded,
            'budget_id': budget_vals['id'],
            'page_break': unfolded and not is_first_budget,
            'expand_function': '_report_expand_unfoldable_line_budget_report',
            'colspan': len(options['columns']) + 1
            # We want it to take the whole line. It makes it easier to unfold it.
        }

    def _report_expand_unfoldable_line_budget_report(self, line_dict_id,
                                                     groupby, options,
                                                     progress, offset,
                                                     unfold_all_batch_data):
        report = self.env['account.report'].browse(options['report_id'])
        new_options = options.copy()

        model, budget_id = report._get_model_info_from_id(line_dict_id)

        if model != 'crossovered.budget':
            raise UserError(
                _('Trying to use the budget line expand function on a line that is not linked to a budget.'))

        lines = []
        budget = self.env[model].browse(budget_id)

        # Get budget lines
        new_lines, after_load_more_lines, has_more, treated_results_count, next_progress, ending_balance_by_col_group = self._get_lines_for_group(
            new_options, line_dict_id, budget, progress, offset)
        lines.extend(new_lines)
        return {
            'lines': lines,
            'after_load_more_lines': after_load_more_lines,
            'offset_increment': treated_results_count,
            'has_more': has_more,
            'progress': next_progress,
        }

    #
    # def _report_expand_unfoldable_line_journal_report_expand_journal_line_by_month(self, line_dict_id, groupby, options, progress, offset, unfold_all_batch_data):
    #     model, record_id = self.env['account.report']._get_model_info_from_id(line_dict_id)
    #
    #     if model != 'account.journal':
    #         raise UserError(_('Trying to use the journal line expand function on a line that is not linked to a journal.'))
    #
    #     lines = []
    #     journal = self.env[model].browse(record_id)
    #     aml_results = self._query_months(options, line_dict_id, offset, journal)
    #     lines.extend(self._get_month_lines(options, line_dict_id, aml_results, progress, offset))
    #
    #     return {
    #         'lines': lines,
    #     }

    def _custom_options_initializer(self, report, options,
                                    previous_options=None):
        super()._custom_options_initializer(report, options,
                                            previous_options=previous_options)
        options['report'] = 'tasc_budget_analysis'
        # if report.user_has_groups('base.group_multi_currency'):
        #     options['multi_currency'] = True
        # else:
        #     options['columns'] = [
        #         column for column in options['columns']
        #         if column['expression_label'] not in {'amount_currency', 'currency'}
        #     ]
        #
        # default_order_column = {
        #     'expression_label': 'invoice_date',
        #     'direction': 'ASC',
        # }
        #
        # options['order_column'] = (previous_options or {}).get('order_column') or default_order_column

    def _get_lines_for_group(self, options, parent_line_id, budget, progress,
                             offset):
        """ Create the report lines for a group of moves. A group is either a journal, or a month if the report is grouped by month."""

        lines, after_load_more_lines = [], []
        current_balances, next_progress = {}, {}
        # Treated result count also consider the lines not rendered in the report, and is used for the query offset.
        # Rendered line count does not consider the lines not rendered, and allows to stop rendering more when the quota has been reached.
        treated_results_count = 0
        has_more_lines = False

        eval_dict = self._query_budget_aml(options, offset, budget)
        if offset == 0:
            lines.append(self._get_columns_line(options, parent_line_id))

        # Group the lines by moves, to simplify the following code.
        line_dict_grouped = self._group_lines_by_budget(options, eval_dict,
                                                        parent_line_id)
        report = self.env.ref(
            'tasc_budget_analysis_report.tasc_budget_analysis_report')

        treated_amls_count = 0
        for budget_key, budget_line_vals_list in line_dict_grouped.items():
            # All move lines for a move will share static values, like if the move is multicurrency, the journal,..
            # These can be fetched using any column groups or lines for this move.
            first_move_line = budget_line_vals_list[0]
            general_line_vals = next(
                col_group_val for col_group_val in first_move_line.values())
            if report.load_more_limit and len(
                    budget_line_vals_list) + treated_amls_count > report.load_more_limit and \
                    options['export_mode'] != 'print':
                # This element won't generate a line now, but we use it to know that we'll need to add a load_more line.
                has_more_lines = True
                if treated_amls_count == 0:
                    # A single move lines count exceed the load more limit, we need to raise to inform the user
                    msg = _(
                        "The 'load more limit' setting of this report is too low to display all the lines of the entry you're trying to show.")
                    if self.env.user.has_group('account.group_account_manager'):
                        action = {
                            "view_mode": "form",
                            "res_model": "account.report",
                            "type": "ir.actions.act_window",
                            "res_id": report.id,
                            "views": [[self.env.ref(
                                "account_reports.account_report_form").id,
                                       "form"]],
                        }
                        title = _('Go to report configuration')

                        raise RedirectWarning(msg, action, title)
                    raise UserError(msg)
                break
            # is_unreconciled_payment = journal.type == 'bank' and not any(line for line in move_line_vals_list if next(col_group_val for col_group_val in line.values())['account_type'] in ('liability_credit_card', 'asset_cash'))
            # if journal.type == 'bank':
            #     cumulate_balance(first_move_line, current_balances, is_unreconciled_payment)

            # Do not display payments move on bank journal if the options isn't enabled.
            # if not options.get('show_payment_lines') and is_unreconciled_payment:
            #     treated_results_count += len(move_line_vals_list)   # used to get the offset
            #     continue
            # Create the first line separately, as we want to give it some specific behavior and styling
            lines.append(self._get_first_budget_line(options, parent_line_id,
                                                     budget_key,
                                                     first_move_line))
            treated_amls_count += len(budget_line_vals_list)
            treated_results_count += 1
            for line_index, budget_line_vals in enumerate(
                    budget_line_vals_list[1:]):
                line = self._get_aml_line(options, parent_line_id,
                                          budget_line_vals, line_index, budget)
                treated_results_count += 1
                if line:
                    lines.append(line)

                multicurrency_name = self._get_aml_line_name(options, budget,
                                                             -1,
                                                             first_move_line)
        return lines, after_load_more_lines, has_more_lines, treated_results_count, next_progress, current_balances

    def _query_budget_aml(self, options, offset=0, budget=False):
        params = []
        queries = []
        lang = self.env.user.lang or get_lang(self.env).code
        cost_center_name = f"COALESCE(aa.name->>'{lang}', aa.name->>'en_US')" if \
            self.pool['account.analytic.account'].name.translate else 'aa.name'
        project_site_name = f"COALESCE(ab.name->>'{lang}', ab.name->>'en_US')" if \
            self.pool['account.analytic.account'].name.translate else 'ab.name'

        report = self.env.ref(
            'tasc_budget_analysis_report.tasc_budget_analysis_report')
        for column_group_key, options_group in report._split_options_per_column_group(
                options).items():
            date_from = options_group['date']['date_from']
            date_to = options_group['date']['date_to']
            # Override any forced options: We want the ones given in the options
            options_group['date'] = options['date']
            tables, where_clause, where_params = report._query_get(
                options_group, 'strict_range',
                domain=[('crossovered_budget_id', '=', budget.id),
                        ('company_id', '=', self.env.company.id),
                        ('date_from', '>=', date_from),
                        ('date_to', '<=', date_to)
                        ])

            sort_by_date = options_group.get('sort_by_date')
            params.append(column_group_key)
            params += where_params
            limit_to_load = report.load_more_limit + 1 if report.load_more_limit and \
                                                          options[
                                                              'export_mode'] != 'print' else None
            params += [limit_to_load, offset]
            queries.append(f"""
                SELECT
                    %s AS column_group_key,
                    "crossovered_budget_lines".id as budget_line_id,
                    "crossovered_budget_lines".crossovered_budget_id as budget_id,
                    "crossovered_budget_lines".project_site_id,
                    "crossovered_budget_lines".date_from,
                    "crossovered_budget_lines".date_to,
                    "crossovered_budget_lines".planned_amount,
                    "crossovered_budget_lines".practical_demo,
                    cb.id as budget_id,
                    abp.name as budgetory_position,
                    {cost_center_name} as cost_center,
                    {project_site_name} as project_site,
                    cb.name as budget_name,
                    cp.currency_id as company_currency
                FROM {tables}
                JOIN crossovered_budget cb ON cb.id = "crossovered_budget_lines".crossovered_budget_id 
                LEFT JOIN account_budget_post abp ON abp.id = "crossovered_budget_lines".general_budget_id 
                JOIN res_company cp ON cp.id = cb.company_id
                LEFT JOIN account_analytic_account aa ON aa.id = "crossovered_budget_lines".analytic_account_id
                LEFT JOIN account_analytic_account ab ON ab.id = "crossovered_budget_lines".project_site_id
                WHERE {where_clause}
                GROUP BY "crossovered_budget_lines".id, cb.id,abp.id, aa.id, ab.id,cp.id
                ORDER BY  "crossovered_budget_lines".id 
               LIMIT %s
               OFFSET %s
            """)
        # 1.2.Fetch data from DB
        rslt = {}
        self._cr.execute('(' + ') UNION ALL ('.join(queries) + ')', params)
        for aml_result in self._cr.dictfetchall():
            rslt.setdefault(aml_result['budget_line_id'],
                            {col_group_key: {} for col_group_key in
                             options['column_groups']})
            rslt[aml_result['budget_line_id']][
                aml_result['column_group_key']] = aml_result

        return rslt

    def _get_columns_line(self, options, parent_key):
        """ returns the line displaying the columns used by the journal.
        The report isn't using the table header, as different journal type needs different columns.

        :param options: The report options
        :param parent_key: the key of the parent line, journal or month
        :param journal_type: the journal type
        """
        columns = []
        # has_multicurrency = self.user_has_groups('base.group_multi_currency')
        report = self.env['account.report'].browse(options['report_id'])
        for column in options['columns']:
            if column['expression_label'] == 'budget':
                col_value = column['name']
            elif column['expression_label'] == 'budget_position':
                col_value = column['name']
            elif column['expression_label'] == 'cost_center':
                col_value = column['name']
            elif column['expression_label'] == 'project':
                col_value = column['name']
            elif column['expression_label'] == 'start_date':
                col_value = column['name']
            elif column['expression_label'] == 'end_date':
                col_value = column['name']
            elif column['expression_label'] == 'planned_amount':
                col_value = column['name']
            elif column['expression_label'] == 'consumed_amount':
                col_value = column['name']
            elif column['expression_label'] == 'remaining_amount':
                col_value = column['name']
            elif column['expression_label'] == 'consumed_percentage':
                col_value = column['name']
            else:
                col_value = ''
            columns.append(
                report._build_column_dict(col_value, column, options=options))

        return {
            'id': report._get_generic_line_id(None, None,
                                              parent_line_id=parent_key,
                                              markup='headers'),
            'name': '',
            'columns': columns,
            'level': 3,
            'parent_id': parent_key,
        }

    def _get_first_budget_line(self, options, parent_key, line_key, values):
        """ Returns the first line of a move.
        It is different from the other lines, as it contains more information such as the date, partner, and a link to the move itself.

        :param options: The report options.
        :param parent_key: The id of the lines that should be parenting the aml lines. Should be the group line (either the journal, or month).
        :param line_key: The id of the move line itself.
        :param values: The values of the move line.
        :param new_balance: The new balance of the move line, if any. Use to display the cumulated balance for bank journals.
        """
        report = self.env['account.report'].browse(options['report_id'])
        # Helps to format the line. If a line is linked to a partner but the account isn't receivable or payable, we want to display it in blue.
        columns = []
        for column_group_key, column_group_options in report._split_options_per_column_group(
                options).items():
            values = values[column_group_key]
            a = parent_key.rsplit('~', 1)
            if values['budget_id'] == int(a[1]):
                budget_line = self.env['crossovered.budget.lines'].browse(
                    values['budget_line_id'])
                remaining_amount = budget_line.remaining_amount
                acutal_percentage = budget_line.actual_percentage

                for column in options['columns']:
                    if column.get('expression_label') == 'budget':
                        col_value = values['budget_name']
                    elif column.get('expression_label') == 'budget_position':
                        col_value = values['budgetory_position']
                    elif column.get('expression_label') == 'cost_center':
                        col_value = values['cost_center']
                    elif column.get('expression_label') == 'project':
                        col_value = values['project_site']
                    elif column.get('expression_label') == 'start_date':
                        col_value = values['date_from']
                    elif column.get('expression_label') == 'end_date':
                        col_value = values['date_to']
                    elif column.get('expression_label') == 'planned_amount':
                        col_value = values['planned_amount']
                    elif column.get('expression_label') == 'consumed_amount':
                        col_value = values['practical_demo']
                    elif column.get('expression_label') == 'remaining_amount':
                        col_value = remaining_amount
                    elif column.get(
                            'expression_label') == 'consumed_percentage':
                        col_value = acutal_percentage
                    else:
                        col_value = ''
                    columns.append(report._build_column_dict(col_value, column,
                                                             options=options))
            return {
                'id': line_key,
                # 'name': values['budget_name'],
                'level': 3,
                'columns': columns,
                'parent_id': parent_key,
                'budget_id': values['budget_id'],
            }

    def _group_lines_by_budget(self, options, eval_dict, parent_line_id):
        report = self.env['account.report'].browse(options['report_id'])
        grouped_dict = defaultdict(list)
        for budget_line_vals in eval_dict.values():
            # We don't care about which column group is used for the id as it will be the same for all of them.
            budget_id = \
                next(col_group_val for col_group_val in
                     budget_line_vals.values())[
                    'budget_id']

            move_key = report._get_generic_line_id('crossovered.budget',
                                                   budget_id,
                                                   parent_line_id=parent_line_id)
            grouped_dict[move_key].append(budget_line_vals)
        return grouped_dict

    def _get_aml_line(self, options, parent_key, eval_dict, line_index,
                      journal):
        """ Returns the line of an account move line.

        :param options: The report options.
        :param parent_key: The id of the lines that should be parenting the aml lines. Should be the group line (either the journal, or month).
        :param values: The values of the move line.
        :param current_balance: The current balance of the move line, if any. Use to display the cumulated balance for bank journals.
        :param line_index: The index of the line in the move line list. Used to write additional information in the name, such as the move reference, or the ammount in currency.
        """
        a = parent_key.rsplit('~', 1)
        report = self.env['account.report'].browse(options['report_id'])
        columns = []
        general_vals = next(
            col_group_val for col_group_val in eval_dict.values())
        if general_vals['budget_id'] == int(a[1]):
            for column_group_key, column_group_options in report._split_options_per_column_group(
                    options).items():
                values = eval_dict[column_group_key]

                # if values['budget_id'] == parent_key
                if values['budget_id'] == int(a[1]):
                    budget_line = self.env['crossovered.budget.lines'].browse(
                        values['budget_line_id'])
                    remaining_amount = budget_line.remaining_amount
                    acutal_percentage = budget_line.actual_percentage

                    for column in options['columns']:
                        # if column.get('expression_label') not in ['additional_col_1', 'additional_col_2']:
                        #     if column.get('expression_label') == 'account':
                        #         if values['journal_type'] == 'bank':  # For additional lines still showing in the bank journal, make sure to use the partner on the account if available.
                        #             col_value = '%s %s' % (values['account_code'], values['partner_name'] or values['account_name'])
                        #         elif values['journal_type'] == 'sale':
                        #             if values['debit']:
                        #                 col_value = '%s %s' % (values['account_code'], values['partner_name'] or values['account_name'])
                        #             else:
                        #                 col_value = '%s %s' % (values['account_code'], values['account_name'])
                        #         else:
                        #             col_value = '%s %s' % (values['account_code'], values['account_name'])
                        #     elif column.get('expression_label') == 'label':
                        if column.get('expression_label') == 'budget':
                            col_value = values['budget_name']
                        elif column.get(
                                'expression_label') == 'budget_position':
                            col_value = values['budgetory_position']
                        elif column.get('expression_label') == 'cost_center':
                            col_value = values['cost_center']
                        elif column.get('expression_label') == 'project':
                            col_value = values['project_site']
                        elif column.get('expression_label') == 'start_date':
                            col_value = values['date_from']
                        elif column.get('expression_label') == 'end_date':
                            col_value = values['date_to']
                        elif column.get('expression_label') == 'planned_amount':
                            col_value = values['planned_amount']
                        elif column.get(
                                'expression_label') == 'consumed_amount':
                            col_value = values['practical_demo']
                        elif column.get(
                                'expression_label') == 'remaining_amount':
                            col_value = remaining_amount
                        elif column.get(
                                'expression_label') == 'consumed_percentage':
                            col_value = acutal_percentage
                        else:
                            col_value = ''
                        # elif column.get('expression_label') == 'invoice_date':
                        #     col_value = ''
                        # else:
                        #     col_value = values[column.get('expression_label')]

                        columns.append(
                            report._build_column_dict(col_value, column,
                                                      options=options))
                        # else:
                        #     balance = False if column_group_options.get('show_payment_lines') and is_unreconciled_payment else values.get('cumulated_balance')
                        #     columns += self._get_move_line_additional_col(column_group_options, balance, values, is_unreconciled_payment)
                        #     break

                return {
                    'id': report._get_generic_line_id('crossovered.budget.line',
                                                      values['budget_line_id'],
                                                      parent_line_id=parent_key),
                    'name': self._get_aml_line_name(options, journal,
                                                    line_index,
                                                    eval_dict),
                    'level': 3,
                    'parent_id': parent_key,
                    'columns': columns,
                }

    def _get_aml_line_name(self, options, journal, line_index, values):
        # """ Returns the information to write as the name of the move lines, if needed.
        # Typically, this is the move reference, or the amount in currency if we are in a multicurrency environment and the move is using a foreign currency.
        #
        # :param options: The report options.
        # :param line_index: The index of the line in the move line list. We always want the reference second if existing and the amount in currency third if needed.
        # :param values: The values of the move line.
        # """
        # # Returns the first occurrence. There is only one column group anyway.
        # for column_group_key in options['column_groups']:
        #     if journal.type == 'bank' or not (self.user_has_groups('base.group_multi_currency') and values[column_group_key]['is_multicurrency']):
        #         amount_currency_name = ''
        #     else:
        #         amount_currency_name = _(
        #             'Amount in currency: %s',
        #             self.env['account.report'].format_value(
        #                 options,
        #                 values[column_group_key]['amount_currency_total'],
        #                 currency=self.env['res.currency'].browse(values[column_group_key]['move_currency']),
        #                 blank_if_zero=False,
        #                 figure_type='monetary'
        #             )
        #         )
        #     if line_index == 0:
        #         res = values[column_group_key]['reference'] or amount_currency_name
        #         # if the invoice ref equals the payment ref then let's not repeat the information
        #         return res if res != values[column_group_key]['move_name'] else ''
        #     elif line_index == 1:
        #         return values[column_group_key]['reference'] and amount_currency_name or ''
        #     elif line_index == -1:  # Only when we create a line just for the amount currency. It's the only time we always want the amount.
        #         return amount_currency_name
        #     else:
        return ''
