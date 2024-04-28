from odoo import models, fields, _
from odoo.tools import format_date, get_lang
from collections import defaultdict


class AssetsReportCustomHandler(models.AbstractModel):
    _inherit = 'account.asset.report.handler'

    def _query_values(self, options, prefix_to_match=None,
                      forced_account_id=None):
        "Get the data from the database"

        self.env['account.move.line'].check_access_rights('read')
        self.env['account.asset'].check_access_rights('read')

        move_filter = f"""move.state {"!= 'cancel'" if options.get('all_entries') else "= 'posted'"}"""

        query_params = {
            'date_to': options['date']['date_to'],
            'date_from': options['date']['date_from'],
            'company_ids': tuple
            (self.env['account.report'].get_report_company_ids(options)),
            'include_draft': options.get('all_entries', False),
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
        if options.get('analytic_accounts') and not any \
                    (x in options.get('analytic_accounts_list', []) for x in
                     options['analytic_accounts']):
            analytic_account_ids += \
                [[str(account_id) for account_id in
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

        sql = f"""
            SELECT asset.id AS asset_id,
                   asset.parent_id AS parent_id,
                   asset.name AS asset_name,
                   asset.original_value AS asset_original_value,
                   asset.currency_id AS asset_currency_id,
                   MIN(move.date) AS asset_date,
                   asset.disposal_date AS asset_disposal_date,
                   asset.acquisition_date AS asset_acquisition_date,
                   asset.method AS asset_method,
                   {project_site_name} as project_site,
                   asset.capex_type as capex_type,
                   asset.sequence_number as sequence_number,
                   asset.method_number AS asset_method_number,
                   asset.method_period AS asset_method_period,
                   asset.method_progress_factor AS asset_method_progress_factor,
                   asset.state AS asset_state,
                   asset.company_id AS company_id,
                   account.code AS account_code,
                   account.name AS account_name,
                   account.id AS account_id,
                   COALESCE(SUM(move.depreciation_value) FILTER (WHERE move.date < %(date_from)s AND {move_filter}), 0) + COALESCE(asset.already_depreciated_amount_import, 0) AS depreciated_before,
                   COALESCE(SUM(move.depreciation_value) FILTER (WHERE move.date BETWEEN %(date_from)s AND %(date_to)s AND {move_filter}), 0) AS depreciated_during
              FROM account_asset AS asset
         LEFT JOIN account_account AS account ON asset.account_asset_id = account.id
         LEFT JOIN account_move move ON move.asset_id = asset.id
         LEFT JOIN account_move reversal ON reversal.reversed_entry_id = move.id
         LEFT JOIN account_analytic_account as project_sites on asset.project_site_id = project_sites.id  
             WHERE asset.company_id in %(company_ids)s
               AND (asset.acquisition_date <= %(date_to)s OR move.date <= %(date_to)s)
               AND (asset.disposal_date >= %(date_from)s OR asset.disposal_date IS NULL)
               AND (asset.state not in ('model', 'draft', 'cancelled') OR (asset.state = 'draft' AND %(include_draft)s))
               AND asset.active = 't'
               AND reversal.id IS NULL
               {prefix_query}
               {account_query}
               {analytical_query}
          GROUP BY asset.id, account.id,project_sites.id
          ORDER BY account.code, asset.acquisition_date;
        """

        self._cr.execute(sql, query_params)
        results = self._cr.dictfetchall()
        return results

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
                asset_depreciation_rate = " ".join(part for part in [
                    years and _("%s y", years),
                    months and _("%s m", months),
                ] if part)
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

            asset_opening = al['asset_original_value'] if opening else 0.0
            asset_add = 0.0 if opening else al['asset_original_value']
            asset_minus = 0.0

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
            if al['asset_state'] == 'close' and al['asset_disposal_date'] and \
                    al['asset_disposal_date'] <= fields.Date.to_date(
                options['date']['date_to']) and al_currency.compare_amounts(
                depreciation_closing, asset_closing) == 0:
                depreciation_minus += depreciation_closing
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
            else:
                apex_type = ''

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
            }

            lines.append(
                (al['account_id'], al['asset_id'], columns_by_expr_label))
        return lines
