from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class AssetBulkRevaluate(models.TransientModel):
    _name = 'asset.bulk.revaluate'

    date = fields.Date(default=lambda self: fields.Date.today(), string='Date')
    method_number = fields.Integer(string='Duration')
    method_period = fields.Selection([('1', 'Months'), ('12', 'Years')],
                                     string='Number of Months in a Period',
                                     help="The amount of time between two depreciations",
                                     default='1')
    company_id = fields.Many2one('res.company',default=lambda self: self.env.company)
    asset_ids = fields.Many2many('account.asset')
    account_asset_counterpart_id = fields.Many2one(
        'account.account',
        check_company=True,
        domain="[('deprecated', '=', False)]",
        string="Asset Counterpart Account",
    )
    asset_revaluate_ids = fields.One2many('asset.modify',
                                              'asset_bulk_revaluate_id')

    def action_generate(self):
        abc = []
        for rec in self.asset_ids:
            asset_bulk = self.env['asset.modify'].create({
                'asset_id': rec.id,
                'date': self.date if self.date else fields.Date.today(),
                'method_number':self.method_number,
                'method_period': self.method_period,
                'account_asset_counterpart_id': self.account_asset_counterpart_id.id,
                'modify_action': 'modify',
            })
            if asset_bulk:  # Ensure record is created successfully
                abc.append(asset_bulk.id)

        # Create the asset.bulk.revaluate record
        self.asset_revaluate_ids= [(6, 0, abc)]

        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }

    def split_list(self, lst, limit):
        return [lst[i:i + limit] for i in range(0, len(lst), limit)]

    def action_apply(self):
        my_list = self.asset_revaluate_ids.ids
        sublists = self.split_list(my_list, 20)
        self.create_jobs(sublists)

    def create_jobs(self, sublist):
        for i in sublist:
            assets = self.env['asset.modify'].search(
                [('id', 'in', i)]).mapped('asset_id')
            self.with_delay(priority=5)._process_job(i, assets)

    def _process_job(self, iteration, assets):
        # Process the job
        # Perform your task here
        for asset in iteration:
            record = self.env['asset.modify'].browse(asset)
            record.with_context(bypass_audit_log=True, force_delete=True).modify()


class AssetModify(models.TransientModel):
    _inherit = 'asset.modify'

    asset_bulk_revaluate_id = fields.Many2one('asset.bulk.revaluate', string='Bulk Revaluate')
