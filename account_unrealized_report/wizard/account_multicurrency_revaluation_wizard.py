from odoo import api, models, fields,Command,_
from odoo.tools import format_date


class AccountMulticurrencyRevaluationWizard(models.TransientModel):
    _name = 'account.multicurrency.revaluation.wizard'
    _inherit = ['account.multicurrency.revaluation.wizard', 'analytic.mixin']


    analytic_account_id = fields.Many2one('account.analytic.account',
                                          string="Cost Center")
    business_unit_id = fields.Many2one('account.analytic.account',
                                       domain=[('plan_id.name', '=ilike', 'Business Unit')],
                                       string="Business Unit")
    project_site_id = fields.Many2one('account.analytic.account',
                                      string="Project Site",domain=[('analytic_account_type', '=',
                                               'project_site')],)
    analytic_distribution = fields.Json()


    @api.onchange('project_site_id', 'analytic_account_id','business_unit_id')
    def onchange_project_site(self):
        analytic_dist = {}
        analytic_distributions = ''
        if self.analytic_account_id:
            analytic_distributions = analytic_distributions + ',' + str(
                self.analytic_account_id.id)
        if self.business_unit_id:
            analytic_distributions = analytic_distributions + ',' + str(
                self.business_unit_id.id)
        if self.project_site_id:
            analytic_distributions = analytic_distributions + ',' + str(
                self.project_site_id.id)
        if self.project_site_id.analytic_type_filter_id:
            analytic_distributions = analytic_distributions + ',' + str(
                self.project_site_id.analytic_type_filter_id.id)
        if self.project_site_id.analytic_location_id:
            analytic_distributions = analytic_distributions + ',' + str(
                self.project_site_id.analytic_location_id.id)
        if self.project_site_id.co_location:
            analytic_distributions = analytic_distributions + ',' + str(
                self.project_site_id.co_location.id)
        a = analytic_distributions.strip()
        b = a.strip(",")
        analytic_dist.update({b: 100})
        self.analytic_distribution = analytic_dist


    @api.model
    def _get_move_vals(self):
        def _get_model_id(parsed_line, selected_model):
            for dummy, parsed_res_model, parsed_res_id in parsed_line:
                if parsed_res_model == selected_model:
                    return parsed_res_id

        def _get_adjustment_balance(line):
            for column in line.get('columns'):
                if column.get('expression_label') == 'adjustment':
                    return column.get('no_format')

        report = self.env.ref('account_reports.multicurrency_revaluation_report')
        included_line_id = report.line_ids.filtered(lambda l: l.code == 'multicurrency_included').id
        generic_included_line_id = report._get_generic_line_id('account.report.line', included_line_id)
        options = {**self._context['multicurrency_revaluation_report_options'], 'unfold_all': False}
        report_lines = report._get_lines(options)
        move_lines = []

        for report_line in report._get_unfolded_lines(report_lines, generic_included_line_id):
            parsed_line_id = report._parse_line_id(report_line.get('id'))
            balance = _get_adjustment_balance(report_line)
            # parsed_line_id[-1][-2] corresponds to res_model of the current line
            if (
                parsed_line_id[-1][-2] == 'account.account'
                and not self.env.company.currency_id.is_zero(balance)
            ):
                account_id = _get_model_id(parsed_line_id, 'account.account')
                currency_id = _get_model_id(parsed_line_id, 'res.currency')
                move_lines.append(Command.create({
                    'name': _(
                        "Provision for %(for_cur)s (1 %(comp_cur)s = %(rate)s %(for_cur)s)",
                        for_cur=self.env['res.currency'].browse(currency_id).display_name,
                        comp_cur=self.env.company.currency_id.display_name,
                        rate=options['currency_rates'][str(currency_id)]['rate']
                    ),
                    'debit': balance if balance > 0 else 0,
                    'credit': -balance if balance < 0 else 0,
                    'analytic_account_id':self.analytic_account_id.id,
                    'project_site_id': self.project_site_id.id,
                    'analytic_distribution': self.analytic_distribution,
                    'amount_currency': 0,
                    'currency_id': currency_id,
                    'account_id': account_id,
                }))
                if balance < 0:
                    move_line_name = _("Expense Provision for %s", self.env['res.currency'].browse(currency_id).display_name)
                else:
                    move_line_name = _("Income Provision for %s", self.env['res.currency'].browse(currency_id).display_name)
                move_lines.append(Command.create({
                    'name': move_line_name,
                    'debit': -balance if balance < 0 else 0,
                    'credit': balance if balance > 0 else 0,
                    'amount_currency': 0,
                    'currency_id': currency_id,
                    'analytic_account_id': self.analytic_account_id.id,
                    'project_site_id': self.project_site_id.id,
                    'analytic_distribution': self.analytic_distribution,
                    'account_id': self.expense_provision_account_id.id if balance < 0 else self.income_provision_account_id.id,
                }))

        return {
            'ref': _("Foreign currencies adjustment entry as of %s", format_date(self.env, self.date)),
            'journal_id': self.journal_id.id,
            'date': self.date,
            'line_ids': move_lines,
        }