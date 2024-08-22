from odoo import fields, models, api, _


class DashboardGirdConfig(models.Model):
    _name = 'dashboard.gird.config'
    _description = 'Dashboard grid configuration'

    name = fields.Char('max_length')
    grid_config_bits = fields.Char('Grid Configurations')
    dashboard_bits_id = fields.Many2one('dashboard.bits', 'Dashboard id')
    dashboard_item_bits_ids = fields.One2many('dashboard.item.bits', 'dashboard_grid_config_id', 'Dashboard item')

