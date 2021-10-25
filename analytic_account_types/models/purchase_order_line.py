# -*- coding: utf-8 -*-

from odoo import models, fields, api

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    # cost_center_id = fields.Many2one(comodel_name="account.analytic.account", string="Cost Center", required=False, )
    project_site_id = fields.Many2one(comodel_name="account.analytic.account", string="Project/Site",domain=[('analytic_account_type','=','project_site')], required=False, )
    type_id = fields.Many2one(comodel_name="account.analytic.account", string="Type",domain=[('analytic_account_type','=','type')], required=False, )
    location_id = fields.Many2one(comodel_name="account.analytic.account", string="Location",domain=[('analytic_account_type','=','location')], required=False, )

    @api.onchange('project_site_id')
    def get_location_and_types(self):
        for rec in self:
            rec.type_id = rec.project_site_id.analytic_type_filter_id.id
            rec.location_id = rec.project_site_id.analytic_location_id.id

    def open_account_analytic_types(self):
        return {
            'name': 'Analytic Account Types',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'wizard.analytic.account.types',
            'context': {'default_po_line': self.id},
            'target': 'new',
        }

    def _prepare_account_move_line(self, move=False):
        res = super(PurchaseOrderLine, self)._prepare_account_move_line()
        res.update({'project_site_id':self.project_site_id.id,'type_id':self.type_id.id,'location_id':self.location_id.id})
        return res

