from odoo import models


class AccountGeneralLedgerInherit(models.AbstractModel):
    _inherit = 'account.general.ledger'

    def _get_columns_name(self, options):
        res = super(AccountGeneralLedgerInherit, self)._get_columns_name(
            options)
        res.insert(3, {
            'name': 'Cost Center'
        })
        res.insert(4, {'name': 'Project Site'})
        return res

    def _get_query_amls_from_clause(self):
        res = super(AccountGeneralLedgerInherit,
                    self)._get_query_amls_from_clause()
        res += '''LEFT JOIN account_analytic_account cost_center on cost_center.id = account_move_line.analytic_account_id
                  LEFT JOIN account_analytic_account project_site on project_site.id = account_move_line.project_site_id'''
        return res

    def _get_query_amls_select_clause(self):
        res = super(AccountGeneralLedgerInherit,
                    self)._get_query_amls_select_clause()
        res += ''', cost_center.name                        AS cost_center_name,
                   project_site.name                        AS project_site_name'''
        return res

    def _get_account_title_line(self, options, account, amount_currency, debit,
                                credit, balance, has_lines):
        res = super(AccountGeneralLedgerInherit, self)._get_account_title_line(
            options, account, amount_currency, debit,
            credit, balance, has_lines)
        res['columns'] = [{'name': '', 'class': 'number'},
                          {'name': '', 'class': 'number'}, ] + res['columns']
        return res

    def _get_initial_balance_line(self, options, account, amount_currency,
                                  debit, credit, balance):
        res = super(AccountGeneralLedgerInherit,
                    self)._get_initial_balance_line(options, account,
                                                    amount_currency,
                                                    debit, credit, balance)
        res['columns'] = [{'name': '', 'class': 'number'},
                          {'name': '', 'class': 'number'}, ] + res['columns']
        return res

    def _get_aml_line(self, options, account, aml, cumulated_balance):
        res = super(AccountGeneralLedgerInherit, self)._get_aml_line(options,
                                                                     account,
                                                                     aml,
                                                                     cumulated_balance)
        res['columns'].insert(2, {'name': aml['cost_center_name'],
                                  'class': 'whitespace_print'})
        res['columns'].insert(3, {'name': aml['project_site_name'],
                                  'class': 'whitespace_print'})
        return res

    def _get_account_total_line(self, options, account, amount_currency, debit,
                                credit, balance):
        res = super(AccountGeneralLedgerInherit, self)._get_account_total_line(
            options, account, amount_currency, debit,
            credit, balance)
        res['columns'] = [{'name': '', 'class': 'number'},
                          {'name': '', 'class': 'number'}, ] + res['columns']
        return res
