from odoo import models, fields
from itertools import chain


class MulticurrencyRevaluationReportInherit(models.AbstractModel):
    _inherit = 'account.multicurrency.revaluation.report.handler'

    def _multi_currency_revaluation_get_custom_lines(self, options, line_code, current_groupby, next_groupby, offset=0, limit=None):
        def build_result_dict(report, query_res):
            return {
                'balance_currency': query_res['balance_currency'] if len(query_res['currency_id']) == 1 else None,
                'currency_id': query_res['currency_id'][0] if len(query_res['currency_id']) == 1 else None,
                'balance_operation': query_res['balance_operation'],
                'balance_current': query_res['balance_current'],
                'adjustment': query_res['adjustment'],
                'has_sublines': query_res['aml_count'] > 0,
            }

        report = self.env['account.report'].browse(options['report_id'])
        report._check_groupby_fields((next_groupby.split(',') if next_groupby else []) + ([current_groupby] if current_groupby else []))

        # No need to run any SQL if we're computing the main line: it does not display any total
        if not current_groupby:
            return {
                'balance_currency': None,
                'currency_id': None,
                'balance_operation': None,
                'balance_current': None,
                'adjustment': None,
                'has_sublines': False,
            }

        query = "(VALUES {})".format(', '.join("(%s, %s)" for rate in options['currency_rates']))
        params = list(chain.from_iterable((cur['currency_id'], cur['rate']) for cur in options['currency_rates'].values()))
        custom_currency_table_query = self.env.cr.mogrify(query, params).decode(self.env.cr.connection.encoding)
        select_part_exchange_move_id = """
            SELECT part.exchange_move_id
              FROM account_partial_reconcile part
             WHERE part.exchange_move_id IS NOT NULL
               AND part.max_date <= %s
        """

        date_to = fields.Date.from_string(options['date']['date_to'])
        tables, where_clause, where_params = report._query_get(options, 'strict_range')
        tail_query, tail_params = report._get_engine_query_tail(offset, limit)
        full_query = f"""
            WITH custom_currency_table(currency_id, rate) AS ({custom_currency_table_query}),
                 -- The amount_residuals_by_aml_id will have all moves that have at least one partial at a certain date
                 amount_residuals_by_aml_id AS (
                    -- We compute the amount_residual and amount_residual_currency of customer invoices by taking the date into account
                    -- And we keep the aml_id and currency_id to help us do a join later in the query
                    SELECT aml.balance - SUM(part.amount) AS amount_residual,
                           ROUND(
                               aml.amount_currency - SUM(part.debit_amount_currency),
                               curr.decimal_places
                           ) AS amount_residual_currency,
                           aml.currency_id AS currency_id,
                           aml.id AS aml_id
                      FROM account_move_line aml
                      JOIN account_partial_reconcile part ON aml.id = part.debit_move_id
                      JOIN res_currency curr ON curr.id = part.debit_currency_id
                      JOIN account_account account ON aml.account_id = account.id
                     WHERE (
                             account.currency_id != aml.company_currency_id
                             OR (
                                 account.account_type IN ('asset_receivable', 'liability_payable')
                                 AND (aml.currency_id != aml.company_currency_id)
                                )
                           )
                       AND part.max_date <= %s
                       AND account.account_type NOT IN ('income', 'income_other', 'expense', 'expense_depreciation', 'expense_direct_cost', 'off_balance')
                  GROUP BY aml_id,
                           curr.decimal_places

                 UNION
                    -- We compute the amount_residual and amount_residual_currency of a bill by taking the date into account
                    -- And we keep the aml_id and currency_id to help us do a join later in the query
                    SELECT aml.balance + SUM(part.amount) AS amount_residual,
                           ROUND(
                               aml.amount_currency + SUM(part.credit_amount_currency),
                               curr.decimal_places
                           ) AS amount_residual_currency,
                           aml.currency_id AS currency_id,
                           aml.id AS aml_id
                      FROM account_move_line aml
                      JOIN account_partial_reconcile part ON aml.id = part.credit_move_id
                      JOIN res_currency curr ON curr.id = part.credit_currency_id
                      JOIN account_account account ON aml.account_id = account.id
                     WHERE (
                             account.currency_id != aml.company_currency_id
                             OR (
                                 account.account_type IN ('asset_receivable', 'liability_payable')
                                 AND (aml.currency_id != aml.company_currency_id)
                                )
                           )
                       AND part.max_date <= %s
                       AND account.account_type NOT IN ('income', 'income_other', 'expense', 'expense_depreciation', 'expense_direct_cost', 'off_balance')
                  GROUP BY aml_id,
                           curr.decimal_places
                 )
            -- Final select that gets the following lines: 
            -- (where there is a change in the rates of currency between the creation of the move and the full payments)
            -- - Moves that don't have a payment yet at a certain date
            -- - Moves that have a partial but are not fully paid at a certain date
            SELECT
                   subquery.grouping_key,
                   ARRAY_AGG(DISTINCT(subquery.currency_id)) AS currency_id,
                   SUM(subquery.balance_currency) AS balance_currency,
                   SUM(subquery.balance_operation) AS balance_operation,
                   SUM(subquery.balance_current) AS balance_current,
                   SUM(subquery.adjustment) AS adjustment,
                   COUNT(subquery.aml_id) AS aml_count
              FROM (
                -- From the amount_residuals_by_aml_id we will get all the necessary information for our report 
                -- for moves that have at least one partial at a certain date, and in this select we add the condition
                -- that the move is not fully paid.
                SELECT
                       """ + (f"account_move_line.{current_groupby} AS grouping_key," if current_groupby else '') + f"""
                       ara.amount_residual AS balance_operation,
                       ara.amount_residual_currency AS balance_currency,
                       ara.amount_residual_currency / custom_currency_table.rate AS balance_current,
                       ara.amount_residual_currency / custom_currency_table.rate - ara.amount_residual AS adjustment,
                       ara.currency_id AS currency_id,
                       ara.aml_id AS aml_id
                  FROM {tables}
                  JOIN amount_residuals_by_aml_id ara ON ara.aml_id = account_move_line.id
                  JOIN custom_currency_table ON custom_currency_table.currency_id = ara.currency_id
                 WHERE {where_clause}
                   AND (account_move_line.move_id NOT IN ({select_part_exchange_move_id}))
                   AND (ara.amount_residual != 0 OR ara.amount_residual_currency != 0)
                   AND {'NOT EXISTS' if line_code == 'to_adjust' else 'EXISTS'} (
                        SELECT * FROM account_account_exclude_res_currency_provision WHERE account_account_id = account_id AND res_currency_id = account_move_line.currency_id
                    )

                UNION
                -- Moves that don't have a payment yet at a certain date
                SELECT
                       """ + (f"account_move_line.{current_groupby} AS grouping_key," if current_groupby else '') + f"""
                       account_move_line.balance AS balance_operation,
                       account_move_line.amount_currency AS balance_currency,
                       account_move_line.amount_currency / custom_currency_table.rate AS balance_current,
                       account_move_line.amount_currency / custom_currency_table.rate - account_move_line.balance AS adjustment,
                       account_move_line.currency_id AS currency_id,
                       account_move_line.id AS aml_id
                  FROM {tables}
             LEFT JOIN amount_residuals_by_aml_id ara ON ara.aml_id = account_move_line.id
                  JOIN account_account account ON account_move_line.account_id = account.id
                  JOIN res_currency currency ON currency.id = account_move_line.currency_id
                  JOIN custom_currency_table ON custom_currency_table.currency_id = currency.id
                 WHERE {where_clause}
                   AND (
                         account.currency_id != account_move_line.company_currency_id
                         OR (
                             account.account_type IN ('asset_receivable', 'liability_payable','asset_cash','asset_current','asset_prepayments','liability_current')
                             AND (account_move_line.currency_id != account_move_line.company_currency_id)
                            )
                       )
                   AND (account_move_line.move_id NOT IN ({select_part_exchange_move_id}))
                   AND {'NOT EXISTS' if line_code == 'to_adjust' else 'EXISTS'} (
                        SELECT * FROM account_account_exclude_res_currency_provision WHERE account_account_id = account_id AND res_currency_id = account_move_line.currency_id
                    )
                   AND account.account_type NOT IN ('income', 'income_other', 'expense', 'expense_depreciation', 'expense_direct_cost', 'off_balance')
                   AND ara IS NULL

            ) subquery

            GROUP BY grouping_key
            {tail_query}
        """
        params = [
            date_to,  # For Customer Invoice in amount_residuals_by_aml_id
            date_to,  # For Vendor Bill in amount_residuals_by_aml_id
            *where_params,  # First params for where_clause
            date_to,  # Date to for first call of select_part_exchange_move_id
            *where_params,  # Second params for where_clause
            date_to,  # Date to for the second call of select_part_exchange_move_id
            *tail_params,
        ]
        self._cr.execute(full_query, params)
        query_res_lines = self._cr.dictfetchall()

        if not current_groupby:
            return build_result_dict(report, query_res_lines and query_res_lines[0] or {})
        else:
            rslt = []
            for query_res in query_res_lines:
                grouping_key = query_res['grouping_key']
                rslt.append((grouping_key, build_result_dict(report, query_res)))
            return rslt
