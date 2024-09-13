# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import io
from odoo import fields, models, _
from odoo.tools import format_date, get_lang, profile
from odoo.tools.misc import xlsxwriter
from collections import defaultdict

MAX_NAME_LENGTH = 50


class AssetsReportCustomHandler(models.AbstractModel):
    _name = 'account.asset.report.depreciation.schedule.handler'
    _inherit = 'account.report.custom.handler'
    _description = 'Depreciation Schedule Report Custom Handler'

    def _get_custom_display_config(self):
        return {
            'client_css_custom_class': 'depreciation_schedule',
            'templates': {
                'AccountReportFilters': 'account_asset.DepreciationScheduleFilters',
            }
        }

    def _dynamic_lines_generator(self, report, options,
                                 all_column_groups_expression_totals,
                                 warnings=None):
        report = self._with_context_company2code2account(report)

        lines, totals_by_column_group = self._generate_report_lines_without_grouping(
            report, options)
        if options["available_variants"][0][
            "name"] == 'Tasc Depreciation Schedule':

            if self.env.context.get('is_xlsx'):
                # add the groups by account

                # options['assets_groupby_account'] = True
                # if options['assets_groupby_account']:
                #     lines = self._group_by_account(report, lines, options)
                # else:
                lines = report._regroup_lines_by_name_prefix(options, lines,
                                                             '_report_expand_unfoldable_line_assets_report_prefix_group',
                                                             0)
        else:
            # add the groups by account

            options['assets_groupby_account'] = True
            if options['assets_groupby_account']:
                lines = self._group_by_account(report, lines, options)
            else:
                lines = report._regroup_lines_by_name_prefix(options, lines,
                                                             '_report_expand_unfoldable_line_assets_report_prefix_group',
                                                             0)

        # add the groups by account

        # add the total line
        total_columns = []
        for column_data in options['columns']:
            col_value = totals_by_column_group[
                column_data['column_group_key']].get(
                column_data['expression_label'])
            col_value = col_value if column_data.get(
                'figure_type') == 'monetary' else ''

            total_columns.append(
                report._build_column_dict(col_value, column_data,
                                          options=options))

        if lines:
            lines.append({
                'id': report._get_generic_line_id(None, None, markup='total'),
                'level': 1,
                'name': _('Total'),
                'columns': total_columns,
                'unfoldable': False,
                'unfolded': False,
            })

        return [(0, line) for line in lines]

    def _generate_report_lines_without_grouping(self, report, options,
                                                prefix_to_match=None,
                                                parent_id=None,
                                                forced_account_id=None):
        # construct a dictionary:
        #   {(account_id, asset_id): {col_group_key: {expression_label_1: value, expression_label_2: value, ...}}}
        all_asset_ids = set()
        all_lines_data = {}
        for column_group_key, column_group_options in report._split_options_per_column_group(
                options).items():
            # the lines returned are already sorted by account_id!
            lines_query_results = self._query_lines(column_group_options,
                                                    prefix_to_match=prefix_to_match,
                                                    forced_account_id=forced_account_id)
            for account_id, asset_id, cols_by_expr_label in lines_query_results:
                line_id = (account_id, asset_id)
                all_asset_ids.add(asset_id)
                if line_id not in all_lines_data:
                    all_lines_data[line_id] = {column_group_key: []}
                all_lines_data[line_id][column_group_key] = cols_by_expr_label

        column_names = [
            'assets_date_from', 'assets_plus', 'assets_minus', 'assets_date_to',
            'depre_date_from',
            'depre_plus', 'depre_minus', 'depre_date_to', 'balance'
        ]
        totals_by_column_group = defaultdict(
            lambda: dict.fromkeys(column_names, 0.0))

        # Browse all the necessary assets in one go, to minimize the number of queries
        assets_cache = {asset.id: asset for asset in
                        self.env['account.asset'].browse(all_asset_ids)}

        # construct the lines, 1 at a time
        lines = []
        company_currency = self.env.company.currency_id
        for (account_id, asset_id), col_group_totals in all_lines_data.items():
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

                # add to the total line
                if column_data['figure_type'] == 'monetary':
                    totals_by_column_group[column_data['column_group_key']][
                        column_data['expression_label']] += col_value

            name = assets_cache[asset_id].name
            line = {
                'id': report._get_generic_line_id('account.asset', asset_id,
                                                  parent_line_id=parent_id),
                'level': 2,
                'name': name,
                'columns': all_columns,
                'unfoldable': False,
                'unfolded': False,
                'caret_options': 'account_asset_line',
                'assets_account_id': account_id,
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
            'account_asset_line': [
                {'name': _("Open Asset"),
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
            if col['expression_label'] in ['assets_date_from',
                                           'depre_date_from']:
                col['name'] = format_date(self.env,
                                          column_group_options['date'][
                                              'date_from'])
            elif col['expression_label'] in ['assets_date_to', 'depre_date_to']:
                col['name'] = format_date(self.env,
                                          column_group_options['date'][
                                              'date_to'])

        options['custom_columns_subheaders'] = [
            {"name": _("Characteristics"), "colspan": 15},
            {"name": _("Assets"), "colspan": 4},
            {"name": _("Depreciation"), "colspan": 4},
            {"name": _("Book Value"), "colspan": 1}
        ]

        # Group by account by default
        groupby_activated = (previous_options or {}).get(
            'assets_groupby_account', False)
        options['assets_groupby_account'] = groupby_activated
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
        asset_lines = self._query_values(options,
                                         prefix_to_match=prefix_to_match,
                                         forced_account_id=forced_account_id)

        # Assign the gross increases sub assets to their main asset (parent)
        parent_lines = []
        children_lines = defaultdict(list)
        for al in asset_lines:
            if al['parent_id']:
                children_lines[al['parent_id']] += [al]
            else:
                parent_lines += [al]

        for al in parent_lines:
            # Compute the depreciation rate string
            if al['asset_method'] == 'linear' and al[
                'asset_method_number']:  # some assets might have 0 depreciations because they dont lose value
                total_months = int(al['asset_method_number']) * int(
                    al['asset_method_period'])
                months = total_months % 12
                years = total_months // 12
                # asset_depreciation_rate = " ".join(part for part in [
                #     years and _("%s y", years),
                #     months and _("%s m", months),
                # ] if part)
                asset_depreciation_rate = " ".join(_("%s m", total_months))
            elif al['asset_method'] == 'linear':
                asset_depreciation_rate = '0.00 %'
            else:
                asset_depreciation_rate = ('{:.2f} %').format(
                    float(al['asset_method_progress_factor']) * 100)

            # Manage the opening of the asset
            opening = (al['asset_acquisition_date'] or al[
                'asset_date']) < fields.Date.to_date(
                options['date']['date_from'])

            # Get the main values of the board for the asset
            depreciation_opening = al['depreciated_before']
            depreciation_add = al['depreciated_during']
            depreciation_minus = 0.0

            asset_disposal_value = al['asset_disposal_value'] if al[
                                                                     'asset_disposal_date'] and \
                                                                 al[
                                                                     'asset_disposal_date'] <= fields.Date.to_date(
                options['date']['date_to']) else 0.0

            asset_opening = al['asset_original_value'] if opening else 0.0
            asset_add = 0.0 if opening else al['asset_original_value']
            asset_minus = 0.0
            asset_salvage_value = al.get('asset_salvage_value', 0.0)

            # Add the main values of the board for all the sub assets (gross increases)
            for child in children_lines[al['asset_id']]:
                depreciation_opening += child['depreciated_before']
                depreciation_add += child['depreciated_during']

                opening = (child['asset_acquisition_date'] or child[
                    'asset_date']) < fields.Date.to_date(
                    options['date']['date_from'])
                asset_opening += child[
                    'asset_original_value'] if opening else 0.0
                asset_add += 0.0 if opening else child['asset_original_value']

            # Compute the closing values
            asset_closing = asset_opening + asset_add - asset_minus
            depreciation_closing = depreciation_opening + depreciation_add - depreciation_minus
            al_currency = self.env['res.currency'].browse(
                al['asset_currency_id'])

            # Manage the closing of the asset
            if (
                    al['asset_state'] == 'close'
                    and al['asset_disposal_date']
                    and al['asset_disposal_date'] <= fields.Date.to_date(
                options['date']['date_to'])
                    and al_currency.compare_amounts(depreciation_closing,
                                                    asset_closing - asset_salvage_value) == 0
            ):
                depreciation_add -= asset_disposal_value
                depreciation_minus += depreciation_closing - asset_disposal_value
                depreciation_closing = 0.0
                asset_minus += asset_closing
                asset_closing = 0.0

            # Manage negative assets (credit notes)
            if al['asset_original_value'] < 0:
                asset_add, asset_minus = -asset_minus, -asset_add
                depreciation_add, depreciation_minus = -depreciation_minus, -depreciation_add

            if al["capex_type"] == 'replacement_capex':
                apex_type = 'Replacement CAPEX'
            elif al["capex_type"] == 'tenant_capex':
                apex_type = 'Tenant upgrade CAPEX'
            elif al["capex_type"] == 'expansion_capex':
                apex_type = 'Expansion CAPEX'
            elif al["capex_type"] == '5g_capex':
                apex_type = '5G CAPEX'
            elif al["capex_type"] == 'other_capex':
                apex_type = 'Other CAPEX'
            elif al["capex_type"] == 'transferred_capex':
                apex_type = 'Transferred CAPEX'
            else:
                apex_type = ''

            if al["asset_state"] == 'draft':
                status = 'Draft'
            elif al["asset_state"] == 'model':
                status = 'Model'
            elif al["asset_state"] == 'open':
                status = 'Running'
            elif al["asset_state"] == 'paused':
                status = 'On Hold'
            elif al["asset_state"] == 'close':
                status = 'Closed'
            elif al["asset_state"] == 'cancelled':
                status = 'Cancelled'
            elif al["asset_state"] == 'to_approve':
                status = 'To Approve'
            else:
                status = ''
            # Format the data
            columns_by_expr_label = {
                "acquisition_date": al[
                                        "asset_acquisition_date"] and format_date(
                    self.env, al["asset_acquisition_date"]) or "",
                # Characteristics
                "first_depreciation": al["asset_date"] and format_date(self.env,
                                                                       al[
                                                                           "asset_date"]) or "",
                "method": (al["asset_method"] == "linear" and _("Linear")) or (
                        al["asset_method"] == "degressive" and _(
                    "Declining")) or _("Dec. then Straight"),
                "duration_rate": asset_depreciation_rate,
                "assets_date_from": asset_opening,
                "assets_plus": asset_add,
                "assets_minus": asset_minus,
                "assets_date_to": asset_closing,
                "depre_date_from": depreciation_opening,
                "depre_plus": depreciation_add,
                "depre_minus": depreciation_minus,
                "depre_date_to": depreciation_closing,
                "balance": asset_closing - depreciation_closing,
                "project_site": al["project_site"],
                "capex_type": apex_type,
                "asset_sequence_number": al["sequence_number"],
                "co_location": al["co_location"],
                "asset_model": al["asset_model_name"],
                "status": status,
                "fixed_asset_account": al["account_code"] + "-" + al[
                    "account_name"],
                "currency": al["currency_name"],
                "serial_no": al["serial_no"],
                "additional_info": al["additional_info"],
                "last_depreciation_date": al["last_depreciation_date"]
            }

            lines.append(
                (al['account_id'], al['asset_id'], columns_by_expr_label))
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
            parent_account_id = line.get('assets_account_id')

            model, res_id = report._get_model_info_from_id(line['id'])
            assert model == 'account.asset'

            # replace the line['id'] to add the account.account.id
            line['id'] = report._build_line_id([
                (None, 'account.account', parent_account_id),
                (None, 'account.asset', res_id)
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
                '_report_expand_unfoldable_line_assets_report_prefix_group',
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
        self.env['account.asset'].check_access_rights('read')

        move_filter = f"""move.state {"!= 'cancel'" if options.get('all_entries') else "= 'posted'"}"""
        query_params = {
            'date_to': options['date']['date_to'],
            'date_from': options['date']['date_from'],
            'company_ids': tuple(
                self.env['account.report'].get_report_company_ids(options)),
            'include_draft': options.get('all_entries', False),
            'limit': 100,
            'offset': 0,
        }
        prefix_query = ''
        if prefix_to_match:
            prefix_query = "AND asset.name ILIKE %(prefix_to_match)s"
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
            analytic_account_ids += [[str(account_id) for account_id in
                                      options['analytic_accounts']]]
        if options.get('analytic_accounts_list'):
            analytic_account_ids += [[str(account_id) for account_id in
                                      options.get('analytic_accounts_list')]]
        if analytic_account_ids:
            analytical_query = 'AND asset.analytic_distribution ?| array[%(analytic_account_ids)s]'
            query_params['analytic_account_ids'] = analytic_account_ids

        lang = self.env.user.lang or get_lang(self.env).code
        project_site_name = f"COALESCE(project_sites.name->>'{lang}', project_sites.name->>'en_US')" if \
            self.pool[
                'account.analytic.account'].name.translate else 'project_sites.name'
        co_loc_name = f"COALESCE(co_locations.name->>'{lang}', co_locations.name->>'en_US')" if \
            self.pool[
                'account.analytic.account'].name.translate else 'co_locations.name'

        if self.env.context.get('is_xlsx'):
            sql = f"""SELECT 
                                asset.id AS asset_id, 
                                asset.parent_id AS parent_id, 
                                asset.name AS asset_name, 
                                asset.serial_no as serial_no, 
                                asset.original_value AS asset_original_value, 
                                asset.currency_id AS asset_currency_id, 
                                COALESCE(asset.salvage_value, 0) as asset_salvage_value, 
                                MIN(move.date) AS asset_date, 
                                asset.disposal_date AS asset_disposal_date, 
                                asset.acquisition_date AS asset_acquisition_date, 
                                asset.method AS asset_method, 
                                COALESCE(project_sites.name ->> 'en_US', '') as project_site, 
                                COALESCE(co_locations.name ->> 'en_US', '') as co_location, 
                                asset.capex_type as capex_type, 
                                asset.sequence_number as sequence_number, 
                                asset.additional_info as additional_info, 
                                asset.method_number AS asset_method_number, 
                                asset.method_period AS asset_method_period, 
                                asset.method_progress_factor AS asset_method_progress_factor, 
                                asset.state AS asset_state, 
                                asset.company_id AS company_id, 
                                account.code AS account_code, 
                                COALESCE(account.name ->> 'en_US', '') as account_name, 
                                account.id AS account_id, 
                                model.name as asset_model_name,
                                currency.name as currency_name,
                                COALESCE(
                                  SUM(move.depreciation_value) FILTER (
                                    WHERE move.date <  %(date_from)s AND move.state = 'posted' AND {move_filter}
                                  ), 0
                                ) + COALESCE(asset.already_depreciated_amount_import, 0) AS depreciated_before, 
                                COALESCE(
                                  SUM(move.depreciation_value) FILTER (
                                    WHERE move.date BETWEEN %(date_from)s AND %(date_to)s AND {move_filter} AND move.state = 'posted'
                                  ), 0
                                ) AS depreciated_during, 
                                COALESCE(
                                  SUM(move.depreciation_value) FILTER (
                                    WHERE move.date BETWEEN %(date_from)s AND %(date_to)s AND {move_filter} AND move.state = 'posted'
                                  ), 0
                                ) AS asset_disposal_value ,
                                (
                                SELECT MAX(move_sub.date)
                                FROM account_move move_sub
                                WHERE move_sub.asset_id = asset.id
                              ) AS last_depreciation_date
                              FROM 
                                account_asset asset 
                                LEFT JOIN account_account account ON asset.account_asset_id = account.id 
                                LEFT JOIN account_analytic_account project_sites ON asset.project_site_id = project_sites.id 
                                LEFT JOIN account_analytic_account co_locations ON asset.co_location = co_locations.id 
                                LEFT JOIN account_move move ON move.asset_id = asset.id 
                                LEFT JOIN account_asset model ON model.id = asset.model_id
                                LEFT JOIN res_currency as currency ON asset.currency_id = currency.id
                              WHERE 
                                asset.active 
                                AND (asset.disposal_date >=  %(date_from)s OR asset.disposal_date IS NULL)
                                AND asset.company_id in %(company_ids)s
                                AND asset.state NOT IN ('model', 'draft', 'cancelled') 
                                AND (asset.acquisition_date <= %(date_to)s OR move.date <= %(date_to)s)
                                AND asset.active = 't'
                              GROUP BY 
                                asset.id, 
                                account.id, 
                                currency.id,
                                project_sites.id, 
                                co_locations.id, 
                                model.name
                              """
            self._cr.execute(sql, query_params)
            results = self._cr.dictfetchall()
            return results
        else:

            sql = f"""SELECT 
                      asset.id AS asset_id, 
                      asset.parent_id AS parent_id, 
                      asset.name AS asset_name, 
                      asset.serial_no as serial_no, 
                      asset.original_value AS asset_original_value, 
                      asset.currency_id AS asset_currency_id, 
                      COALESCE(asset.salvage_value, 0) as asset_salvage_value, 
                      MIN(move.date) AS asset_date, 
                      asset.disposal_date AS asset_disposal_date, 
                      asset.acquisition_date AS asset_acquisition_date, 
                      asset.method AS asset_method, 
                      COALESCE(project_sites.name ->> 'en_US', '') as project_site, 
                      COALESCE(co_locations.name ->> 'en_US', '') as co_location, 
                      asset.capex_type as capex_type, 
                      asset.sequence_number as sequence_number, 
                      asset.additional_info as additional_info, 
                      asset.method_number AS asset_method_number, 
                      asset.method_period AS asset_method_period, 
                      asset.method_progress_factor AS asset_method_progress_factor, 
                      asset.state AS asset_state, 
                      asset.company_id AS company_id, 
                      account.code AS account_code, 
                      COALESCE(account.name ->> 'en_US', '') as account_name, 
                      account.id AS account_id, 
                      model.name as asset_model_name,
                      currency.name as currency_name,
                      COALESCE(
                        SUM(move.depreciation_value) FILTER (
                          WHERE move.date <  %(date_from)s AND move.state = 'posted' AND {move_filter}
                        ), 0
                      ) + COALESCE(asset.already_depreciated_amount_import, 0) AS depreciated_before, 
                      COALESCE(
                        SUM(move.depreciation_value) FILTER (
                          WHERE move.date BETWEEN %(date_from)s AND %(date_to)s AND {move_filter} AND move.state = 'posted'
                        ), 0
                      ) AS depreciated_during, 
                      COALESCE(
                        SUM(move.depreciation_value) FILTER (
                          WHERE move.date BETWEEN %(date_from)s AND %(date_to)s AND {move_filter} AND move.state = 'posted'
                        ), 0
                      ) AS asset_disposal_value ,
                      	  (
		SELECT MAX(move_sub.date)
		FROM account_move move_sub
		WHERE move_sub.asset_id = asset.id
	  ) AS last_depreciation_date
                    FROM 
                      account_asset asset 
                      LEFT JOIN account_account account ON asset.account_asset_id = account.id 
                      LEFT JOIN account_analytic_account project_sites ON asset.project_site_id = project_sites.id 
                      LEFT JOIN account_analytic_account co_locations ON asset.co_location = co_locations.id 
                      LEFT JOIN account_move move ON move.asset_id = asset.id 
                      LEFT JOIN account_asset model ON model.id = asset.model_id
                      LEFT JOIN res_currency currency ON asset.currency_id= currency.id
                    WHERE 
                      asset.active 
                      AND (asset.disposal_date >=  %(date_from)s OR asset.disposal_date IS NULL)
                      AND asset.company_id in %(company_ids)s
                      AND asset.state NOT IN ('model', 'draft', 'cancelled') 
                      AND (asset.acquisition_date <= %(date_to)s OR move.date <= %(date_to)s)
                      AND asset.active = 't'
                    GROUP BY 
                      asset.id, 
                      account.id, 
                      currency.id,
                      project_sites.id, 
                      co_locations.id, 
                      model.name
                    LIMIT 100;"""
            self._cr.execute(sql, query_params)
            results = self._cr.dictfetchall()
            return results

    def _report_expand_unfoldable_line_assets_report_prefix_group(self,
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
                'account.report']._get_res_id_from_line_id(line_dict_id,
                                                           'account.account'),
        )

        lines = report._regroup_lines_by_name_prefix(
            options,
            lines,
            '_report_expand_unfoldable_line_assets_report_prefix_group',
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

    def _init_options_buttons(self, options, previous_options=None):
        if options["available_variants"][0][
            "name"] == 'Tasc Depreciation Schedule':
            options['buttons'] = [
                {'name': _('PDF'), 'sequence': 10, 'action': 'export_file',
                 'action_param': 'export_to_pdf', 'file_export_type': _('PDF'),
                 'branch_allowed': True},
                {'name': _('XLSX'), 'sequence': 20, 'action': 'export_file',
                 'action_param': 'export_to_xlsx', 'file_export_type': _('XLSX'),
                 'branch_allowed': True},
                {'name': _('TASC XLSX'), 'sequence': 20, 'action': 'export_file',
                 'action_param': 'tasc_export_to_xlsx',
                 'file_export_type': _('XLSX'),
                 'branch_allowed': True},
                {'name': _('Save'), 'sequence': 100,
                 'action': 'open_report_export_wizard'},
            ]
        else:
            options['buttons'] = [
                {'name': _('PDF'), 'sequence': 10, 'action': 'export_file',
                 'action_param': 'export_to_pdf', 'file_export_type': _('PDF'),
                 'branch_allowed': True},
                {'name': _('XLSX'), 'sequence': 20, 'action': 'export_file',
                 'action_param': 'export_to_xlsx',
                 'file_export_type': _('XLSX'),
                 'branch_allowed': True},
                {'name': _('Save'), 'sequence': 100,
                 'action': 'open_report_export_wizard'},
            ]

    def split_list(self, lst, limit):
        return [lst[i:i + limit] for i in range(0, len(lst), limit)]

    def tasc_export_to_xlsx(self, options, response=None):
        self.ensure_one()
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {
            'in_memory': True,
            'strings_to_formulas': False,
        })

        print_options = self.get_options(
            previous_options={**options, 'export_mode': 'print'})
        if print_options['sections']:
            reports_to_print = self.env['account.report'].browse(
                [section['id'] for section in print_options['sections']])
        else:
            reports_to_print = self
        reports_options = []
        for report in reports_to_print:
            report_options = report.get_options(
                previous_options={**print_options,
                                  'selected_section_id': report.id})
            reports_options.append(report_options)

            # report._inject_report_into_xlsx_sheet(report_options, workbook, workbook.add_worksheet(report.name[:31]))
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
            self.env['account.move.line'].check_access_rights('read')
            self.env['account.asset'].check_access_rights('read')

            move_filter = f"""move.state {"!= 'cancel'" if options.get('all_entries') else "= 'posted'"}"""
            query_params = {
                'date_to': options['date']['date_to'],
                'date_from': options['date']['date_from'],
                'company_ids': tuple(
                    self.env['account.report'].get_report_company_ids(options)),
                'include_draft': options.get('all_entries', False),
                'limit': 100,
                'offset': 0,
            }

            sql = f"""SELECT 
                                asset.id AS asset_id, 
                                asset.parent_id AS parent_id, 
                                asset.name AS asset_name, 
                                asset.serial_no as serial_no, 
                                asset.original_value AS asset_original_value, 
                                asset.currency_id AS asset_currency_id, 
                                COALESCE(asset.salvage_value, 0) as asset_salvage_value, 
                                MIN(move.date) AS asset_date, 
                                asset.disposal_date AS asset_disposal_date, 
                                asset.acquisition_date AS asset_acquisition_date, 
                                asset.method AS asset_method, 
                                COALESCE(project_sites.name ->> 'en_US', '') as project_site, 
                                COALESCE(co_locations.name ->> 'en_US', '') as co_location, 
                                asset.capex_type as capex_type, 
                                asset.sequence_number as sequence_number, 
                                asset.additional_info as additional_info, 
                                asset.method_number AS asset_method_number, 
                                asset.method_period AS asset_method_period, 
                                asset.method_progress_factor AS asset_method_progress_factor, 
                                asset.state AS asset_state, 
                                asset.company_id AS company_id, 
                                account.code AS account_code, 
                                COALESCE(account.name ->> 'en_US', '') as account_name, 
                                account.id AS account_id, 
                                model.name as asset_model_name,
                                currency.name as currency_name,
                                COALESCE(
                                  SUM(move.depreciation_value) FILTER (
                                    WHERE move.date <  %(date_from)s AND move.state = 'posted' AND {move_filter}
                                  ), 0
                                ) + COALESCE(asset.already_depreciated_amount_import, 0) AS depreciated_before, 
                                COALESCE(
                                  SUM(move.depreciation_value) FILTER (
                                    WHERE move.date BETWEEN %(date_from)s AND %(date_to)s AND {move_filter} AND move.state = 'posted'
                                  ), 0
                                ) AS depreciated_during, 
                                COALESCE(
                                  SUM(move.depreciation_value) FILTER (
                                    WHERE move.date BETWEEN %(date_from)s AND %(date_to)s AND {move_filter} AND move.state = 'posted'
                                  ), 0
                                ) AS asset_disposal_value 
                              FROM 
                                account_asset asset 
                                LEFT JOIN account_account account ON asset.account_asset_id = account.id 
                                LEFT JOIN account_analytic_account project_sites ON asset.project_site_id = project_sites.id 
                                LEFT JOIN account_analytic_account co_locations ON asset.co_location = co_locations.id 
                                LEFT JOIN account_move move ON move.asset_id = asset.id 
                                LEFT JOIN account_asset model ON model.id = asset.model_id
                                LEFT JOIN res_currency as currency ON asset.currency_id = currency.id
                              WHERE 
                                asset.active 
                                AND (asset.disposal_date >=  %(date_from)s OR asset.disposal_date IS NULL)
                                AND asset.company_id in %(company_ids)s
                                AND asset.state NOT IN ('model', 'draft', 'cancelled') 
                                AND (asset.acquisition_date <= %(date_to)s OR move.date <= %(date_to)s)
                                AND asset.active = 't'
                              GROUP BY 
                                asset.id, 
                                account.id, 
                                currency.id,
                                project_sites.id, 
                                co_locations.id, 
                                model.name
                              """
            self._cr.execute(sql, query_params)
            results = self._cr.dictfetchall()
            sublists = self.split_list(results, 40000)

            j = 0
            for sub in sublists:
                sheet = workbook.add_worksheet('Sheet ' + str(j))

                account_lines_split_names = {}
                if len(account_lines_split_names) > 0:
                    sheet.set_column(0, 0, 11)
                    sheet.set_column(1, 1, 50)
                else:
                    sheet.set_column(0, 0, 50)

                original_x_offset = 1 if len(
                    account_lines_split_names) > 0 else 0

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

                for subheader in column_headers_render_data[
                    'custom_subheaders']:
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
                                       column.get('name', ''), colspan,
                                       title_style)
                    x_offset += colspan
                y_offset += 1
                j += 1
                for i in sub:
                    opening = (i['asset_acquisition_date'] or i[
                        'asset_date']) < fields.Date.to_date(
                        options['date']['date_from'])

                    # Get the main values of the board for the asset
                    depreciation_opening = i['depreciated_before']
                    depreciation_add = i['depreciated_during']
                    depreciation_minus = 0.0

                    asset_disposal_value = i['asset_disposal_value'] if i[
                                                                            'asset_disposal_date'] and \
                                                                        i[
                                                                            'asset_disposal_date'] <= fields.Date.to_date(
                        options['date']['date_to']) else 0.0

                    asset_opening = i[
                        'asset_original_value'] if opening else 0.0
                    asset_add = 0.0 if opening else i['asset_original_value']
                    asset_minus = 0.0
                    asset_salvage_value = i.get('asset_salvage_value', 0.0)

                    # Add the main values of the board for all the sub assets (gross increases)
                    # children_lines = defaultdict(list)
                    children_lines = [d for d in results if
                                      d.get('parent_id') == i['asset_id']]
                    # for al in asset_lines:
                    #     if al['parent_id']:
                    #         children_lines[al['parent_id']] += [al]

                    for child in children_lines:
                        depreciation_opening += child['depreciated_before']
                        depreciation_add += child['depreciated_during']

                        opening = (child['asset_acquisition_date'] or child[
                            'asset_date']) < fields.Date.to_date(
                            options['date']['date_from'])
                        asset_opening += child[
                            'asset_original_value'] if opening else 0.0
                        asset_add += 0.0 if opening else child[
                            'asset_original_value']

                    # Compute the closing values
                    asset_closing = asset_opening + asset_add - asset_minus
                    depreciation_closing = depreciation_opening + depreciation_add - depreciation_minus
                    al_currency = self.env['res.currency'].browse(
                        i['asset_currency_id'])

                    # Manage the closing of the asset
                    if (
                            i['asset_state'] == 'close'
                            and i['asset_disposal_date']
                            and i[
                        'asset_disposal_date'] <= fields.Date.to_date(
                        options['date']['date_to'])
                            and al_currency.compare_amounts(
                        depreciation_closing,
                        asset_closing - asset_salvage_value) == 0
                    ):
                        depreciation_add -= asset_disposal_value
                        depreciation_minus += depreciation_closing - asset_disposal_value
                        depreciation_closing = 0.0
                        asset_minus += asset_closing
                        asset_closing = 0.0

                    # Manage negative assets (credit notes)
                    if i['asset_original_value'] < 0:
                        asset_add, asset_minus = -asset_minus, -asset_add
                        depreciation_add, depreciation_minus = -depreciation_minus, -depreciation_add

                    if i["capex_type"] == 'replacement_capex':
                        apex_type = 'Replacement CAPEX'
                    elif i["capex_type"] == 'tenant_capex':
                        apex_type = 'Tenant upgrade CAPEX'
                    elif i["capex_type"] == 'expansion_capex':
                        apex_type = 'Expansion CAPEX'
                    elif i["capex_type"] == '5g_capex':
                        apex_type = '5G CAPEX'
                    elif i["capex_type"] == 'other_capex':
                        apex_type = 'Other CAPEX'
                    elif i["capex_type"] == 'transferred_capex':
                        apex_type = 'Transferred CAPEX'
                    else:
                        apex_type = ''

                    if i["asset_state"] == 'draft':
                        status = 'Draft'
                    elif i["asset_state"] == 'model':
                        status = 'Model'
                    elif i["asset_state"] == 'open':
                        status = 'Running'
                    elif i["asset_state"] == 'paused':
                        status = 'On Hold'
                    elif i["asset_state"] == 'close':
                        status = 'Closed'
                    elif i["asset_state"] == 'cancelled':
                        status = 'Cancelled'
                    elif i["asset_state"] == 'to_approve':
                        status = 'To Approve'
                    else:
                        status = ''

                    x_offset = 0
                    sheet.write(y_offset, x_offset, i['asset_name'],
                                date_default_col1_style)
                    x_offset += 1
                    sheet.write(y_offset, x_offset,
                                i['asset_model_name'],
                                date_default_col1_style)
                    x_offset += 1
                    sheet.write(y_offset, x_offset,
                                status,
                                default_style)
                    x_offset += 1
                    sheet.write(y_offset, x_offset,
                                i['asset_acquisition_date'] and format_date(
                                    self.env,
                                    i["asset_acquisition_date"]) or "",
                                date_default_col1_style)
                    x_offset += 1

                    sheet.write(y_offset, x_offset,
                                i['account_code'] + i['account_name'],
                                date_default_col1_style)
                    x_offset += 1

                    sheet.write(y_offset, x_offset,
                                i['project_site'],
                                date_default_col1_style)
                    x_offset += 1
                    sheet.write(y_offset, x_offset,
                                i['co_location'],
                                date_default_col1_style)
                    x_offset += 1
                    sheet.write(y_offset, x_offset,
                                i['currency_name'],
                                date_default_col1_style)
                    x_offset += 1
                    sheet.write(y_offset, x_offset,
                                apex_type,
                                date_default_col1_style)
                    x_offset += 1
                    sheet.write(y_offset, x_offset,
                                i['sequence_number'],
                                date_default_col1_style)
                    x_offset += 1
                    sheet.write(y_offset, x_offset,
                                i['serial_no'],
                                date_default_col1_style)
                    x_offset += 1
                    sheet.write(y_offset, x_offset,
                                i['additional_info'],
                                date_default_col1_style)
                    x_offset += 1
                    sheet.write(y_offset, x_offset,
                                i['asset_date'] and format_date(
                                    self.env, i["asset_date"]) or "",
                                date_default_col1_style)
                    x_offset += 1
                    sheet.write(y_offset, x_offset,
                                (i["asset_method"] == "linear" and _(
                                    "Linear")) or (
                                        i[
                                            "asset_method"] == "degressive" and _(
                                    "Declining")) or _("Dec. then Straight"),
                                date_default_col1_style)
                    x_offset += 1

                    if i['asset_method'] == 'linear' and i[
                        'asset_method_number']:  # some assets might have 0 depreciations because they dont lose value
                        total_months = int(i['asset_method_number']) * int(
                            i['asset_method_period'])
                        asset_depreciation_rate = " ".join(
                            _("%s m", total_months))
                    elif i['asset_method'] == 'linear':
                        asset_depreciation_rate = '0.00 %'
                    else:
                        asset_depreciation_rate = ('{:.2f} %').format(
                            float(i['asset_method_progress_factor']) * 100)

                    sheet.write(y_offset, x_offset,
                                asset_depreciation_rate,
                                date_default_col1_style)
                    x_offset += 1

                    sheet.write(y_offset, x_offset,
                                asset_opening,
                                default_style)
                    x_offset += 1
                    sheet.write(y_offset, x_offset,
                                asset_add,
                                default_style)
                    x_offset += 1
                    sheet.write(y_offset, x_offset,
                                asset_minus,
                                default_style)
                    x_offset += 1
                    sheet.write(y_offset, x_offset,
                                asset_closing,
                                default_style)
                    x_offset += 1

                    sheet.write(y_offset, x_offset,
                                depreciation_opening,
                                default_style)
                    x_offset += 1
                    sheet.write(y_offset, x_offset,
                                depreciation_add,
                                default_style)
                    x_offset += 1
                    sheet.write(y_offset, x_offset,
                                depreciation_minus,
                                default_style)
                    x_offset += 1
                    sheet.write(y_offset, x_offset,
                                depreciation_closing,
                                default_style)
                    x_offset += 1
                    sheet.write(y_offset, x_offset,
                                asset_closing - depreciation_closing,
                                default_style)
                    x_offset += 1
                    y_offset += 1

        self._add_options_xlsx_sheet(workbook, reports_options)

        workbook.close()
        output.seek(0)
        generated_file = output.read()
        output.close()

        return {
            'file_name': self.get_default_report_filename(options, 'xlsx'),
            'file_content': generated_file,
            'file_type': 'xlsx',
        }

    def _inject_report_into_xlsx_sheet(self, options, workbook, sheet):
        if options["available_variants"][0][
            "name"] == 'Tasc Depreciation Schedule':
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

            print_mode_self = self.with_context(no_format=True, is_xlsx=True)
            lines = self._filter_out_depreciation_schedule_folded_children(
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

    def _filter_out_depreciation_schedule_folded_children(self, lines):
        """ Returns a list containing all the lines of the provided list that need to be displayed when printing,
        hence removing the children whose parent is folded (especially useful to remove total lines).
        """
        rslt = []
        folded_lines = set()
        for line in lines:
            if line.get('unfoldable') and not line.get('unfolded'):
                folded_lines.add(line['id'])

            # if 'parent_id' not in line or line['parent_id'] not in folded_lines:
            rslt.append(line)
        return rslt
