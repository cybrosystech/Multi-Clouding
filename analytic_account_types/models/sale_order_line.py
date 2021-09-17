# -*- coding: utf-8 -*-

from odoo import models, fields, api

class SalesOrderLine(models.Model):
    _inherit = 'sale.order.line'

    cost_center_id = fields.Many2one(comodel_name="account.analytic.account", string="Cost Center",domain=[('analytic_account_type','=','cost_center')], required=False, )
    project_site_id = fields.Many2one(comodel_name="account.analytic.account", string="Project/Site",domain=[('analytic_account_type','=','project_site')], required=False, )
    type_id = fields.Many2one(comodel_name="account.analytic.account", string="Type",domain=[('analytic_account_type','=','type')], required=False, )
    location_id = fields.Many2one(comodel_name="account.analytic.account", string="Location",domain=[('analytic_account_type','=','location')], required=False, )

    def open_account_analytic_types(self):
        return {
            'name': 'Analytic Account Types',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'wizard.analytic.account.types',
            'context': {'default_so_line': self.id},
            'target': 'new',
        }

    def _prepare_invoice_line(self, **optional_values):
        res = super(SalesOrderLine, self)._prepare_invoice_line(**optional_values)
        res.update({'analytic_account_id':self.cost_center_id.id if self.cost_center_id else self.order_id.analytic_account_id.id
                    , 'project_site_id':self.project_site_id.id,'type_id':self.type_id.id,'location_id':self.location_id.id})
        return res

