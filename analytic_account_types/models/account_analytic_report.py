# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict
from odoo import api, fields, models
from odoo.osv import expression


class Acc(models.Model):
    _inherit = 'account.analytic.account'

    crossovered_budget_proj_line = fields.One2many('crossovered.budget.lines',
                                                   'project_site_id',
                                                   'Budget Lines')
    crossovered_budget_type_line = fields.One2many('crossovered.budget.lines',
                                                   'type_id', 'Budget Lines')
    crossovered_budget_loc_line = fields.One2many('crossovered.budget.lines',
                                                  'location_id', 'Budget Lines')
    analytic_location_id = fields.Many2one(
        comodel_name="account.analytic.account", string="Location",
        required=False, domain=[('analytic_account_type', '=', 'location')], )
    analytic_type_filter_id = fields.Many2one(
        comodel_name="account.analytic.account", string="Type", required=False,
        domain=[('analytic_account_type', '=', 'type')], )

    site_address = fields.Char(string='Site Address')
    group = fields.Selection([
        ('managed', 'Managed'),
        ('owned', 'Owned')], 'Group',)

    @api.depends('line_ids.amount')
    def _compute_debit_credit_balance(self):
        Curr = self.env['res.currency']
        analytic_line_obj = self.env['account.analytic.line']
        domain = [
            ('account_id', 'in', self.ids),
        ]
        if self._context.get('from_date', False):
            domain.append(('date', '>=', self._context['from_date']))
        if self._context.get('to_date', False):
            domain.append(('date', '<=', self._context['to_date']))
        if self._context.get('tag_ids'):
            tag_domain = expression.OR([[('tag_ids', 'in', [tag])] for tag in
                                        self._context['tag_ids']])
            domain = expression.AND([domain, tag_domain])

        user_currency = self.env.company.currency_id
        credit_groups = analytic_line_obj.read_group(
            domain=domain + [('amount', '>=', 0.0)],
            fields=['account_id', 'currency_id', 'amount'],
            groupby=['account_id', 'currency_id'],
            lazy=False, )

        data_credit = defaultdict(float)
        for l in credit_groups:
            data_credit[l['account_id'][0]] += Curr.browse(
                l['currency_id'][0])._convert(
                l['amount'], user_currency, self.env.company,
                fields.Date.today())
        debit_groups = analytic_line_obj.read_group(
            domain=domain + [('amount', '<', 0.0)],
            fields=['account_id', 'currency_id', 'amount'],
            groupby=['account_id', 'currency_id'],
            lazy=False,
        )
        data_debit = defaultdict(float)
        for l in debit_groups:
            data_debit[l['account_id'][0]] += Curr.browse(
                l['currency_id'][0])._convert(
                l['amount'], user_currency, self.env.company,
                fields.Date.today())

        for account in self:
            account.debit = abs(data_debit.get(account.id, 0.0))
            account.credit = data_credit.get(account.id, 0.0)
            account.balance = account.credit - account.debit

