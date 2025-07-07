from odoo import api, fields, models, tools, _


class TASCLocationReport(models.Model):
    _name = "tasc.location.report"
    _description = 'TASC Location'
    _auto = False

    product_id = fields.Many2one('product.product',string="Product")
    quantity = fields.Float('On hand Quantity')
    reserved_quantity = fields.Float('Reserved Quantity')
    location_id = fields.Many2one('stock.location', string="Location")
    project_site_id = fields.Many2one('account.analytic.account',string="Project Site")
    package_id = fields.Many2one('stock.quant.package', 'Package')
    lot_id = fields.Many2one('stock.lot', 'Lot/Serial Number')
    categ_id = fields.Many2one('product.category', 'Product Category')

    def init(self):
        tools.drop_view_if_exists(self._cr, self._table)
        view_name = self._table

        sql = f"""
            CREATE OR REPLACE VIEW {view_name} AS (
                WITH movement AS (
                    -- On-hand quantity: only done moves
                    SELECT
                        sml.product_id,
                        pt.categ_id AS categ_id,
                        sml.location_id,
                        sml.project_site_id,
                        sml.package_id,
                        sml.lot_id,
                        -sml.quantity AS qty,
                        0::numeric AS reserved
                    FROM stock_move_line sml
                    JOIN product_product pp ON pp.id = sml.product_id
                    JOIN product_template pt ON pt.id = pp.product_tmpl_id
                    JOIN stock_location sl ON sl.id = sml.location_id
                    WHERE sml.state = 'done' AND sl.usage NOT IN ('customer', 'supplier')
            
                    UNION ALL
            
                    SELECT
                        sml.product_id,
                        pt.categ_id AS categ_id,
                        sml.location_dest_id AS location_id,
                        sml.project_site_id,
                        sml.package_id,
                        sml.lot_id,
                        sml.quantity AS qty,
                        0::numeric AS reserved
                    FROM stock_move_line sml
                    JOIN product_product pp ON pp.id = sml.product_id
                    JOIN product_template pt ON pt.id = pp.product_tmpl_id
                    JOIN stock_location sl ON sl.id = sml.location_dest_id
                    WHERE sml.state = 'done' AND sl.usage NOT IN ('customer', 'supplier')
            
                    UNION ALL
            
                    -- Reserved quantity: not done, reserved quantity at source location
                    SELECT
                        sml.product_id,
                        pt.categ_id AS categ_id,
                        sml.location_id,
                        sml.project_site_id,
                        sml.package_id,
                        sml.lot_id,
                        0::numeric AS qty,
                        sml.quantity AS reserved
                    FROM stock_move_line sml
                    JOIN product_product pp ON pp.id = sml.product_id
                    JOIN product_template pt ON pt.id = pp.product_tmpl_id
                    JOIN stock_location sl ON sl.id = sml.location_id
                    WHERE sml.state != 'done' AND sml.quantity > 0 AND sl.usage NOT IN ('customer', 'supplier')
                )
            
                SELECT
                    ROW_NUMBER() OVER () AS id,
                    product_id,
                    categ_id,
                    location_id,
                    project_site_id,
                    package_id,
                    lot_id,
                    SUM(qty) AS quantity,
                    SUM(reserved) AS reserved_quantity
                FROM movement
                GROUP BY product_id, categ_id, location_id, project_site_id, package_id, lot_id
                ORDER BY product_id, categ_id, location_id, project_site_id, package_id, lot_id
            )
        """
        self._cr.execute(sql)

    def action_view_stock_moves(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'TASC Move History',
            'res_model': 'tasc.move.history',
            'view_mode': 'tree',
            'view_id': self.env.ref('tasc_inventory_reports.tasc_move_history_view_tree').id,
            'domain': [('product_id', '=', self.product_id.id)],  # <== your dynamic filter
            'context': {},
            'target': 'current'
        }
