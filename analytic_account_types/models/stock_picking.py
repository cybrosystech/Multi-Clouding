from odoo import api,models,fields

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.onchange('location_id')
    def onchange_location_id(self):
        if self.move_ids:
            if self.picking_type_id.code == 'internal':
                self.move_ids.write({'source_project_site_id': self.location_id.project_site_id.id})

    @api.onchange('location_dest_id')
    def onchange_location_dest_id(self):
        if self.move_ids:
            if self.picking_type_id.code == 'internal':
                self.move_ids.write({'project_site_id': self.location_dest_id.project_site_id.id})
