from odoo import api, models,fields,osv


class AccountReport(models.AbstractModel):
    _inherit = 'account.report'

    filter_budgets = fields.Boolean(
        string="Budgets",
        compute=lambda x: x._compute_report_option_filter('filter_budgets'), readonly=False, store=True, depends=['root_report_id', 'section_main_report_ids'],
    )

    def _get_filter_budgets(self, options, additional_domain=None):
        return self.env['crossovered.budget'].with_context(active_test=False).search([
                *self.env['crossovered.budget']._check_company_domain(self.get_report_company_ids(options)),
                *(additional_domain or []),
            ], order="company_id, name")

    @api.model
    def _query_get(self, options, date_scope, domain=None):
        if options.get('report', False) and options['report'] == 'tasc_budget_analysis':
            self.env['crossovered.budget.lines'].check_access_rights('read')

            query = self.env['crossovered.budget.lines']._where_calc(domain)
            # Wrap the query with 'company_id IN (...)' to avoid bypassing company access rights.
            self.env['crossovered.budget.lines']._apply_ir_rules(query)

            return query.get_sql()
        else:
            domain = self._get_options_domain(options, date_scope) + (
                        domain or [])
            if options.get('forced_domain'):
                # That option key is set when splitting options between column groups
                domain += options['forced_domain']

            self.env['account.move.line'].check_access_rights('read')

            query = self.env['account.move.line']._where_calc(domain)

            # Wrap the query with 'company_id IN (...)' to avoid bypassing company access rights.
            self.env['account.move.line']._apply_ir_rules(query)
            return query.get_sql()
