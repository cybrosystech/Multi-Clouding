from odoo import models,fields

class StockMove(models.Model):
    _inherit = 'stock.move'

    site_status = fields.Selection(
        [('on_air', 'ON AIR'), ('off_air', 'OFF AIR'), ],
        string='Site Status')
    t_budget = fields.Selection(
        [('capex', 'CAPEX'), ('opex', 'OPEX'), ],
        string='T.Budget')
    t_budget_name = fields.Char(string="T.Budget Name")

