from odoo import models,fields

class Product(models.Model):
    _inherit = 'product.product'

    def action_view_tasc_stock_moves(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'TASC Move History',
            'res_model': 'tasc.move.history',
            'view_mode': 'tree',
            'view_id': self.env.ref('tasc_inventory_reports.tasc_move_history_view_tree').id,
            'domain': [('product_id', '=', self.id)],  # <== your dynamic filter
            'context': {},
            'target': 'current'
        }

    def action_view_tasc_stock_locations(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'TASC Locations',
            'res_model': 'tasc.location.report',
            'view_mode': 'tree',
            'view_id': self.env.ref('tasc_inventory_reports.tasc_location_report_view_tree').id,
            'domain': [('product_id', '=', self.id)],  # <== your dynamic filter
            'context': {},
            'target': 'current'
        }