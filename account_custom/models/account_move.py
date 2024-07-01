from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    project_site_id = fields.Many2one('account.analytic.account',
                                      string="Project Site",
                                      compute='compute_project_site',
                                      help=" Project Site",
                                      search='_search_project_site_id')

    @api.depends()
    def compute_project_site(self):
        for rec in self:
            move_line_id = self.env['account.move.line'].search(
                [('id', 'in', rec.invoice_line_ids.ids)], limit=1,
                order="id ASC")
            if move_line_id:
                # rec.project_site_id = move_line_id.project_site_id.id
                rec.project_site_id = False

            else:
                rec.project_site_id = False

    def _search_project_site_id(self, operator, value):
        move_ids = self.env['account.move'].search([])
        if operator == '=':
            move_ids = move_ids.filtered(
                lambda l: l.project_site_id.name == value)
        if operator == '!=':
            move_ids = move_ids.filtered(
                lambda l: l.project_site_id.name != value)
        if operator == 'ilike':
            project_sites = self.env['account.analytic.account'].search(
                [('name', 'ilike', value)])
            move_ids = move_ids.filtered(
                lambda l: l.project_site_id.id in project_sites.ids)
        if operator == 'not ilike':
            project_sites = self.env['account.analytic.account'].search(
                [('name', 'not ilike', value)])
            move_ids = move_ids.filtered(
                lambda l: l.project_site_id.id in project_sites.ids)
        return [('id', 'in', move_ids.ids)]


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    code = fields.Integer(string="Code", related='account_id.code_num')
