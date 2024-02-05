# -*- coding: utf-8 -*-


from odoo import models, fields, api


class AccountReport(models.AbstractModel):
    _inherit = 'account.report'

    @api.model
    def _init_filter_analytic(self, options, previous_options=None):
        super(AccountReport, self)._init_filter_analytic( options, previous_options)
        if not self.filter_analytic:
            return

        if self.user_has_groups('analytic.group_analytic_accounting'):
            options['project_site_ids'] = previous_options and previous_options.get('project_site_ids') or []
            project_site_ids = [int(acc) for acc in options['project_site_ids']]
            selected_project_sites = project_site_ids and self.env['account.analytic.account'].browse(project_site_ids) or self.env['account.analytic.account']
            options['selected_project_sites'] = selected_project_sites.mapped('name')

            options['type_ids'] = previous_options and previous_options.get('type_ids') or []
            type_ids = [int(acc) for acc in options['type_ids']]
            selected_types = type_ids and self.env['account.analytic.account'].browse(type_ids) or self.env[
                'account.analytic.account']
            options['selected_types'] = selected_types.mapped('name')

            options['location_ids'] = previous_options and previous_options.get('location_ids') or []
            location_ids = [int(acc) for acc in options['location_ids']]
            selected_locations = location_ids and self.env['account.analytic.account'].browse(location_ids) or self.env[
                'account.analytic.account']
            options['selected_locations'] = selected_locations.mapped('name')


    @api.model
    def _get_options_analytic_domain(self, options):
        domain = super(AccountReport, self)._get_options_analytic_domain(options)
        if options.get('project_site_ids'):
            project_site_ids = [int(acc) for acc in options['project_site_ids']]
            domain.append(('project_site_id', 'in', project_site_ids))
        if options.get('type_ids'):
            type_ids = [int(acc) for acc in options['type_ids']]
            domain.append(('type_id', 'in', type_ids))
        if options.get('location_ids'):
            location_ids = [int(acc) for acc in options['location_ids']]
            domain.append(('location_id', 'in', location_ids))

        return domain

    def _set_context(self, options):
        ctx = super(AccountReport, self)._set_context(options)
        if options.get('project_site_ids'):
            ctx['project_site_ids'] = self.env['account.analytic.account'].browse([int(project) for project in options['project_site_ids']])
        if options.get('type_ids'):
            ctx['type_ids'] = self.env['account.analytic.account'].browse([int(t) for t in options['type_ids']])
        if options.get('location_ids'):
            ctx['location_ids'] = self.env['account.analytic.account'].browse([int(l) for l in options['location_ids']])

        return ctx

    def get_report_informations(self, options):
        '''
        return a dictionary of informations that will be needed by the js widget, manager_id, footnotes, html of report and searchview, ...
        '''
        options = self._get_options(options)

        searchview_dict = {'options': options, 'context': self.env.context}
        # Check if report needs analytic

        if options.get('analytic_accounts') is not None:
            options['selected_analytic_account_names'] = [self.env['account.analytic.account'].browse(int(account)).name
                                                          for account in options['analytic_accounts']]
        if options.get('analytic_tags') is not None:
            options['selected_analytic_tag_names'] = [self.env['account.analytic.tag'].browse(int(tag)).name for tag in
                                                      options['analytic_tags']]
        if options.get('partner'):
            options['selected_partner_ids'] = [self.env['res.partner'].browse(int(partner)).name for partner in
                                               options['partner_ids']]
            options['selected_partner_categories'] = [self.env['res.partner.category'].browse(int(category)).name for
                                                      category in options['partner_categories']]

        if options.get('project_site_ids') is not None:
            options['selected_project_sites'] = [self.env['account.analytic.account'].browse(int(project)).name for project in
                                              options['project_site_ids']]
        if options.get('type_ids') is not None:
            options['selected_types'] = [self.env['account.analytic.account'].browse(int(project)).name for project in
                                              options['type_ids']]
        if options.get('location_ids') is not None:
            options['selected_locations'] = [self.env['account.analytic.account'].browse(int(project)).name for project in
                                              options['location_ids']]

        # Check whether there are unposted entries for the selected period or not (if the report allows it)
        if options.get('date') and options.get('all_entries') is not None:
            date_to = options['date'].get('date_to') or options['date'].get('date') or fields.Date.today()
            period_domain = [('state', '=', 'draft'), ('date', '<=', date_to)]
            options['unposted_in_period'] = bool(self.env['account.move'].search_count(period_domain))

        if options.get('journals'):
            journals_selected = set(journal['id'] for journal in options['journals'] if journal.get('selected'))
            for journal_group in self.env['account.journal.group'].search([('company_id', '=', self.env.company.id)]):
                if journals_selected and journals_selected == set(self._get_filter_journals().ids) - set(
                        journal_group.excluded_journal_ids.ids):
                    options['name_journal_group'] = journal_group.name
                    break

        report_manager = self._get_report_manager(options)
        info = {'options': options,
                'context': self.env.context,
                'report_manager_id': report_manager.id,
                'footnotes': [{'id': f.id, 'line': f.line, 'text': f.text} for f in report_manager.footnotes_ids],
                'buttons': self._get_reports_buttons_in_sequence(),
                'main_html': self.get_html(options),
                'searchview_html': self.env['ir.ui.view']._render_template(
                    self._get_templates().get('search_template', 'account_report.search_template'),
                    values=searchview_dict),
                }
        return info
