from odoo import models, fields


class AssetsSubModel(models.Model):
    _name = 'assets.sub.model'
    _description = ''

    name = fields.Char()
    asset_model_id = fields.Many2one('account.asset', domain=[('asset_type', '=', 'purchase'), ('state', '=', 'model')])