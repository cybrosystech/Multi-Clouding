from odoo import api, fields, models, tools, _


class TASCMovesHistory(models.Model):
    _name = "tasc.move.history"
    _description = 'TASC Moves History'
    _auto = False

    product_id = fields.Many2one('product.product',string="Product")
    location_dest_id = fields.Many2one('stock.location',string="Location")
    project_site_id = fields.Many2one('account.analytic.account',string="Project Site")
    quantity = fields.Float('Quantity')
    package_id = fields.Many2one('stock.quant.package', 'Package')
    lot_id = fields.Many2one('stock.lot', 'Lot/Serial Number')

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        self.init()
        return super().fields_view_get(view_id, view_type, toolbar, submenu)

    def init(self):
        tools.drop_view_if_exists(self._cr, self._table)
        view_name = self._table
        sql = f"""
                CREATE OR REPLACE VIEW {view_name} AS (
                SELECT 
                ROW_NUMBER() OVER () AS id,
                sml.product_id,
                sml.location_dest_id,
                sml.project_site_id,
                sml.package_id,
                sml.lot_id,
                SUM(sml.quantity) AS quantity
                FROM stock_move_line sml
                WHERE sml.state='done' AND sml.project_site_id IS NOT NULL
                GROUP BY sml.product_id, sml.location_dest_id, sml.project_site_id,sml.package_id,sml.lot_id

                UNION ALL
                
                SELECT 
                    ROW_NUMBER() OVER () + 100000 AS id,  -- offset to avoid ID clash
                    sml.product_id,
                    sml.location_dest_id,
                    NULL AS project_site_id,
                    sml.package_id,
                    sml.lot_id,
                    SUM(sml.quantity)  AS quantity
                FROM stock_move_line sml
                WHERE sml.state='done'  AND sml.project_site_id IS NULL
                GROUP BY sml.product_id, sml.location_dest_id,sml.project_site_id,sml.package_id,sml.lot_id)
           """

        self._cr.execute(sql)