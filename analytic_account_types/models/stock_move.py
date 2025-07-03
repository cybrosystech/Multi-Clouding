from odoo import api,models,fields

class StockMove(models.Model):
    _inherit = 'stock.move'

    site_status = fields.Selection(
        [('on_air', 'ON AIR'), ('off_air', 'OFF AIR'), ],
        string='Site Status')
    t_budget = fields.Selection(
        [('capex', 'CAPEX'), ('opex', 'OPEX'), ],
        string='T.Budget')
    t_budget_name = fields.Char(string="T.Budget Name")
    project_site_id = fields.Many2one(comodel_name="account.analytic.account",
                                      string="Destination Project/Site",
                                      domain=[('analytic_account_type', '=',
                                               'project_site')],
                                      readonly=False,
                                      )
    source_project_site_id = fields.Many2one(comodel_name="account.analytic.account",
                                      string=" Source Project/Site",
                                      domain=[('analytic_account_type', '=',
                                               'project_site')],
                                             readonly=False,
                                      )

    @api.onchange('location_id')
    def onchange_location_id(self):
        if self.picking_type_id.code == 'internal':
            self.source_project_site_id = self.location_id.project_site_id.id

    @api.onchange('location_dest_id')
    def onchange_location_dest_id(self):
        if self.picking_type_id.code == 'internal':
            self.project_site_id = self.location_dest_id.project_site_id.id

    def _prepare_move_line_vals(self, quantity=None, reserved_quant=None):
        vals = super()._prepare_move_line_vals(quantity, reserved_quant)
        vals['project_site_id'] = self.project_site_id.id
        vals['source_project_site_id'] = self.source_project_site_id.id
        return vals

    def write(self,vals):
        res = super().write(vals)
        if 'source_project_site_id' in vals or 'project_site_id' in vals:
            self.set_project_sites()
        return res

    def set_project_sites(self):
        for move in self:
            for line in move.move_line_ids:
                if move.project_site_id:
                    line.project_site_id = move.project_site_id.id
                if move.source_project_site_id:
                    line.source_project_site_id = move.source_project_site_id.id


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    project_site_id = fields.Many2one(comodel_name="account.analytic.account",
                                      string="Destination Project/Site",
                                      domain=[('analytic_account_type', '=',
                                               'project_site')],
                                      )
    source_project_site_id = fields.Many2one(comodel_name="account.analytic.account",
                                      string=" Source Project/Site",
                                      domain=[('analytic_account_type', '=',
                                               'project_site')],
                                      )

