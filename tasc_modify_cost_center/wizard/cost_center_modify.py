from odoo import models, fields, api


class ModelRecordUnlink(models.Model):
    _name = 'cost.center.modify'

    company_id = fields.Many2one('res.company', string='Company', required=True)
    records = fields.Integer(string="Records")
    limit = fields.Integer(string="Limit", required=True)
    journal_state = fields.Selection(
        [('draft', 'Draft'), ('to_approve', 'To Approve'),
         ('posted', 'Posted'), ('cancel', 'Cancelled')])
    from_value = fields.Many2one('account.analytic.account',
                                 string="From Cost Center", required=True,
                                 domain="[('company_id', '=', company_id)]")
    to_value = fields.Many2one('account.analytic.account',
                               string="To Cost Center", required=True,
                               domain="[('company_id', '=', company_id)]")

    def modify_cost_center(self):
        print("modify_cost_center")
        if self.journal_state:
            items = self.env['account.move.line'].search(
                [('analytic_account_id', '=', self.from_value.id),
                 ('company_id', '=', self.company_id.id)],
                limit=self.limit)
        else:
            items = self.env['account.move.line'].search(
                [('analytic_account_id', '=', self.from_value.id),
                 ('company_id', '=', self.company_id.id),
                 ('move_id.state', '=', self.journal_state)],
                limit=self.limit)
        print("items", items)
        for item in items:
            item.analytic_account_id = self.to_value.id
            print("ddddddddddd", item)

    @api.onchange('from_value', 'company_id', 'journal_state')
    def onchange_from_value(self):
        print("uuuuuuuuuuu")
        if self.journal_state and self.limit:
            items_count = self.env['account.move.line'].search_count(
                [('analytic_account_id', '=', self.from_value.id),
                 ('company_id', '=', self.company_id.id)],
                limit=self.limit)
        else:
            items_count = self.env['account.move.line'].search_count(
                [('analytic_account_id', '=', self.from_value.id),
                 ('company_id', '=', self.company_id.id),
                 ('move_id.state', '=', self.journal_state)])
        self.records = items_count
