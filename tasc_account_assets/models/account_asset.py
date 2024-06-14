from datetime import timedelta
from odoo import api, models, fields
from odoo.tools.sql import column_exists, create_column


class AccountAsset(models.Model):
    _inherit = 'account.asset'

    def _auto_init(self):
        if not column_exists(self.env.cr, "account_asset", "value_residual"):
            create_column(self.env.cr, "account_asset", "value_residual",
                          "numeric")
            self.env.cr.execute("""
                UPDATE account_asset 
                SET value_residual = 0.0
                """)
        return super()._auto_init()

    value_residual = fields.Monetary(string='Depreciable Value',
                                     compute='_compute_value_residual',
                                     store=True)
    sequence_number = fields.Char(string="Asset Sequence Number")

    @api.model
    def create(self, vals):
        res = super(AccountAsset, self).create(vals)
        if res.model_id:
            if res.model_id.name.lower() != 'ground lease':
                sequence_number = self.env['ir.sequence'].next_by_code(
                    'account.asset')
                res.sequence_number = sequence_number
        else:
            sequence_number = self.env['ir.sequence'].next_by_code(
                'account.asset')
            res.sequence_number = sequence_number
        return res

    @api.model
    def set_asset_sequence_number(self, limit):
        asset_ids = self.env['account.asset'].search(
            [('sequence_number', '=', False),
             ('company_id', '=', self.env.company.id)], order='id ASC',
            limit=limit).filtered(
            lambda x: x.model_id.name.lower() != 'ground lease'  if x.model_id else not x.model_id)
        for asset in asset_ids:
            sequence_number = self.env['ir.sequence'].next_by_code(
                'account.asset')
            asset.sequence_number = sequence_number
        asset_ids = self.env['account.asset'].search(
            [('sequence_number', '=', False),
             ('company_id', '=', self.env.company.id)]).filtered(
            lambda x: x.model_id.name.lower() != 'ground lease' if x.model_id else  not x.model_id)
        if asset_ids:
            date = fields.Datetime.now()
            schedule = self.env.ref(
                'tasc_account_assets.action_set_asset_sequence_number_cron_update')
            schedule.update({
                'nextcall': date + timedelta(seconds=15)
            })

    @api.model
    def set_asset_sequence_number_cron_update(self):
        date = fields.Datetime.now()
        schedule = self.env.ref(
            'tasc_account_assets.action_set_asset_sequence_number')
        schedule.update({
            'nextcall': date + timedelta(seconds=15)
        })

    def set_depreciable_value(self, limit):
        asset_ids = self.env['account.asset'].search(
            ['|', ('value_residual', '=', 0), ('value_residual', '=', False),
             ('company_id', '=', self.env.company.id)], limit=limit)
        for asset in asset_ids:
            posted = asset.depreciation_move_ids.filtered(
                lambda m: m.state == 'posted' and not m.reversal_move_id
            )
            if asset.currency_id != asset.env.company.currency_id:
                posted_depreciation_move_ids = asset.depreciation_move_ids.filtered(
                    lambda x: x.state == 'posted')
                asset.value_residual = (
                        asset.original_value
                        - asset.salvage_value
                        - asset.already_depreciated_amount_import
                        - sum(
                    posted_depreciation_move_ids.mapped('amount_total'))
                )
            else:
                asset.value_residual = (
                        asset.original_value
                        - asset.salvage_value
                        - asset.already_depreciated_amount_import
                        - sum(move._get_depreciation() for move in posted)
                )
        asset_ids = self.env['account.asset'].search(
            ['|', ('value_residual', '=', 0), ('value_residual', '=', 0),
             ('company_id', '=', self.env.company.id)])
        if asset_ids:
            date = fields.Datetime.now()
            schedule = self.env.ref(
                'tasc_account_assets.action_set_depreciable_value_cron_update')
            schedule.update({
                'nextcall': date + timedelta(seconds=15)
            })

    def set_depreciable_value_cron_update(self):
        date = fields.Datetime.now()
        schedule = self.env.ref(
            'tasc_account_assets.action_set_depreciable_value')
        schedule.update({
            'nextcall': date + timedelta(seconds=15)
        })
