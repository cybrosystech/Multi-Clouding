# -*- coding: utf-8 -*-

from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class CrossOveredBudgetLines(models.Model):
    _inherit = 'crossovered.budget.lines'

    project_site_id = fields.Many2one(comodel_name="account.analytic.account", string="Project/Site",
                                      domain=[('analytic_account_type', '=', 'project_site')], required=False, )
    type_id = fields.Many2one(comodel_name="account.analytic.account", string="Type",
                              domain=[('analytic_account_type', '=', 'type')], required=False, )
    location_id = fields.Many2one(comodel_name="account.analytic.account", string="Location",
                                  domain=[('analytic_account_type', '=', 'location')], required=False, )
    remaining_amount = fields.Monetary(string="Remaining Amount",  required=False,compute='get_remaining_amount',)
    actual_percentage = fields.Float(string="Actual Percentage",  required=False,compute='get_actual_percentage' )

    @api.depends('planned_amount','practical_amount')
    def get_remaining_amount(self):
        for rec in self:
            rec.remaining_amount = rec.planned_amount + rec.practical_amount

    @api.depends('planned_amount', 'practical_amount')
    def get_actual_percentage(self):
        for rec in self:
            if rec.planned_amount != 0:
                rec.actual_percentage = (
                                                abs(rec.practical_amount) * 100) / rec.planned_amount
            else:
                rec.actual_percentage = 0.0

    @api.depends("crossovered_budget_id", "general_budget_id", "analytic_account_id")
    def _compute_line_name(self):
        # just in case someone opens the budget line in form view
        for record in self:
            computed_name = record.crossovered_budget_id.name
            if record.general_budget_id:
                computed_name += ' - ' + record.general_budget_id.name
            if record.analytic_account_id:
                computed_name += ' - ' + record.analytic_account_id.name
            if record.project_site_id:
                computed_name += ' - ' + record.project_site_id.name
            if record.type_id:
                computed_name += ' - ' + record.type_id.name
            if record.location_id:
                computed_name += ' - ' + record.location_id.name
            record.name = computed_name

    def _compute_practical_amount(self):
        for line in self:
            acc_ids = line.general_budget_id.account_ids.ids
            date_to = line.date_to
            date_from = line.date_from
            if line.analytic_account_id.id or line.project_site_id.id or line.type_id.id or line.location_id.id:
                domain = []
                analytic_line_obj = self.env['account.analytic.line']
                if line.analytic_account_id.id:
                    domain += [('account_id', '=', line.analytic_account_id.id),
                              ('date', '>=', date_from),
                              ('date', '<=', date_to),
                              ]
                if line.project_site_id.id:
                    domain += [('project_site_id', '=', line.project_site_id.id)
                    ]
                if line.type_id.id:
                    domain += [('type_id', '=', line.type_id.id)

                              ]
                if line.location_id.id:
                    domain += [('location_id', '=', line.location_id.id)
                              ]
                if acc_ids:
                    domain += [('general_account_id', 'in', acc_ids)]

                where_query = analytic_line_obj._where_calc(domain)
                analytic_line_obj._apply_ir_rules(where_query, 'read')
                from_clause, where_clause, where_clause_params = where_query.get_sql()
                select = "SELECT SUM(amount) from " + from_clause + " where " + where_clause

            else:
                aml_obj = self.env['account.move.line']
                domain = [('account_id', 'in',
                           line.general_budget_id.account_ids.ids),
                          ('date', '>=', date_from),
                          ('date', '<=', date_to),
                          ('move_id.state', '=', 'posted')
                          ]
                where_query = aml_obj._where_calc(domain)
                aml_obj._apply_ir_rules(where_query, 'read')
                from_clause, where_clause, where_clause_params = where_query.get_sql()
                select = "SELECT sum(credit)-sum(debit) from " + from_clause + " where " + where_clause

            self.env.cr.execute(select, where_clause_params)
            line.practical_amount = self.env.cr.fetchone()[0] or 0.0

    def action_open_budget_entries(self):
        action = self.env['ir.actions.act_window']._for_xml_id('analytic.account_analytic_line_action_entries')
        if self.analytic_account_id:
            # if there is an analytic account, then the analytic items are loaded
            action['domain'] = [('account_id', '=', self.analytic_account_id.id),
                                ('date', '>=', self.date_from),
                                ('date', '<=', self.date_to)
                                ]
            if self.project_site_id:
                action['domain'] += [('project_site_id', '=', self.project_site_id.id)
                                    ]
            if self.type_id:
                action['domain'] += [('type_id', '=', self.type_id.id)
                                    ]
            if self.location_id:
                action['domain'] += [('location_id', '=', self.location_id.id)
                                    ]
            if self.general_budget_id:
                action['domain'] += [('general_account_id', 'in', self.general_budget_id.account_ids.ids)]
        else:
            # otherwise the journal entries booked on the accounts of the budgetary postition are opened
            action = self.env['ir.actions.act_window']._for_xml_id('account.action_account_moves_all_a')
            action['domain'] = [('account_id', 'in',
                                 self.general_budget_id.account_ids.ids),
                                ('date', '>=', self.date_from),
                                ('date', '<=', self.date_to)
                                ]
        return action






