from odoo import models, fields


class AssetsSubModel(models.Model):
    _name = 'assets.sub.model'
    _description = ''

    name = fields.Char()
    asset_model_id = fields.Many2many('account.asset', domain=[('state', '=', 'model')])