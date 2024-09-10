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
    project_site_id = fields.Many2one('account.analytic.account',
                                 string="Project Site",
                                 domain="[('company_id', '=', company_id),('analytic_account_type','=','project_site')]")
    to_value = fields.Many2one('account.analytic.account',
                               string="To", required=True,
                               domain="[('company_id', '=', company_id),'|',('analytic_account_type','=',analytic_account_types),('analytic_account_type','=',False)]")
    year = fields.Char(default=lambda self: fields.Date.today().year)

    def modify_cost_center(self):
        domain = []

        if self.analytic_account_types == 'cost_center':
            domain.append(('analytic_account_id', '=', self.from_value.id))
        else:
            domain.append(('project_site_id', '=', self.from_value.id))

        domain.append(('company_id', '=', self.company_id.id))

        if self.journal_state:
            domain.append(('move_id.state', '=', self.journal_state))

        if self.project_site_id:
            domain.append(('project_site_id', '=', self.project_site_id.id))

        items = self.env['account.move.line'].search(domain, limit=self.limit)
        if self.year:
            items = items.filtered( lambda l: l.move_id.date.year == int(self.year))

        for item in items:
            if self.analytic_account_types == 'cost_center':
                item.analytic_account_id = self.to_value.id
                item.onchange_project_site()
                analytic_line = self.env['account.analytic.line'].search(
                    [('move_line_id', '=', item.id)])
                analytic_line.account_id = self.to_value.id
            else:
                item.project_site_id = self.to_value.id
                item.onchange_project_site()
                analytic_line = self.env['account.analytic.line'].search(
                    [('move_line_id', '=', item.id)])
                analytic_line.project_site_id = self.to_value.id

    @api.onchange('from_value', 'company_id', 'journal_state', 'year','project_site_id')
    def onchange_from_value(self):
        domain = []

        if self.analytic_account_types == 'cost_center':
            domain.append(('analytic_account_id', '=', self.from_value.id))
        else:
            domain.append(('project_site_id', '=', self.from_value.id))

        domain.append(('company_id', '=', self.company_id.id))

        if self.journal_state:
            domain.append(('move_id.state', '=', self.journal_state))

        if self.project_site_id:
            domain.append(('project_site_id', '=', self.project_site_id.id))

        items = self.env['account.move.line'].search(domain)
        if self.year:
            items = items.filtered(
                lambda l: l.move_id.date.year == int(self.year))
        items_count = len(items)
        self.records = items_count
