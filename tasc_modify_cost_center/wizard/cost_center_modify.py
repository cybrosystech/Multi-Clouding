from odoo import models, fields, api


class ModelRecordUnlink(models.Model):
    _name = 'cost.center.modify'

    company_id = fields.Many2one('res.company', string='Company', required=True)
    analytic_account_types = fields.Selection(string="Analytic Type",
                                              default='cost_center', selection=[
            ('cost_center', 'Cost Center'), ('project_site', 'Project/Site')],
                                              required=True)
    records = fields.Integer(string="Records")
    limit = fields.Integer(string="Limit", required=True)
    journal_state = fields.Selection(
        [('draft', 'Draft'), ('to_approve', 'To Approve'),
         ('posted', 'Posted'), ('cancel', 'Cancelled')])

    from_value = fields.Many2one('account.analytic.account',
                                 string="From",
                                 domain="[('company_id', '=', company_id),'|',('analytic_account_type','=',analytic_account_types),('analytic_account_type','=',False)]")
    to_value = fields.Many2one('account.analytic.account',
                               string="To", required=True,
                               domain="[('company_id', '=', company_id),'|',('analytic_account_type','=',analytic_account_types),('analytic_account_type','=',False)]")
    year = fields.Char(default=lambda self: fields.Date.today().year)

    def modify_cost_center(self):
        if self.analytic_account_types == 'cost_center':
            if self.journal_state:
                if self.year:
                    items = self.env['account.move.line'].search(
                        [('analytic_account_id', '=', self.from_value.id),
                         ('company_id', '=', self.company_id.id),
                         ('move_id.state', '=', self.journal_state), ],
                        limit=self.limit).filtered(
                        lambda l: l.move_id.date.year == int(self.year))
                else:
                    items = self.env['account.move.line'].search(
                        [('analytic_account_id', '=', self.from_value.id),
                         ('company_id', '=', self.company_id.id),
                         ('move_id.state', '=', self.journal_state), ],
                        limit=self.limit)
            else:
                if self.year:
                    items = self.env['account.move.line'].search(
                        [('analytic_account_id', '=', self.from_value.id),
                         ('company_id', '=', self.company_id.id)],
                        limit=self.limit)
                else:
                    items = self.env['account.move.line'].search(
                        [('analytic_account_id', '=', self.from_value.id),
                         ('company_id', '=', self.company_id.id)],
                        limit=self.limit).filtered(
                        lambda l: l.move_id.date.year == int(self.year))
            print("items", items)
            for item in items:
                item.analytic_account_id = self.to_value.id
                analytic_line = self.env['account.analytic.line'].search(
                    [('move_id', '=', item.id)])
                analytic_line.account_id = self.to_value.id
        else:
            if self.journal_state:
                if self.year:
                    items = self.env['account.move.line'].search(
                        [('project_site_id', '=', self.from_value.id),
                         ('company_id', '=', self.company_id.id),
                         ('move_id.state', '=', self.journal_state)
                         ],
                        limit=self.limit).filtered(
                        lambda l: l.move_id.date.year == int(self.year))
                else:
                    items = self.env['account.move.line'].search(
                        [('project_site_id', '=', self.from_value.id),
                         ('company_id', '=', self.company_id.id),
                         ('move_id.state', '=', self.journal_state)
                         ],
                        limit=self.limit)
            else:
                if self.year:
                    items = self.env['account.move.line'].search(
                        [('project_site_id', '=', self.from_value.id),
                         ('company_id', '=', self.company_id.id)],
                        limit=self.limit)
                else:
                    items = self.env['account.move.line'].search(
                        [('project_site_id', '=', self.from_value.id),
                         ('company_id', '=', self.company_id.id)],
                        limit=self.limit).filtered(
                        lambda l: l.move_id.date.year == int(self.year))
            for item in items:
                item.project_site_id = self.to_value.id
                analytic_line = self.env['account.analytic.line'].search(
                    [('move_id', '=', item.id)])
                analytic_line.project_site_id = self.to_value.id

    @api.onchange('from_value', 'company_id', 'journal_state', 'year')
    def onchange_from_value(self):
        if self.analytic_account_types == 'cost_center':
            if self.journal_state:
                if self.year:
                    items = self.env['account.move.line'].search(
                        [('analytic_account_id', '=', self.from_value.id),
                         ('company_id', '=', self.company_id.id),
                         ('move_id.state', '=', self.journal_state),
                         ('move_id.date', '!=', False)],
                    ).filtered(
                        lambda l: l.move_id.date.year == int(self.year))
                    items_count = len(items)
                else:
                    items_count = self.env['account.move.line'].search_count(
                        [('analytic_account_id', '=', self.from_value.id),
                         ('company_id', '=', self.company_id.id),
                         ('move_id.state', '=', self.journal_state)],
                    )
            else:
                if self.year:
                    items = self.env['account.move.line'].search(
                        [('analytic_account_id', '=', self.from_value.id),
                         ('company_id', '=', self.company_id.id),
                         ]).filtered(
                        lambda l: l.move_id.date.year == int(self.year))
                    items_count = len(items)
                else:
                    items_count = self.env['account.move.line'].search_count(
                        [('analytic_account_id', '=', self.from_value.id),
                         ('company_id', '=', self.company_id.id),
                         ])
            self.records = items_count
        else:
            if self.journal_state:
                if self.year:
                    items = self.env['account.move.line'].search(
                        [('project_site_id', '=', self.from_value.id),
                         ('company_id', '=', self.company_id.id),
                         ('move_id.state', '=', self.journal_state)],
                    ).filtered(
                        lambda l: l.move_id.date.year == int(self.year))
                    items_count = len(items)
                else:
                    items_count = self.env['account.move.line'].search_count(
                        [('project_site_id', '=', self.from_value.id),
                         ('company_id', '=', self.company_id.id),
                         ('move_id.state', '=', self.journal_state)],
                    )
            else:
                if self.year:
                    items = self.env['account.move.line'].search(
                        [('project_site_id', '=', self.from_value.id),
                         ('company_id', '=', self.company_id.id),
                         ]).filtered(lambda l: l.date.year == int(self.year))
                    items_count = len(items)
                else:
                    items_count = self.env['account.move.line'].search_count(
                        [('project_site_id', '=', self.from_value.id),
                         ('company_id', '=', self.company_id.id),
                         ])
            self.records = items_count
