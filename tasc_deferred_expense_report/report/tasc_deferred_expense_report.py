from odoo import fields, models, _
from odoo.tools import format_date, get_lang

from collections import defaultdict

MAX_NAME_LENGTH = 50


class TascDeferredExpenseReport(models.AbstractModel):
    _name = 'tasc.deferred.expense.report'
    _inherit = 'account.report.custom.handler'
    _description = 'Tasc Deferred Expense Report Handler'

    def _dynamic_lines_generator(self, report, options,
                                 all_column_groups_expression_totals,
                                 warnings=None):
        report = self._with_context_company2code2account(report)

        lines, totals_by_column_group = self._generate_report_lines_without_grouping(
            report, options)
        # add the groups by account
        if options['move_groupby_account']:
            lines = self._group_by_account(report, lines, options)
        else:
            lines = report._regroup_lines_by_name_prefix(options, lines,
                                                         '_report_expand_unfoldable_line_move_report_prefix_group',
                                                         0)
        return [(0, line) for line in lines]

    def _generate_report_lines_without_grouping(self, report, options,
                                                prefix_to_match=None,
                                                parent_id=None,
                                                forced_account_id=None):
        # construct a dictionary:
        #   {(account_id, asset_id): {col_group_key: {expression_label_1: value, expression_label_2: value, ...}}}
        all_move_ids = set()
        all_lines_data = {}
        for column_group_key, column_group_options in report._split_options_per_column_group(
                options).items():
            # the lines returned are already sorted by account_id!
            lines_query_results = self._query_lines(column_group_options,
                                                    prefix_to_match=prefix_to_match,
                                                    forced_account_id=forced_account_id)
            for account_id, move_id, cols_by_expr_label in lines_query_results:
                line_id = (account_id, move_id)
                all_move_ids.add(move_id)
                if line_id not in all_lines_data:
                    all_lines_data[line_id] = {column_group_key: []}
                all_lines_data[line_id][column_group_key] = cols_by_expr_label
        column_names = [
            'name'
        ]
        totals_by_column_group = defaultdict(
            lambda: dict.fromkeys(column_names, 0.0))

        # Browse all the necessary assets in one go, to minimize the number of queries
        moves_cache = {move.id: move for move in
                       self.env['account.move'].browse(all_move_ids)}
        # construct the lines, 1 at a time
        lines = []
        company_currency = self.env.company.currency_id
        for (account_id, move_id), col_group_totals in all_lines_data.items():
            all_columns = []
            for column_data in options['columns']:
                col_group_key = column_data['column_group_key']
                expr_label = column_data['expression_label']
                if col_group_key not in col_group_totals or expr_label not in \
                        col_group_totals[col_group_key]:
                    all_columns.append(report._build_column_dict(None, None))
                    continue

                col_value = col_group_totals[col_group_key][expr_label]
                col_data = None if col_value is None else column_data

                all_columns.append(
                    report._build_column_dict(col_value, col_data,
                                              options=options))

            name = moves_cache[move_id].name
            line = {
                'id': report._get_generic_line_id('account.move', move_id,
                                                  parent_line_id=parent_id),
                'level': 2,
                'name': name,
                'columns': all_columns,
                'unfoldable': False,
                'unfolded': False,
                'caret_options': 'account_move_line',
                'move_account_id': account_id,
            }
            if parent_id:
                line['parent_id'] = parent_id
            if len(name) >= MAX_NAME_LENGTH:
                line['title_hover'] = name
            lines.append(line)
        return lines, totals_by_column_group

    def _caret_options_initializer(self):
        # Use 'caret_option_open_record_form' defined in account_reports rather than a custom function
        return {
            'account_move_line': [
                {'name': _("Open Journal Entry"),
                 'action': 'caret_option_open_record_form'},
            ]
        }

    def _custom_options_initializer(self, report, options,
                                    previous_options=None):
        super()._custom_options_initializer(report, options,
                                            previous_options=previous_options)
        column_group_options_map = report._split_options_per_column_group(
            options)

        for col in options['columns']:
            column_group_options = column_group_options_map[
                col['column_group_key']]
            # Dynamic naming of columns containing dates
            if col['expression_label'] == 'balance':
                col[
                    'name'] = ''  # The column label will be displayed in the subheader
            if col['expression_label'] in ['start_date',
                                           'end_date']:
                col['name'] = format_date(self.env,
                                          column_group_options['date'][
                                              'date_from'])
            elif col['expression_label'] in ['start_date', 'end_date']:
                col['name'] = format_date(self.env,
                                          column_group_options['date'][
                                              'date_to'])

        options['custom_columns_subheaders'] = [
            {"name": _("Characteristics"), "colspan": 15},
        ]

        # Group by account by default
        groupby_activated = (previous_options or {}).get('move_groupby_account',
                                                         True)
        options['move_groupby_account'] = groupby_activated
        # If group by account is activated, activate the hierarchy (which will group by account group as well) if
        # the company has at least one account group, otherwise only group by account
        has_account_group = self.env['account.group'].search_count(
            [('company_id', '=', self.env.company.id)], limit=1)
        hierarchy_activated = (previous_options or {}).get('hierarchy', True)
        options[
            'hierarchy'] = has_account_group and hierarchy_activated or False

    def _with_context_company2code2account(self, report):
        if self.env.context.get('company2code2account') is not None:
            return report

        company2code2account = defaultdict(dict)
        for account in self.env['account.account'].search([]):
            company2code2account[account.company_id.id][account.code] = account

        return report.with_context(company2code2account=company2code2account)

    def _query_lines(self, options, prefix_to_match=None,
                     forced_account_id=None):
        """
        Returns a list of tuples: [(asset_id, account_id, [{expression_label: value}])]
        """
        lines = []
        move_lines = self._query_values(options,
                                        prefix_to_match=prefix_to_match,
                                        forced_account_id=forced_account_id)

        # Assign the gross increases sub assets to their main asset (parent)
        parent_lines = []
        children_lines = defaultdict(list)
        for al in move_lines:
            parent_lines += [al]

        for al in parent_lines:
            posted_amt = 0.0
            unposted_amt = 0.0
            tot_amt = 0.0
            if al["posted_deferred_move_amount_total"] != None:
                posted_amt = al["posted_deferred_move_amount_total"]
            if al["unposted_deferred_move_amount_total"] != None:
                unposted_amt = al["unposted_deferred_move_amount_total"]

            if al["deferred_move_amount_total"] != None:
                tot_amt = al["deferred_move_amount_total"]

            # Format the data
            columns_by_expr_label = {
                "name": al["deferral_name"],
                "deferred_account_id": al["account_name"],
                "move_id": al["move_name"],
                "project_site": al["project_site"],
                "cost_center": al["cost_center"],
                "deferred_start_date": al["start_date"],
                "deferred_end_date": al["end_date"],
                "currency": al["currency"],
                "tot_period": al["tot_period"],
                "tot_period_posted": al["posted_deferred_moves"],
                "tot_remining_period": al["unposted_deferred_moves"],
                "original_amount": tot_amt,
                "deferred_amount": posted_amt,
                "remaining_amount": unposted_amt,
                "expense_account_id": al["credit_account_name"],
            }

            lines.append(
                (al['account_id'], al['move_id'], columns_by_expr_label))
        return lines

    def _group_by_account(self, report, lines, options):
        """
        This function adds the grouping lines on top of each group of account.asset
        It iterates over the lines, change the line_id of each line to include the account.account.id and the
        account.asset.id.
        """
        if not lines:
            return lines

        line_vals_per_account_id = {}
        for line in lines:
            parent_account_id = line.get('move_account_id')

            model, res_id = report._get_model_info_from_id(line['id'])
            assert model == 'account.move'

            # replace the line['id'] to add the account.account.id
            line['id'] = report._build_line_id([
                (None, 'account.account', parent_account_id),
                (None, 'account.move', res_id)
            ])

            line_vals_per_account_id.setdefault(parent_account_id, {
                # We don't assign a name to the line yet, so that we can batch the browsing of account.account objects
                'id': report._build_line_id(
                    [(None, 'account.account', parent_account_id)]),
                'columns': [],  # Filled later
                'unfoldable': True,
                'unfolded': options.get('unfold_all', False),
                'level': 1,

                # This value is stored here for convenience; it will be removed from the result
                'group_lines': [],
            })['group_lines'].append(line)

        # Generate the result
        idx_monetary_columns = [idx_col for idx_col, col in
                                enumerate(options['columns']) if
                                col['figure_type'] == 'monetary']
        accounts = self.env['account.account'].browse(
            line_vals_per_account_id.keys())
        rslt_lines = []
        for account in accounts:
            account_line_vals = line_vals_per_account_id[account.id]
            account_line_vals['name'] = f"{account.code} {account.name}"

            rslt_lines.append(account_line_vals)

            group_totals = {column_index: 0 for column_index in
                            idx_monetary_columns}
            group_lines = report._regroup_lines_by_name_prefix(
                options,
                account_line_vals.pop('group_lines'),
                '_report_expand_unfoldable_line_move_report_prefix_group',
                account_line_vals['level'],
                parent_line_dict_id=account_line_vals['id'],
            )

            for account_subline in group_lines:
                # Add this line to the group totals
                for column_index in idx_monetary_columns:
                    group_totals[column_index] += account_subline['columns'][
                        column_index].get('no_format', 0)

                # Setup the parent and add the line to the result
                account_subline['parent_id'] = account_line_vals['id']
                rslt_lines.append(account_subline)

            # Add totals (columns) to the account line
            for column_index in range(len(options['columns'])):
                account_line_vals['columns'].append(report._build_column_dict(
                    group_totals.get(column_index, ''),
                    options['columns'][column_index],
                    options=options,
                ))
        return rslt_lines

    def _query_values(self, options, prefix_to_match=None,
                      forced_account_id=None):
        "Get the data from the database"

        self.env['account.move.line'].check_access_rights('read')
        self.env['account.move'].check_access_rights('read')

        move_filter = f"""move.state {"!= 'cancel'" if options.get('all_entries') else "= 'posted'"}"""

        query_params = {
            'date_to': options['date']['date_to'],
            'date_from': options['date']['date_from'],
            'company_ids': tuple(
                self.env['account.report'].get_report_company_ids(options)),
            'include_draft': options.get('all_entries', False),
        }

        prefix_query = ''
        if prefix_to_match:
            prefix_query = "AND move.name ILIKE %(prefix_to_match)s"
            query_params['prefix_to_match'] = f"{prefix_to_match}%"

        account_query = ''
        if forced_account_id:
            account_query = "AND account.id = %(forced_account_id)s"
            query_params['forced_account_id'] = forced_account_id

        analytical_query = ''
        analytic_account_ids = []
        if options.get('analytic_accounts') and not any(
                x in options.get('analytic_accounts_list', []) for x in
                options['analytic_accounts']):
            analytic_account_ids += [
                [str(account_id) for account_id in
                 options['analytic_accounts']]]
        if options.get('analytic_accounts_list'):
            analytic_account_ids += [[str(account_id) for account_id in
                                      options.get('analytic_accounts_list')]]
            # if analytic_account_ids:
            # analytical_query = 'AND aml.analytic_distribution ?| array[%(analytic_account_ids)s]'
            query_params['analytic_account_ids'] = analytic_account_ids
        lang = self.env.user.lang or get_lang(self.env).code
        project_site_name = f"COALESCE(project_sites.name->>'{lang}', project_sites.name->>'en_US')" if \
            self.pool[
                'account.analytic.account'].name.translate else 'project_sites.name'
        cc_name = f"COALESCE(cc.name->>'{lang}', cc.name->>'en_US')" if \
            self.pool[
                'account.analytic.account'].name.translate else 'cc.name'
        account_name = f"COALESCE(account.name->>'{lang}', account.name->>'en_US')" if \
            self.pool[
                'account.account'].name.translate else 'account.name'
        credit_account_name = f"COALESCE(credit_account.name->>'{lang}', credit_account.name->>'en_US')" if \
            self.pool[
                'account.account'].name.translate else 'credit_account.name'

        sql = f"""            
                  SELECT  
                    count(amd.deferred_move_id) as tot_period,
                    {account_name} as account_name,
                     account.id AS account_id,
                    move.name as move_name,
                    move.id as move_id,
                    aml.name as deferral_name,
                    aml.deferred_start_date as start_date,
                    aml.deferred_end_date as end_date,
                    {project_site_name} as project_site,
                    {cc_name} as cost_center,
                    currency.name as currency,
                    count(posted_deferred_moves.deferred_move_id) as posted_deferred_moves,
                    sum(posted_deferred_move_amounts.amount_total) as posted_deferred_move_amount_total,
                    count(unposted_deferred_moves.deferred_move_id) as unposted_deferred_moves,
                    sum(unposted_deferred_move_amounts.amount_total) as unposted_deferred_move_amount_total,
	                sum(deferred_move_amounts.amount_total) as deferred_move_amount_total,
	                                     {credit_account_name} as credit_account_name,

                    credit_account.id as credit_account_id
                    FROM account_move_deferred_rel AS amd
                    LEFT JOIN account_move move on move.id=amd.original_move_id
                    LEFT JOIN account_move_line aml ON aml.move_id = move.id
                    LEFT JOIN account_account AS account ON aml.account_id = account.id
                    LEFT JOIN account_analytic_account as project_sites on aml.project_site_id = project_sites.id  
                    LEFT JOIN account_analytic_account as cc on aml.analytic_account_id = cc.id  
                    LEFT JOIN res_currency as currency on move.currency_id = currency.id  
                    LEFT JOIN account_move_line credit_aml ON credit_aml.move_id = move.id AND credit_aml.credit != 0
                    LEFT JOIN account_account AS credit_account ON credit_aml.account_id = credit_account.id
                    
                                        LEFT JOIN (
                                        SELECT
                                            amd.deferred_move_id
                                        FROM account_move_deferred_rel amd
                                        JOIN account_move am ON amd.deferred_move_id = am.id
                                        WHERE am.state = 'posted'
                                        ) AS posted_deferred_moves ON amd.deferred_move_id = posted_deferred_moves.deferred_move_id
                                          LEFT JOIN (
                                        SELECT
                                            amd.deferred_move_id
                                        FROM account_move_deferred_rel amd
                                        JOIN account_move am ON amd.deferred_move_id = am.id
                                        WHERE am.state = 'draft' or am.state='to_approve' or am.state='cancel'
                                        ) AS unposted_deferred_moves ON amd.deferred_move_id = unposted_deferred_moves.deferred_move_id
                                        LEFT JOIN (
                        SELECT
                            amd.deferred_move_id,
                            SUM(am.amount_total) as amount_total
                        FROM account_move_deferred_rel amd
                        JOIN account_move am ON amd.deferred_move_id = am.id
                        WHERE am.state = 'posted'
                        GROUP BY amd.deferred_move_id
                    ) AS posted_deferred_move_amounts ON amd.deferred_move_id = posted_deferred_move_amounts.deferred_move_id
                                        LEFT JOIN (
                        SELECT
                            amd.deferred_move_id,
                            SUM(am.amount_total) as amount_total
                        FROM account_move_deferred_rel amd
                        JOIN account_move am ON amd.deferred_move_id = am.id
                        WHERE am.state = 'draft' or am.state='to_approve' or am.state='cancel'
                        GROUP BY amd.deferred_move_id
                    ) AS unposted_deferred_move_amounts ON amd.deferred_move_id = unposted_deferred_move_amounts.deferred_move_id
                    LEFT JOIN (
                        SELECT
                            amd.deferred_move_id,
                            SUM(am.amount_total) as amount_total
                        FROM account_move_deferred_rel amd
                        JOIN account_move am ON amd.deferred_move_id = am.id
                        GROUP BY amd.deferred_move_id
                    ) AS deferred_move_amounts ON amd.deferred_move_id = deferred_move_amounts.deferred_move_id
                where aml.debit !=0 and aml.tax_line_id is NULL and
                move.company_id in %(company_ids)s and
                ((move.date <= %(date_to)s and move.date >= %(date_from)s) or (amd.original_move_id in (select amdr.original_move_id from account_move amv join account_move_deferred_rel amdr 
							on amdr.deferred_move_id = amv.id where amv.date <=  %(date_to)s and amv.date >=  %(date_from)s)))
               {prefix_query}
                GROUP BY  account.id,move.id,aml.id,project_sites.id,cc.id,currency.id,credit_account.id
                ORDER BY account.code
                """
        self._cr.execute(sql, query_params)
        results = self._cr.dictfetchall()
        return results

    def _report_expand_unfoldable_line_move_report_prefix_group(self,
                                                                line_dict_id,
                                                                groupby,
                                                                options,
                                                                progress,
                                                                offset,
                                                                unfold_all_batch_data=None):
        matched_prefix = self.env[
            'account.report']._get_prefix_groups_matched_prefix_from_line_id(
            line_dict_id)
        report = self.env['account.report'].browse(options['report_id'])

        lines, _totals_by_column_group = self._generate_report_lines_without_grouping(
            report,
            options,
            prefix_to_match=matched_prefix,
            parent_id=line_dict_id,
            forced_account_id=self.env[
                'account.report']._get_res_id_from_line_id(
                line_dict_id, 'account.account'),
        )

        lines = report._regroup_lines_by_name_prefix(
            options,
            lines,
            '_report_expand_unfoldable_line_move_report_prefix_group',
            len(matched_prefix),
            matched_prefix=matched_prefix,
            parent_line_dict_id=line_dict_id,
        )

        return {
            'lines': lines,
            'offset_increment': len(lines),
            'has_more': False,
        }
