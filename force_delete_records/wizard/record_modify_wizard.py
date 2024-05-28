from odoo import models, fields, api


class ModelRecordUnlink(models.Model):
    _name = 'unlink.records.wizard'

    state = fields.Selection(
        [('draft', 'Draft'), ('open', 'Running'), ('close', 'Close'),
         ('paused', 'On Hold'), ('to_approve', 'To Approve')])
    company_id = fields.Many2one('res.company', string='Company')
    records = fields.Integer()
    limit = fields.Integer()
    state_entry = fields.Selection([('assets', 'Assets'),
                                    ('journal', 'Journal Entries')])
    journal_state = fields.Selection([('draft', 'Draft'), ('to_approve', 'To Approve'),
                                      ('posted', 'Posted'), ('cancel', 'Cancelled')])
    journal_ids = fields.Many2many('account.journal', string='Journals',default=lambda self: self.env['account.journal'].search([('company_id', '=', self.company_id.id)]))

    @api.onchange('company_id', 'state', 'journal_state', 'state_entry','journal_ids')
    def _onchange_compute_assets(self):
        if self.state_entry == 'assets':
            domain = [('asset_type', '=', 'purchase')]
            environment = self.env['account.asset']
            if self.state:
                domain += [('state', '=', self.state)]
        else:
            domain = []
            environment = self.env['account.move']
            if self.journal_state:
                domain += [('state', '=', self.journal_state)]
        if self.company_id:
            domain += [('company_id', '=', self.company_id.id)]
        if self.journal_ids:
            domain += [('journal_id', 'in', self.journal_ids.ids)]
        assets = environment.search(domain)
        self.records = len(assets)

    def delete_records(self):
        if self.state_entry == 'assets':
            domain = [('asset_type', '=', 'purchase')]
            environment = self.env['account.asset']
            if self.state:
                domain += [('state', '=', self.state)]
        else:
            domain = []
            environment = self.env['account.move']
            if self.journal_state:
                domain += [('state', '=', self.journal_state)]
        if self.company_id:
            domain += [('company_id', '=', self.company_id.id)]
        if self.journal_ids:
            domain += [('journal_id', 'in', self.journal_ids.ids)]

        items = environment.search(domain, limit=self.limit)
        if self.state_entry == 'assets':
            for rec in items:
                for journal in rec.depreciation_move_ids:
                    journal.with_context(force_delete=True).unlink()
                rec.state = 'draft'
        else:
            items.with_context(force_delete=True).unlink()
