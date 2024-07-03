# -*- coding: utf-8 -*-
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
            rec.remaining_amount = rec.planned_amount + rec.practical_amount

    @api.depends('planned_amount', 'practical_amount')
    def get_actual_percentage(self):
        for rec in self:
            if rec.planned_amount != 0:
                rec.actual_percentage = (
                                                abs(rec.practical_amount) * 100) / rec.planned_amount
            else:
                rec.actual_percentage = 0.0

    @api.depends("crossovered_budget_id", "general_budget_id",
                 "analytic_account_id")
    def _compute_line_name(self):
        print("18")
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
        print("555555555")
        analytic_line_ids = []
        for line in self:
            if 'default_move_type' not in list(self._context.keys()):
                analytic_accounts = self.filtered(lambda
                                                      x: x.general_budget_id.id == line.general_budget_id.id).mapped(
                    'analytic_account_id').ids
                acc_ids = line.general_budget_id.account_ids.ids
                date_to = line.date_to
                date_from = line.date_from
                if acc_ids and line.analytic_account_id and line.project_site_id:
                    analytic_line_obj = self.env['account.analytic.line']
                    domain = [('id', 'not in', analytic_line_ids),
                              ('account_id', '=', line.analytic_account_id.id),
                              ('date', '>=', date_from),
                              ('date', '<=', date_to),
                              ('general_account_id', 'in', acc_ids)]
                    where_query = analytic_line_obj._where_calc(domain)
                    analytic_line_obj._apply_ir_rules(where_query, 'read')
                    from_clause, where_clause, where_clause_params = where_query.get_sql()
                    select = "SELECT id , amount from " + from_clause + " where " + where_clause
                    self.env.cr.execute(select, where_clause_params)
                    fetched_dict = self.env.cr.dictfetchall()
                    if fetched_dict:
                        total = sum(
                            list(map(lambda x: x['amount'], fetched_dict)))
                        analytic_line_ids += list(
                            map(lambda x: x['id'], fetched_dict))
                        line.practical_amount = total if total else 0
                    else:
                        line.practical_amount = 0
                elif acc_ids and line.analytic_account_id:
                    analytic_line_obj = self.env['account.analytic.line']
                    domain = [('id', 'not in', analytic_line_ids),
                              ('account_id', '=', line.analytic_account_id.id),
                              ('date', '>=', date_from),
                              ('date', '<=', date_to),
                              ('general_account_id', 'in', acc_ids)]
                    where_query = analytic_line_obj._where_calc(domain)
                    analytic_line_obj._apply_ir_rules(where_query, 'read')
                    from_clause, where_clause, where_clause_params = where_query.get_sql()
                    select = "SELECT id ,amount from " + from_clause + " where " + where_clause
                    self.env.cr.execute(select, where_clause_params)
                    fetched_dict = self.env.cr.dictfetchall()
                    if fetched_dict:
                        total = sum(
                            list(map(lambda x: x['amount'], fetched_dict)))
                        analytic_line_ids += list(
                            map(lambda x: x['id'], fetched_dict))
                        line.practical_amount = total if total else 0
                    else:
                        line.practical_amount = 0
                elif acc_ids and line.project_site_id:
                    analytic_line_obj = self.env['account.analytic.line']
                    domain = [('id', 'not in', analytic_line_ids),
                              ('date', '>=', date_from),
                              ('date', '<=', date_to),
                              ('general_account_id', 'in', acc_ids),
                              ]
                    where_query = analytic_line_obj._where_calc(domain)
                    analytic_line_obj._apply_ir_rules(where_query, 'read')
                    from_clause, where_clause, where_clause_params = where_query.get_sql()
                    select = "SELECT id, amount from " + from_clause + " where " + where_clause
                    self.env.cr.execute(select, where_clause_params)
                    fetched_dict = self.env.cr.dictfetchall()
                    if fetched_dict:
                        total = sum(
                            list(map(lambda x: x['amount'], fetched_dict)))
                        analytic_line_ids += list(
                            map(lambda x: x['id'], fetched_dict))
                        line.practical_amount = total if total else 0
                    else:
                        line.practical_amount = 0
                else:
                    analytic_line_obj = self.env['account.analytic.line']
                    domain = [('id', 'not in', analytic_line_ids),
                              ('account_id', 'not in', analytic_accounts),
                              ('date', '>=', date_from),
                              ('date', '<=', date_to),
                              ('general_account_id', 'in', acc_ids)]
                    where_query = analytic_line_obj._where_calc(domain)
                    analytic_line_obj._apply_ir_rules(where_query, 'read')
                    from_clause, where_clause, where_clause_params = where_query.get_sql()
                    select = "SELECT id , amount from " + from_clause + " where " + where_clause
                    self.env.cr.execute(select, where_clause_params)
                    fetched_dict = self.env.cr.dictfetchall()
                    if fetched_dict:
                        total = sum(
                            list(map(lambda x: x['amount'], fetched_dict)))
                        analytic_line_ids += list(
                            map(lambda x: x['id'], fetched_dict))
                        line.practical_amount = total if total else 0
                    else:
                        line.practical_amount = 0
                line.practical_demo = line.practical_amount
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
