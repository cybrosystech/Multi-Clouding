from odoo import models, fields, api


class ModelRecordUnlink(models.Model):
    _name = 'cost.center.modify'

    company_id = fields.Many2one('res.company', string='Company', required=True)
    analytic_account_types = fields.Selection(string="Analytic Type", selection=[('cost_center', 'Cost Center'), ('project_site', 'Project/Site')], required=True)
    records = fields.Integer(string="Records")
    limit = fields.Integer(string="Limit", required=True)
    journal_state = fields.Selection(
        [('draft', 'Draft'), ('to_approve', 'To Approve'),
         ('posted', 'Posted'), ('cancel', 'Cancelled')])
    from_value = fields.Many2one('account.analytic.account',
                                 string="From",
                                 domain="[('company_id', '=', company_id),('analytic_account_type','=',analytic_account_types)]")
    to_value = fields.Many2one('account.analytic.account',
                               string="To", required=True,
                               domain="[('company_id', '=', company_id),('analytic_account_type','=',analytic_account_types)]")

    def modify_cost_center(self):
        print("modify_cost_center")
        if self.analytic_account_types == 'cost_center':
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
                analytic_line = self.env['account.analytic.line'].search([('move_id','=',item.id)])
                analytic_line.account_id = self.to_value.id
        else:
            if self.journal_state:
                items = self.env['account.move.line'].search(
                    [('project_site_id', '=', self.from_value.id),
                     ('company_id', '=', self.company_id.id)],
                    limit=self.limit)
            else:
                items = self.env['account.move.line'].search(
                    [('project_site_id', '=', self.from_value.id),
                     ('company_id', '=', self.company_id.id),
                     ('move_id.state', '=', self.journal_state)],
                    limit=self.limit)
            print("items", items)
            for item in items:
                item.project_site_id = self.to_value.id
                analytic_line = self.env['account.analytic.line'].search([('move_id','=',item.id)])
                analytic_line.project_site_id = self.to_value.id

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
