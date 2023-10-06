from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    project_site_id = fields.Many2one('account.analytic.account',
                                      string="Project Site",
                                      compute='compute_project_site',
                                      help=" Project Site",
                                      search='_search_project_site_id')

    @api.depends('invoice_line_ids')
    def compute_project_site(self):
        for rec in self:
            move_line_id = self.env['account.move.line'].search(
                [('id', 'in', rec.invoice_line_ids.ids)], limit=1,
                order="id ASC")
            if move_line_id:
                rec.project_site_id = move_line_id.project_site_id.id
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

    def _search_virtual_remaining_leaves(self, operator, value):
        value = float(value)
        leave_types = self.env['hr.leave.type'].search([])
        valid_leave_types = self.env['hr.leave.type']

        for leave_type in leave_types:
            if leave_type.allocation_type != 'no':
                if operator == '>' and leave_type.virtual_remaining_leaves > value:
                    valid_leave_types |= leave_type
                elif operator == '<' and leave_type.virtual_remaining_leaves < value:
                    valid_leave_types |= leave_type
                elif operator == '>=' and leave_type.virtual_remaining_leaves >= value:
                    valid_leave_types |= leave_type
                elif operator == '<=' and leave_type.virtual_remaining_leaves <= value:
                    valid_leave_types |= leave_type
                elif operator == '=' and leave_type.virtual_remaining_leaves == value:
                    valid_leave_types |= leave_type
                elif operator == '!=' and leave_type.virtual_remaining_leaves != value:
                    valid_leave_types |= leave_type
            else:
                valid_leave_types |= leave_type

        return [('id', 'in', valid_leave_types.ids)]
