from odoo import models, fields, api


class AssetBulkSaleDisposeWizard(models.Model):
    _name = 'asset.bulk.sale.dispose.wizard'
    _description = 'Asset Bulk Sale Dispose'

    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 domain=lambda self: [
                                     ('id', 'in', self.env.companies.ids)])

    records = fields.Integer(string="Records")
    limit = fields.Integer(string="Limit", required=True)
    from_date = fields.Date(string="Acquisition From Date")
    to_date = fields.Date(string="Acquisition To Date")
    disposal_date = fields.Date(string="Disposal Date", required=True)
    state = fields.Selection(
        [('draft', 'Draft'), ('open', 'Running'), ('close', 'Close'),
         ('paused', 'On Hold'), ('to_approve', 'To Approve')], required=True)

    loss_account_id = fields.Many2one('account.account',
                                      domain="[('deprecated', '=', False), ('company_id', '=', company_id)]",
                                      help="Account used to write the journal item in case of loss",
                                      readonly=False)
    gain_account_id = fields.Many2one('account.account',
                                      domain="[('deprecated', '=', False), ('company_id', '=', company_id)]",
                                      help="Account used to write the journal item in case of gain",
                                      readonly=False)

    def action_bulk_sale_dispose(self):
        if self.limit != 0:
            if self.company_id and self.state and self.from_date and self.to_date:
                items = self.env['account.asset'].search(
                    [('state', '=', self.state),
                     ('company_id', '=', self.company_id.id),
                     ('acquisition_date', '>=', self.from_date),
                     ('acquisition_date', '<=', self.to_date),
                     ('state', '!=', 'model'), ('state', '!=', 'model'),
                     ('leasee_contract_ids', '=', False),
                     ('parent_id', '=', False)], limit=self.limit)
            elif self.company_id and self.state and self.from_date:
                items = self.env['account.asset'].search(
                    [('state', '=', self.state),
                     ('company_id', '=', self.company_id.id),
                     ('acquisition_date', '>=', self.from_date),
                     ('leasee_contract_ids', '=', False),
                     ('state', '!=', 'model'), ('parent_id', '=', False)],
                    limit=self.limit)
            elif self.company_id and self.state and self.to_date:
                items = self.env['account.asset'].search(
                    [('state', '=', self.state),
                     ('company_id', '=', self.company_id.id),
                     ('acquisition_date', '<=', self.to_date),
                     ('leasee_contract_ids', '=', False),
                     ('state', '!=', 'model'), ('parent_id', '=', False)],
                    limit=self.limit)
            elif self.company_id and self.state:
                items = self.env['account.asset'].search(
                    [('state', '=', self.state),
                     ('company_id', '=', self.company_id.id),
                     ('leasee_contract_ids', '=', False),
                     ('state', '!=', 'model'), ('parent_id', '=', False)],
                    limit=self.limit)
            else:
                items = self.env['account.asset'].search(
                    [('company_id', '=', self.company_id.id),
                     ('leasee_contract_ids', '=', False),
                     ('state', '!=', 'model'), ('parent_id', '=', False)],
                    limit=self.limit)
        else:
            if self.company_id and self.state and self.from_date and self.to_date:
                items = self.env['account.asset'].search(
                    [('state', '=', self.state),
                     ('company_id', '=', self.company_id.id),
                     ('acquisition_date', '>=', self.from_date),
                     ('acquisition_date', '<=', self.to_date),
                     ('leasee_contract_ids', '=', False),
                     ('state', '!=', 'model'), ('state', '!=', 'model'),
                     ('parent_id', '=', False)])
            elif self.company_id and self.state and self.from_date:
                items = self.env['account.asset'].search(
                    [('state', '=', self.state),
                     ('company_id', '=', self.company_id.id),
                     ('leasee_contract_ids', '=', False),
                     ('acquisition_date', '>=', self.from_date),
                     ('state', '!=', 'model'), ('parent_id', '=', False)])
            elif self.company_id and self.state and self.to_date:
                items = self.env['account.asset'].search(
                    [('state', '=', self.state),
                     ('company_id', '=', self.company_id.id),
                     ('acquisition_date', '<=', self.to_date),
                     ('leasee_contract_ids', '=', False),
                     ('state', '!=', 'model'), ('parent_id', '=', False)])
            elif self.company_id and self.state:
                items = self.env['account.asset'].search(
                    [('state', '=', self.state),
                     ('leasee_contract_ids', '=', False),
                     ('company_id', '=', self.company_id.id),
                     ('state', '!=', 'model'), ('parent_id', '=', False)])
            else:
                items = self.env['account.asset'].search(
                    [('company_id', '=', self.company_id.id),
                     ('leasee_contract_ids', '=', False),
                     ('state', '!=', 'model'), ('parent_id', '=', False)])
        abc = []
        for rec in items:
            if rec.leasee_contract_ids:
                asset_bulk = self.env['asset.sell.disposal.lines'].create({
                    'asset_id': rec.id,
                    'from_leasee_contract': True,
                    'action': 'dispose',
                    'contract_end_date': self.disposal_date,
                    'loss_account_id': self.loss_account_id.id,
                    'gain_account_id': self.gain_account_id.id,
                })
            else:
                asset_bulk = self.env['asset.sell.disposal.lines'].create({
                    'asset_id': rec.id,
                    'action': 'dispose',
                    'contract_end_date': self.disposal_date,
                    'loss_account_id': self.loss_account_id.id,
                    'gain_account_id': self.gain_account_id.id,
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

    @api.onchange('from_date', 'to_date', 'company_id', 'state')
    def onchange_from_value(self):
        if self.company_id and self.state and self.from_date and self.to_date:
            self.records = self.env['account.asset'].search_count(
                [('state', '=', self.state),
                 ('company_id', '=', self.company_id.id),
                 ('acquisition_date', '>=', self.from_date),
                 ('acquisition_date', '<=', self.to_date),
                 ('leasee_contract_ids', '=', False),
                 ('state', '!=', 'model'), ('state', '!=', 'model'),
                 ('parent_id', '=', False)])
        elif self.company_id and self.state and self.from_date:
            self.records = self.env['account.asset'].search_count(
                [('state', '=', self.state),
                 ('company_id', '=', self.company_id.id),
                 ('acquisition_date', '>=', self.from_date),
                 ('leasee_contract_ids', '=', False),
                 ('state', '!=', 'model'), ('parent_id', '=', False)])
        elif self.company_id and self.state and self.to_date:
            self.records = self.env['account.asset'].search_count(
                [('state', '=', self.state),
                 ('company_id', '=', self.company_id.id),
                 ('acquisition_date', '<=', self.to_date),
                 ('leasee_contract_ids', '=', False),
                 ('state', '!=', 'model'), ('parent_id', '=', False)])
        elif self.company_id and self.state:
            self.records = self.env['account.asset'].search_count(
                [('state', '=', self.state),
                 ('company_id', '=', self.company_id.id),
                 ('leasee_contract_ids', '=', False),
                 ('state', '!=', 'model'), ('parent_id', '=', False)])
        else:
            self.records = self.env['account.asset'].search_count(
                [('company_id', '=', self.company_id.id),
                 ('leasee_contract_ids', '=', False),
                 ('state', '!=', 'model'), ('parent_id', '=', False)])
