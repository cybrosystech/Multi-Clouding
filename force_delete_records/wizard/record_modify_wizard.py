from odoo import models, fields, api


class ModelRecordUnlink(models.Model):
    _name = 'unlink.records.wizard'

    state = fields.Selection(
        [('draft', 'Draft'), ('open', 'Running'), ('close', 'Close'),
         ('paused', 'On Hold'), ('to_approve', 'To Approve')])
    company_id = fields.Many2one('res.company', string='Company')
    records = fields.Integer()
    limit = fields.Integer()

    @api.onchange('company_id', 'state')
    def _onchange_compute_assets(self):
        domain = [('asset_type', '=', 'purchase')]
        if self.company_id:
            domain += [('company_id', '=', self.company_id.id)]
        if self.state:
            domain += [('state', '=', self.state)]
        print(domain)
        assets = self.env['account.asset'].search(domain)
        print(assets)
        self.records = len(assets)

    def delete_records(self):
        domain = [('asset_type', '=', 'purchase')]
        if self.company_id:
            domain += [('company_id', '=', self.company_id.id)]
        if self.state:
            domain += [('state', '=', self.state)]
        print(domain)
        assets = self.env['account.asset'].search(domain, limit=self.limit)
        for rec in assets:
            for journal in rec.depreciation_move_ids:
                journal.with_context(force_delete=True).unlink()
            rec.state = 'draft'
