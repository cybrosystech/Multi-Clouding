# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.addons.web.controllers.main import clean_action


class analytic_report(models.AbstractModel):
    _inherit = 'account.analytic.report'




    @api.model
    def _get_lines(self, options, line_id=None):
        AccountAnalyticGroup = self.env['account.analytic.group']
        lines = []
        parent_group = AccountAnalyticGroup
        date_from = options['date']['date_from']
        date_to = options['date']['date_to']

        # context is set because it's used for the debit, credit and balance computed fields
        AccountAnalyticAccount = self.env['account.analytic.account'].with_context(from_date=date_from,
                                                                                   to_date=date_to)
        # The options refer to analytic entries. So first determine
        # the subset of analytic categories we have to search in.
        analytic_entries_domain = [('date', '>=', date_from),
                                   ('date', '<=', date_to)]
        analytic_account_domain = []
        analytic_account_ids = []
        analytic_tag_ids = []
        analytic_ids =  []
        if options['analytic_accounts']:
            analytic_account_ids = [int(id) for id in options['analytic_accounts']]
            analytic_entries_domain += [('account_id', 'in', analytic_account_ids)]
            analytic_ids +=analytic_account_ids
        if options['project_site_ids']:
            analytic_account_ids = [int(id) for id in options['project_site_ids']]
            analytic_entries_domain += [('project_site_id', 'in', analytic_account_ids)]
            analytic_ids +=analytic_account_ids
        if options['type_ids']:
            analytic_account_ids = [int(id) for id in options['type_ids']]
            analytic_entries_domain += [('type_id', 'in', analytic_account_ids)]
            analytic_ids +=analytic_account_ids
        if options['location_ids']:
            analytic_account_ids = [int(id) for id in options['location_ids']]
            analytic_entries_domain += [('location_id', 'in', analytic_account_ids)]
            analytic_ids +=analytic_account_ids
        if analytic_ids:
            analytic_account_domain += [('id', 'in', analytic_ids)]

        if options.get('analytic_tags'):
            analytic_tag_ids = [int(id) for id in options['analytic_tags']]
            analytic_entries_domain += [('tag_ids', 'in', analytic_tag_ids)]
            AccountAnalyticAccount = AccountAnalyticAccount.with_context(tag_ids=analytic_tag_ids)

        if options.get('multi_company'):
            company_ids = self.env.companies.ids
        else:
            company_ids = self.env.company.ids

        analytic_account_domain += ['|', ('company_id', 'in', company_ids), ('company_id', '=', False)]

        if not options.get('hierarchy'):
            return self._generate_analytic_account_lines(AccountAnalyticAccount.search(analytic_account_domain))

        # display all groups that have accounts
        analytic_accounts = AccountAnalyticAccount.search(analytic_account_domain)
        analytic_groups = analytic_accounts.mapped('group_id')

        # also include the parent analytic groups, even if they didn't have a child analytic line
        if analytic_groups:
            analytic_groups = AccountAnalyticGroup.search([('id', 'parent_of', analytic_groups.ids)])

        domain = [('id', 'in', analytic_groups.ids)]

        if line_id:
            parent_group = AccountAnalyticGroup if line_id == self.DUMMY_GROUP_ID else AccountAnalyticGroup.browse(int(line_id))
            domain += [('parent_id', '=', parent_group.id)]

            # the engine replaces line_id with what is returned so
            # first re-render the line that was just clicked
            lines.append(self._generate_analytic_group_line(parent_group, analytic_entries_domain, unfolded=True))

            # append analytic accounts part of this group, taking into account the selected options
            analytic_account_domain += [('group_id', '=', parent_group.id)]

            analytic_accounts = AccountAnalyticAccount.search(analytic_account_domain)
            lines += self._generate_analytic_account_lines(analytic_accounts, parent_group.id if parent_group else self.DUMMY_GROUP_ID)
        else:
            domain += [('parent_id', '=', False)]

        # append children groups unless the dummy group has been clicked, it has no children
        if line_id != self.DUMMY_GROUP_ID:
            for group in AccountAnalyticGroup.search(domain):
                if group.id in options.get('unfolded_lines') or options.get('unfold_all'):
                    lines += self._get_lines(options, line_id=str(group.id))
                else:
                    lines.append(self._generate_analytic_group_line(group, analytic_entries_domain))

        # finally append a 'dummy' group which contains the accounts that do not have an analytic group
        if not line_id and any(not account.group_id for account in analytic_accounts):
            if self.DUMMY_GROUP_ID in options.get('unfolded_lines'):
                lines += self._get_lines(options, line_id=self.DUMMY_GROUP_ID)
            else:
                lines.append(self._generate_analytic_group_line(AccountAnalyticGroup, analytic_entries_domain))

        return lines
