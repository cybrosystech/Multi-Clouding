# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import ast
import copy
import json
import io
import logging
import lxml.html
import datetime
import ast
from collections import defaultdict
from math import copysign

from dateutil.relativedelta import relativedelta

from odoo.tools.misc import xlsxwriter
from odoo import models, fields, api, _
from odoo.tools import config, date_utils, get_lang
from odoo.osv import expression
from babel.dates import get_quarter_names
from odoo.tools.misc import formatLang, format_date
from odoo.addons.web.controllers.main import clean_action

_logger = logging.getLogger(__name__)


class AccountReport(models.AbstractModel):
    _inherit = 'account.report'

    ####################################################
    # OPTIONS: analytic
    ####################################################

    @api.model
    def _init_filter_analytic(self, options, previous_options=None):
        if not self.filter_analytic:
            return

        options['analytic'] = self.filter_analytic

        if self.user_has_groups('analytic.group_analytic_accounting'):
            options['analytic_accounts'] = previous_options and previous_options.get('analytic_accounts') or []
            analytic_account_ids = [int(acc) for acc in options['analytic_accounts']]
            selected_analytic_accounts = analytic_account_ids \
                                         and self.env['account.analytic.account'].browse(analytic_account_ids) \
                                         or self.env['account.analytic.account']
            options['selected_analytic_account_names'] = selected_analytic_accounts.mapped('name')

            # Analytic Account Project
            options['analytic_accounts_project'] = previous_options and previous_options.get('analytic_accounts_project') or []
            analytic_account_project_ids = [int(acc) for acc in options['analytic_accounts_project']]
            selected_analytic_accounts_project = analytic_account_ids \
                                         and self.env['account.analytic.account'].browse(analytic_account_project_ids) \
                                         or self.env['account.analytic.account']
            options['selected_analytic_account_project_names'] = selected_analytic_accounts_project.mapped('name')


        if self.user_has_groups('analytic.group_analytic_tags'):
            options['analytic_tags'] = previous_options and previous_options.get('analytic_tags') or []
            analytic_tag_ids = [int(tag) for tag in options['analytic_tags']]
            selected_analytic_tags = analytic_tag_ids \
                                     and self.env['account.analytic.tag'].browse(analytic_tag_ids) \
                                     or self.env['account.analytic.tag']
            options['selected_analytic_tag_names'] = selected_analytic_tags.mapped('name')

    @api.model
    def _get_options_analytic_domain(self, options):
        domain = []
        if options.get('analytic_accounts'):
            analytic_account_ids = [int(acc) for acc in options['analytic_accounts']]
            domain.append(('analytic_account_id', 'in', analytic_account_ids))

        #analytic account Project
        if options.get('analytic_accounts_project'):
            analytic_account_project_ids = [int(acc) for acc in options['analytic_accounts_project']]
            domain.append(('analytic_account_project_id', 'in', analytic_account_project_ids))

        if options.get('analytic_tags'):
            analytic_tag_ids = [int(tag) for tag in options['analytic_tags']]
            domain.append(('analytic_tag_ids', 'in', analytic_tag_ids))
        return domain


    def open_journal_items(self, options, params):
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_line_select")
        action = clean_action(action, env=self.env)
        ctx = self.env.context.copy()
        if params and 'id' in params:
            active_id = params['id']
            ctx.update({
                    'search_default_account_id': [active_id],
            })

        if options:
            if options.get('journals'):
                selected_journals = [journal['id'] for journal in options['journals'] if journal.get('selected')]
                if selected_journals: # Otherwise, nothing is selected, so we want to display everything
                    ctx.update({
                        'search_default_journal_id': selected_journals,
                    })

            domain = expression.normalize_domain(ast.literal_eval(action.get('domain') or '[]'))
            if options.get('analytic_accounts'):
                analytic_ids = [int(r) for r in options['analytic_accounts']]
                domain = expression.AND([domain, [('analytic_account_id', 'in', analytic_ids)]])

            #Analytic Account Project
            if options.get('analytic_accounts_project'):
                analytic_project_ids = [int(r) for r in options['analytic_accounts_project']]
                domain = expression.AND([domain, [('project_site_id', 'in', analytic_project_ids)]])

            if options.get('date'):
                opt_date = options['date']
                if opt_date.get('date_from'):
                    domain = expression.AND([domain, [('date', '>=', opt_date['date_from'])]])
                if opt_date.get('date_to'):
                    domain = expression.AND([domain, [('date', '<=', opt_date['date_to'])]])
                if not opt_date.keys() & {'date_from', 'date_to'} and opt_date.get('date'):
                    domain = expression.AND([domain, [('date', '<=', opt_date['date'])]])
            # In case the line has been generated for a "group by" financial line, append the parent line's domain to the one we created
            if params.get('financial_group_line_id'):
                # In case the hierarchy is enabled, 'financial_group_line_id' might be a string such
                # as 'hierarchy_xxx'. This will obviously cause a crash at domain evaluation.
                if not (isinstance(params['financial_group_line_id'], str) and 'hierarchy_' in params['financial_group_line_id']):
                    parent_financial_report_line = self.env['account.financial.html.report.line'].browse(params['financial_group_line_id'])
                    domain = expression.AND([domain, ast.literal_eval(parent_financial_report_line.domain)])

            if not options.get('all_entries'):
                ctx['search_default_posted'] = True

            action['domain'] = domain
        action['context'] = ctx
        return action


    def _set_context(self, options):
        """This method will set information inside the context based on the options dict as some options need to be in context for the query_get method defined in account_move_line"""
        ctx = self.env.context.copy()
        if options.get('date') and options['date'].get('date_from'):
            ctx['date_from'] = options['date']['date_from']
        if options.get('date'):
            ctx['date_to'] = options['date'].get('date_to') or options['date'].get('date')
        if options.get('all_entries') is not None:
            ctx['state'] = options.get('all_entries') and 'all' or 'posted'
        if options.get('journals'):
            ctx['journal_ids'] = [j.get('id') for j in options.get('journals') if j.get('selected')]
        if options.get('analytic_accounts'):
            ctx['analytic_account_ids'] = self.env['account.analytic.account'].browse([int(acc) for acc in options['analytic_accounts']])

        #Analytic Account Project
        if options.get('analytic_accounts_project'):
            ctx['analytic_account_project_ids'] = self.env['account.analytic.account'].browse([int(acc) for acc in options['analytic_accounts_project']])

        if options.get('analytic_tags'):
            ctx['analytic_tag_ids'] = self.env['account.analytic.tag'].browse([int(t) for t in options['analytic_tags']])
        if options.get('partner_ids'):
            ctx['partner_ids'] = self.env['res.partner'].browse([int(partner) for partner in options['partner_ids']])
        if options.get('partner_categories'):
            ctx['partner_categories'] = self.env['res.partner.category'].browse([int(category) for category in options['partner_categories']])
        if not ctx.get('allowed_company_ids') or not options.get('multi_company'):
            """Contrary to the generic multi_company strategy,
            If we have not specified multiple companies, we only use
            the user company for account reports.

            To do so, we set the allowed_company_ids to only the main current company
            so that self.env.company == self.env.companies
            """
            ctx['allowed_company_ids'] = self.env.company.ids
        return ctx

    def get_report_informations(self, options):
        '''
        return a dictionary of informations that will be needed by the js widget, manager_id, footnotes, html of report and searchview, ...
        '''
        options = self._get_options(options)

        searchview_dict = {'options': options, 'context': self.env.context}
        # Check if report needs analytic
        if options.get('analytic_accounts') is not None:
            options['selected_analytic_account_names'] = [self.env['account.analytic.account'].browse(int(account)).name for account in options['analytic_accounts']]

        #Analytic Account Project
        if options.get('analytic_accounts_project') is not None:
            options['selected_analytic_account_project_names'] = [self.env['account.analytic.account'].browse(int(account)).name for account in options['analytic_accounts_project']]

        if options.get('analytic_tags') is not None:
            options['selected_analytic_tag_names'] = [self.env['account.analytic.tag'].browse(int(tag)).name for tag in options['analytic_tags']]
        if options.get('partner'):
            options['selected_partner_ids'] = [self.env['res.partner'].browse(int(partner)).name for partner in options['partner_ids']]
            options['selected_partner_categories'] = [self.env['res.partner.category'].browse(int(category)).name for category in (options.get('partner_categories') or [])]

        # Check whether there are unposted entries for the selected period or not (if the report allows it)
        if options.get('date') and options.get('all_entries') is not None:
            date_to = options['date'].get('date_to') or options['date'].get('date') or fields.Date.today()
            period_domain = [('state', '=', 'draft'), ('date', '<=', date_to)]
            options['unposted_in_period'] = bool(self.env['account.move'].search_count(period_domain))

        if options.get('journals'):
            journals_selected = set(journal['id'] for journal in options['journals'] if journal.get('selected'))
            for journal_group in self.env['account.journal.group'].search([('company_id', '=', self.env.company.id)]):
                if journals_selected and journals_selected == set(self._get_filter_journals().ids) - set(journal_group.excluded_journal_ids.ids):
                    options['name_journal_group'] = journal_group.name
                    break

        report_manager = self._get_report_manager(options)
        info = {'options': options,
                'context': self.env.context,
                'report_manager_id': report_manager.id,
                'footnotes': [{'id': f.id, 'line': f.line, 'text': f.text} for f in report_manager.footnotes_ids],
                'buttons': self._get_reports_buttons_in_sequence(),
                'main_html': self.get_html(options),
                'searchview_html': self.env['ir.ui.view']._render_template(self._get_templates().get('search_template', 'account_report.search_template'), values=searchview_dict),
                }
        return info


# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.tools.misc import format_date
from odoo.tools.safe_eval import safe_eval
from odoo.osv import expression

from collections import defaultdict, namedtuple

HierarchyDetail = namedtuple('HierarchyDetail', ['field', 'foldable', 'lazy', 'section_total', 'namespan'])
ColumnDetail = namedtuple('ColumnDetail', ['name', 'classes', 'getter', 'formatter'])


class AccountingReport(models.AbstractModel):
    _inherit = 'account.accounting.report'
    analytic_account_project_id = fields.Many2one('account.analytic.account')

    def _get_move_line_fields(self, aml_alias="account_move_line"):
        return ', '.join('%s.%s' % (aml_alias, field) for field in (
            'id',
            'move_id',
            'name',
            'account_id',
            'journal_id',
            'company_id',
            'currency_id',
            'analytic_account_id',
            'project_site_id',
            'display_type',
            'date',
            'debit',
            'credit',
            'balance',
        ))






