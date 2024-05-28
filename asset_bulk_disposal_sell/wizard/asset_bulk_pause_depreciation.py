from odoo import fields, models


class AssetBulkWizard(models.TransientModel):
    _name = 'asset.bulk.pause.wizard'

    asset_ids = fields.Many2many('account.asset')
    date = fields.Date(string='Pause date', required=True, default=fields.Date.today())

    def do_action(self):
        for record in self:
            for asset in record.asset_ids:
                asset.pause(pause_date=record.date, message=asset.name)
