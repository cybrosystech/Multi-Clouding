# -*- coding: utf-8 -*-
from collections import defaultdict
from odoo import api, fields, models, _


class CrossOveredBudgetLines(models.Model):
    _inherit = 'crossovered.budget.lines'

    analytic_account_id = fields.Many2one('account.analytic.account',
                                          'Analytic Accounts',
                                          domain=[('analytic_account_type', '=',
                                                   'cost_center')],
                                          )

    project_site_id = fields.Many2one(comodel_name="account.analytic.account",
                                      string="Project/Site",
                                      domain=[('analytic_account_type', '=',
                                               'project_site')],
                                      required=False, )
    business_unit_id = fields.Many2one(comodel_name="account.analytic.account",
                                      string="Business unit",
                                       domain=[('plan_id.name', '=ilike', 'Business Unit')],
                                       required=False )
    type_id = fields.Many2one(comodel_name="account.analytic.account",
                              string="Type",
                              domain=[('analytic_account_type', '=', 'type')],
                              required=False, )
    location_id = fields.Many2one(comodel_name="account.analytic.account",
                                  string="Location",
                                  domain=[('analytic_account_type', '=',
                                           'location')], required=False, )
    remaining_amount = fields.Monetary(string="Remaining Amount",
                                       required=False,
                                       compute='get_remaining_amount', )
    actual_percentage = fields.Float(string="Actual Percentage", required=False,
                                     compute='get_actual_percentage')
    practical_demo = fields.Monetary()

    @api.depends('planned_amount', 'practical_amount')
    def get_remaining_amount(self):
        for rec in self:
            rec.remaining_amount = rec.planned_amount - rec.practical_amount

    @api.depends('planned_amount', 'practical_amount')
    def get_actual_percentage(self):
        for rec in self:
            if rec.planned_amount != 0:
                rec.actual_percentage = (abs(rec.practical_amount) * 100) / rec.planned_amount
            else:
                rec.actual_percentage = 0.0


    @api.depends("crossovered_budget_id", "general_budget_id",
                 "analytic_account_id")
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
            if record.business_unit_id:
                computed_name += ' - ' + record.business_unit_id.name
            record.name = computed_name

    def _compute_practical_amount(self):
        for line in self:
            item_amount =0
            amount = 0
            if not line.analytic_account_id and not line.project_site_id:
                lines = self.env['crossovered.budget.lines'].search(
                    [('crossovered_budget_id', '=',
                      line.crossovered_budget_id.id),
                     ('general_budget_id', '=', line.general_budget_id.id),
                     ('analytic_account_id', '!=', False),
                     ('project_site_id', '!=', False), ('id', '!=', line.id),
                     ('date_from', '=', line.date_from),
                     ('date_to', '=', line.date_to)
                     ])
                amount = sum(lines.mapped('practical_amount'))
                journal_items = self.env['account.move.line'].search([(
                    'account_id',
                    'in',
                    line.general_budget_id.account_ids.ids),
                    (
                        'parent_state',
                        '=',
                        'posted'), ('date', '>=', line.date_from),
                    ('date', '<=', line.date_to)])
                item_amount = sum(journal_items.mapped('balance'))
                line.practical_amount = item_amount - amount
                line.practical_demo = item_amount - amount

            elif line.analytic_account_id and line.project_site_id:
                journal_items = self.env['account.move.line'].search([(
                    'account_id',
                    'in',
                    line.general_budget_id.account_ids.ids),
                    ('analytic_account_id', '=', line.analytic_account_id.id),
                    ('project_site_id', '=', line.project_site_id.id),
                    ('parent_state', '=', 'posted'),
                    ('date', '>=', line.date_from),
                    ('date', '<=', line.date_to)])
                item_amount = sum(journal_items.mapped('balance'))
                line.practical_amount = item_amount
                line.practical_demo = item_amount
            else:
                line.practical_amount = 0
                line.practical_demo = 0

    def action_open_budget_entries(self):
        action = self.env['ir.actions.act_window']._for_xml_id(
            'analytic.account_analytic_line_action_entries')
        if self.analytic_account_id:
            # if there is an analytic account, then the analytic items are loaded
            action['domain'] = [
                ('account_id', '=', self.analytic_account_id.id),
                ('date', '>=', self.date_from),
                ('date', '<=', self.date_to)
            ]
            if self.project_site_id:
                action['domain'] += [
                    ('project_site_id', '=', self.project_site_id.id)
                ]
            if self.type_id:
                action['domain'] += [('type_id', '=', self.type_id.id)
                                     ]
            if self.location_id:
                action['domain'] += [('location_id', '=', self.location_id.id)
                                     ]
            if self.general_budget_id:
                action['domain'] += [('general_account_id', 'in',
                                      self.general_budget_id.account_ids.ids)]
        else:
            # otherwise the journal entries booked on the accounts of the budgetary postition are opened
            action = self.env['ir.actions.act_window']._for_xml_id(
                'account.action_account_moves_all_a')
            action['domain'] = [('account_id', 'in',
                                 self.general_budget_id.account_ids.ids),
                                ('date', '>=', self.date_from),
                                ('date', '<=', self.date_to)
                                ]
        return action
