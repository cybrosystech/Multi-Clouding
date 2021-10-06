# -*- coding: utf-8 -*-

from odoo import models, fields, api

class AnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    analytic_account_type = fields.Selection(string="Analytic Type", selection=[('cost_center', 'Cost Center'), ('project_site', 'Project/Site'),('type', 'Type'),('location', 'Location'), ], required=False, )

class WizardAnalyticAccountTypes(models.Model):
    _name = 'wizard.analytic.account.types'

    cost_center_id = fields.Many2one(comodel_name="account.analytic.account", string="Cost Center",domain=[('analytic_account_type','=','cost_center')], required=False, )
    project_site_id = fields.Many2one(comodel_name="account.analytic.account", string="Project/Site",domain=[('analytic_account_type','=','project_site')], required=False, )
    type_id = fields.Many2one(comodel_name="account.analytic.account", string="Type",domain=[('analytic_account_type','=','type')], required=False, )
    location_id = fields.Many2one(comodel_name="account.analytic.account", string="Location",domain=[('analytic_account_type','=','location')],  required=False, )
    budget_id = fields.Many2one(comodel_name="crossovered.budget", string="Budget", required=False, )

    so_line = fields.Many2one(comodel_name="sale.order.line", string="So Line", required=False, )
    po_line = fields.Many2one(comodel_name="purchase.order.line", string="po Line", required=False, )
    move_line = fields.Many2one(comodel_name="account.move.line", string="move Line", required=False, )

    @api.onchange('cost_center_id','project_site_id','type_id','location_id','budget_id','po_line','move_line')
    def _get_budgets(self):
        if self.po_line:
            budgets = []
            budget_lines = self.env['crossovered.budget.lines'].search([]).filtered(lambda x: self.po_line.order_id.date_order.date() >= x.date_from and self.po_line.order_id.date_order.date() <= x.date_to and x.analytic_account_id == self.cost_center_id and x.project_site_id == self.project_site_id and x.type_id == self.type_id and x.location_id == self.location_id)
            if budget_lines:
                for bud_line in budget_lines:
                    budgets.append(bud_line.crossovered_budget_id.id)
            return {'domain':{'budget_id':[('id','in',budgets)]}}
        elif self.move_line:
            budgets = []
            budget_lines = self.env['crossovered.budget.lines'].search([]).filtered(lambda x: self.move_line.move_id.invoice_date >= x.date_from and self.move_line.move_id.invoice_date <= x.date_to and x.analytic_account_id == self.cost_center_id and x.project_site_id == self.project_site_id and x.type_id == self.type_id and x.location_id == self.location_id)
            if budget_lines:
                for bud_line in budget_lines:
                    budgets.append(bud_line.crossovered_budget_id.id)
            return {'domain': {'budget_id': [('id', 'in', budgets)]}}


    @api.onchange('project_site_id')
    def get_location_and_types(self):
        for rec in self:
            rec.type_id = rec.project_site_id.analytic_type_filter_id.id
            rec.location_id = rec.project_site_id.analytic_location_id.id

    def set_analytics_lines(self):
        if self.so_line:
            self.so_line.cost_center_id = self.cost_center_id.id
            self.so_line.project_site_id = self.project_site_id.id
            self.so_line.type_id = self.type_id.id
            self.so_line.location_id = self.location_id.id
        if self.po_line:
            self.po_line.account_analytic_id = self.cost_center_id.id
            self.po_line.project_site_id = self.project_site_id.id
            self.po_line.type_id = self.type_id.id
            self.po_line.location_id = self.location_id.id
            self.po_line.budget_id = self.budget_id.id
            self.po_line.order_id.get_budgets_in_out_budget_tab()
        if self.move_line:
            self.move_line.analytic_account_id = self.cost_center_id.id
            self.move_line.project_site_id = self.project_site_id.id
            self.move_line.type_id = self.type_id.id
            self.move_line.location_id = self.location_id.id
            self.move_line.budget_id = self.budget_id.id
            self.move_line.move_id.get_budgets_in_out_budget_tab()




