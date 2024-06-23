from odoo import models, fields, api


class AssetBulkSaleDisposeWizard(models.Model):
    _name = 'asset.bulk.sale.dispose.wizard'
    _description = 'Asset Bulk Sale Dispose'

    company_id = fields.Many2one('res.company', string='Company', required=True)

    records = fields.Integer(string="Records")
    limit = fields.Integer(string="Limit", required=True)
    from_date = fields.Date(string="Acquisition From Date")
    to_date = fields.Date(string="Acquisition To Date")
    disposal_date = fields.Date(string="Disposal Date",required=True)
    state = fields.Selection(
        [('draft', 'Draft'), ('open', 'Running'), ('close', 'Close'),
         ('paused', 'On Hold'), ('to_approve', 'To Approve')], required=True)

    def action_bulk_sale_dispose(self):
        if self.from_date and self.to_date:
            items = self.env['account.asset'].search(
                [('state', '=', self.state),
                 ('company_id', '=', self.company_id.id),
                 ('acquisition_date', '>=', self.from_date),
                 ('acquisition_date', '<=', self.to_date)], limit=self.limit)
        elif self.from_date:
            items = self.env['account.asset'].search(
                [('state', '=', self.state),
                 ('company_id', '=', self.company_id.id),
                 ('acquisition_date', '>=', self.from_date),
                 ], limit=self.limit)
        elif self.to_date:
            items = self.env['account.asset'].search(
                [('state', '=', self.state),
                 ('company_id', '=', self.company_id.id),
                 ('acquisition_date', '<=', self.to_date)], limit=self.limit)
        else:
            items = self.env['account.asset'].search(
                [('state', '=', self.state),
                 ('company_id', '=', self.company_id.id)], limit=self.limit)
        abc = []
        for rec in items:
            if rec.leasee_contract_ids:
                asset_bulk = self.env['asset.sell.disposal.lines'].create({
                    'asset_id': rec.id,
                    'from_leasee_contract': True,
                    'action': 'dispose',
                    'contract_end_date': self.disposal_date,
                })
            else:
                asset_bulk = self.env['asset.sell.disposal.lines'].create({
                    'asset_id': rec.id,
                    'action': 'dispose',
                    'contract_end_date': self.disposal_date,
                })
            abc.append(asset_bulk.id)
        dd = self.env['asset.bulk.wizard'].create({
            'asset_sell_disposal_ids': [(6, 0, abc)]
        })
        return {
            'name': 'Asset Bulk sale',
            'view_mode': 'form',
            'res_model': 'asset.bulk.wizard',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'res_id': dd.id,
        }


    @api.onchange('from_date', 'to_date', 'company_id','state')
    def onchange_from_value(self):
        if self.from_date and self.to_date:
            self.records = self.env['account.asset'].search_count(
                [('state', '=', self.state),
                 ('company_id', '=', self.company_id.id),
                 ('acquisition_date', '>=', self.from_date),
                 ('acquisition_date', '<=', self.to_date)])
        elif self.from_date:
            self.records = self.env['account.asset'].search_count(
                [('state', '=', self.state),
                 ('company_id', '=', self.company_id.id),
                 ('acquisition_date', '>=', self.from_date),
                ])
        elif self.to_date:
            self.records = self.env['account.asset'].search_count(
                [('state', '=', self.state),
                 ('company_id', '=', self.company_id.id),
                 ('acquisition_date', '<=', self.to_date)])
        else:
            self.records = self.env['account.asset'].search_count(
                [('state', '=', self.state),
                 ('company_id', '=', self.company_id.id),
                 ])


