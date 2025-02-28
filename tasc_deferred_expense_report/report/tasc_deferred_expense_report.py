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
            # amount_untaxed = 0.0
            tot_amt = 0.0

            # if al["amount_untaxed"]:
            #     if self.env.company.currency_id.id == al["currency_id"]:
            #         amount_untaxed = al["amount_untaxed"]
            #     else:
            #         currency = self.env['res.currency'].browse(
            #             al["currency_id"])
            #         amount_untaxed = currency._convert(al["amount_untaxed"],
            #                                            self.env.company.currency_id,
            #                                            self.env.company,
            #                                            al["move_date"])

            # if al["posted_deferred_move_amount_total"] != None:
            #     posted_amt = al["posted_deferred_move_amount_total"]
            #
            # if al["deferred_move_amount_total"] != None:
            #     tot_amt = al["deferred_move_amount_total"]
            #
            # remaining_amount = tot_amt - posted_amt

            # Format the data
            columns_by_expr_label = {
                "name": al["deferral_name"],
                "deferred_account_id": al["account_name"],
                "move_id": al["move_name"],
                "project_site": al["project_site"],
                "cost_center": al["cost_center"],
                "deferred_start_date": al["deferred_start_date"],
                "deferred_end_date": al["deferred_end_date"],
                "currency": al["currency"],
                "tot_period": al["total_count"] ,
                "tot_period_posted": al["posted_count"],
                "tot_remining_period": al["unposted_count"],
                "original_amount": al["total_credits"],
                "deferred_amount": al["posted_credits"],
                "remaining_amount": al["unposted_credits"],
                "expense_account_id": al["expense_account"],
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
            account_query = "AND deferred_account.id = %(forced_account_id)s"
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
        project_site_name = f"COALESCE(project_site.name->>'{lang}', project_site.name->>'en_US')" if \
            self.pool[
                'account.analytic.account'].name.translate else 'project_site.name'
        cc_name = f"COALESCE(cc.name->>'{lang}', cc.name->>'en_US')" if \
            self.pool[
                'account.analytic.account'].name.translate else 'cc.name'
        account_name = f"COALESCE(account.name->>'{lang}', account.name->>'en_US')" if \
            self.pool[
                'account.account'].name.translate else 'account.name'
        exp_account_name = f"COALESCE(ae.name->>'{lang}', ae.name->>'en_US')" if \
            self.pool[
                'account.account'].name.translate else 'ae.name'

        sql = f"""
                SELECT 
                    {account_name} AS account_name,
                    account.id as account_id,
                    move.name AS move_name, 
                    move.id AS move_id,
                    line.name AS deferral_name,
                    line.deferred_start_date,
                    line.deferred_end_date,
                    {project_site_name} as project_site,
                    {cc_name} as cost_center,
                    currency.name as currency,
                    currency.id as currency_id,
                    {exp_account_name} AS expense_account,
                    SUM(CASE WHEN mv.state = 'posted' THEN ml.credit ELSE 0 END) AS posted_credits,
                    SUM(CASE WHEN mv.state != 'posted' THEN ml.credit ELSE 0 END) AS unposted_credits,
                    SUM(ml.credit) AS total_credits,
                    COUNT(DISTINCT CASE WHEN mv.state = 'posted' THEN mv.id END) AS posted_count,
                    COUNT(DISTINCT CASE WHEN mv.state != 'posted' THEN mv.id END) AS unposted_count,
                    COUNT(DISTINCT mv.id) AS total_count
                FROM 
                    account_move_deferred_rel amdr 
                LEFT JOIN 
                    account_move move ON move.id = amdr.original_move_id 
                LEFT JOIN 
                    account_move mv ON mv.id = amdr.deferred_move_id 
                LEFT JOIN 
                    account_move_line line ON line.move_id = move.id 
                LEFT JOIN 
                    account_move_line ml ON ml.move_id = mv.id 
                LEFT JOIN 
                    account_account account ON line.deferred_account_id = account.id
                LEFT JOIN account_analytic_account as project_site on 
                    line.project_site_id = project_site.id  
                LEFT JOIN account_analytic_account as cc on 
                    line.analytic_account_id = cc.id  
                LEFT JOIN res_currency as currency on 
                    move.currency_id = currency.id  
                LEFT JOIN 
                    account_account AS ae ON EXISTS (
                        SELECT 1 
                        FROM account_move_line l 
                        INNER JOIN account_move m ON m.id = l.move_id
                        WHERE m.id = mv.id AND l.account_id = ae.id AND l.debit !=0
                    )
                WHERE 
                    line.deferred_account_id = ml.account_id 
                    AND ml.credit != 0 AND move.company_id in %(company_ids)s 
                    AND move.date <= %(date_to)s AND move.date >= %(date_from)s
                GROUP BY 
                    account.id,
                    move.id,
                    line.id,
                     project_site.id,
                     cc.id,
                     currency.id,
                     ae.id
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


class AccountReport(models.Model):
    _inherit = 'account.report'

    def _inject_report_into_xlsx_sheet(self, options, workbook, sheet):
        if options["available_variants"][0][
            "name"] == 'Tasc Deferred Expense Report':
            def write_with_colspan(sheet, x, y, value, colspan, style):
                if colspan == 1:
                    sheet.write(y, x, value, style)
                else:
                    sheet.merge_range(y, x, y, x + colspan - 1, value, style)

            date_default_col1_style = workbook.add_format(
                {'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666',
                 'indent': 2, 'num_format': 'yyyy-mm-dd'})
            date_default_style = workbook.add_format(
                {'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666',
                 'num_format': 'yyyy-mm-dd'})
            default_col1_style = workbook.add_format(
                {'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666',
                 'indent': 2})
            default_style = workbook.add_format(
                {'font_name': 'Arial', 'font_size': 12,
                 'font_color': '#666666'})
            title_style = workbook.add_format(
                {'font_name': 'Arial', 'bold': True, 'bottom': 2})
            level_0_style = workbook.add_format(
                {'font_name': 'Arial', 'bold': True, 'font_size': 13,
                 'bottom': 6,
                 'font_color': '#666666'})
            level_1_style = workbook.add_format(
                {'font_name': 'Arial', 'bold': True, 'font_size': 13,
                 'bottom': 1,
                 'font_color': '#666666'})
            level_2_col1_style = workbook.add_format(
                {'font_name': 'Arial', 'bold': True, 'font_size': 12,
                 'font_color': '#666666', 'indent': 1})
            level_2_col1_total_style = workbook.add_format(
                {'font_name': 'Arial', 'bold': True, 'font_size': 12,
                 'font_color': '#666666'})
            level_2_style = workbook.add_format(
                {'font_name': 'Arial', 'bold': True, 'font_size': 12,
                 'font_color': '#666666'})
            level_3_col1_style = workbook.add_format(
                {'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666',
                 'indent': 2})
            level_3_col1_total_style = workbook.add_format(
                {'font_name': 'Arial', 'bold': True, 'font_size': 12,
                 'font_color': '#666666', 'indent': 1})
            level_3_style = workbook.add_format(
                {'font_name': 'Arial', 'font_size': 12,
                 'font_color': '#666666'})

            print_mode_self = self.with_context(no_format=True)
            lines = self._filter_out_deferred_folded_children(
                print_mode_self._get_lines(options))

            # For reports with lines generated for accounts, the account name and codes are shown in a single column.
            # To help user post-process the report if they need, we should in such a case split the account name and code in two columns.
            account_lines_split_names = {}
            for line in lines:
                line_model = self._get_model_info_from_id(line['id'])[0]
                if line_model == 'account.account':
                    # Reuse the _split_code_name to split the name and code in two values.
                    account_lines_split_names[line['id']] = self.env[
                        'account.account']._split_code_name(line['name'])

            # Set the first column width to 50.
            # If we have account lines and split the name and code in two columns, we will also set the second column.
            if len(account_lines_split_names) > 0:
                sheet.set_column(0, 0, 11)
                sheet.set_column(1, 1, 50)
            else:
                sheet.set_column(0, 0, 50)

            original_x_offset = 1 if len(account_lines_split_names) > 0 else 0

            y_offset = 0
            # 1 and not 0 to leave space for the line name. original_x_offset allows making place for the code column if needed.
            x_offset = original_x_offset + 1

            # Add headers.
            # For this, iterate in the same way as done in main_table_header template
            column_headers_render_data = self._get_column_headers_render_data(
                options)
            for header_level_index, header_level in enumerate(
                    options['column_headers']):
                for header_to_render in header_level * \
                                        column_headers_render_data[
                                            'level_repetitions'][
                                            header_level_index]:
                    colspan = header_to_render.get('colspan',
                                                   column_headers_render_data[
                                                       'level_colspan'][
                                                       header_level_index])
                    write_with_colspan(sheet, x_offset, y_offset,
                                       header_to_render.get('name', ''),
                                       colspan,
                                       title_style)
                    x_offset += colspan
                if options['show_growth_comparison']:
                    write_with_colspan(sheet, x_offset, y_offset, '%', 1,
                                       title_style)
                y_offset += 1
                x_offset = original_x_offset + 1

            for subheader in column_headers_render_data['custom_subheaders']:
                colspan = subheader.get('colspan', 1)
                write_with_colspan(sheet, x_offset, y_offset,
                                   subheader.get('name', ''), colspan,
                                   title_style)
                x_offset += colspan
            y_offset += 1
            x_offset = original_x_offset + 1

            for column in options['columns']:
                colspan = column.get('colspan', 1)
                write_with_colspan(sheet, x_offset, y_offset,
                                   column.get('name', ''), colspan, title_style)
                x_offset += colspan
            y_offset += 1

            if options.get('order_column'):
                lines = self.sort_lines(lines, options)

            # Add lines.
            for y in range(0, len(lines)):
                level = lines[y].get('level')
                if lines[y].get('caret_options'):
                    style = level_3_style
                    col1_style = level_3_col1_style
                elif level == 0:
                    y_offset += 1
                    style = level_0_style
                    col1_style = style
                elif level == 1:
                    style = level_1_style
                    col1_style = style
                elif level == 2:
                    style = level_2_style
                    col1_style = 'total' in lines[y].get('class', '').split(
                        ' ') and level_2_col1_total_style or level_2_col1_style
                elif level == 3:
                    style = level_3_style
                    col1_style = 'total' in lines[y].get('class', '').split(
                        ' ') and level_3_col1_total_style or level_3_col1_style
                else:
                    style = default_style
                    col1_style = default_col1_style

                # write the first column, with a specific style to manage the indentation
                x_offset = original_x_offset + 1
                if lines[y]['id'] in account_lines_split_names:
                    code, name = account_lines_split_names[lines[y]['id']]
                    sheet.write(y + y_offset, x_offset - 2, code, col1_style)
                    sheet.write(y + y_offset, x_offset - 1, name, col1_style)
                else:
                    if lines[y].get('parent_id') and lines[y][
                        'parent_id'] in account_lines_split_names:
                        sheet.write(y + y_offset, x_offset - 2,
                                    account_lines_split_names[
                                        lines[y]['parent_id']][0], col1_style)
                    cell_type, cell_value = self._get_cell_type_value(lines[y])
                    if cell_type == 'date':
                        sheet.write_datetime(y + y_offset, x_offset - 1,
                                             cell_value,
                                             date_default_col1_style)
                    else:
                        sheet.write(y + y_offset, x_offset - 1, cell_value,
                                    col1_style)

                # write all the remaining cells
                columns = lines[y]['columns']
                if options[
                    'show_growth_comparison'] and 'growth_comparison_data' in \
                        lines[y]:
                    columns += [lines[y].get('growth_comparison_data')]
                for x, column in enumerate(columns, start=x_offset):
                    cell_type, cell_value = self._get_cell_type_value(column)
                    if cell_type == 'date':
                        sheet.write_datetime(y + y_offset,
                                             x + lines[y].get('colspan', 1) - 1,
                                             cell_value, date_default_style)
                    else:
                        sheet.write(y + y_offset,
                                    x + lines[y].get('colspan', 1) - 1,
                                    cell_value,
                                    style)

        else:
            super()._inject_report_into_xlsx_sheet(options, workbook, sheet)

    def _filter_out_deferred_folded_children(self, lines):
        """ Returns a list containing all the lines of the provided list that need to be displayed when printing,
        hence removing the children whose parent is folded (especially useful to remove total lines).
        """
        rslt = []
        folded_lines = set()
        for line in lines:
            if line.get('unfoldable') and not line.get('unfolded'):
                folded_lines.add(line['id'])

            # if 'parent_id' not in line or line[
            #     'parent_id'] not in folded_lines:
            rslt.append(line)
        return rslt
