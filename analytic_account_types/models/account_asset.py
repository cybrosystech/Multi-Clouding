# -*- coding: utf-8 -*-
from math import copysign
from odoo import api, fields, models, _,SUPERUSER_ID
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class AccountAsset(models.Model):
    _inherit = 'account.asset'

    project_site_id = fields.Many2one(comodel_name="account.analytic.account",
                                      string="Project/Site",
                                      domain=[('analytic_account_type', '=',
                                               'project_site')],
                                      required=True, )
    analytic_account_id = fields.Many2one(
        comodel_name="account.analytic.account",
        string="Cost Center",
        required=True, domain=[
            ('analytic_account_type', '=',
             'cost_center')], )
    site_address = fields.Char(string='Site Address',
                               compute='compute_site_address')
    is_admin = fields.Boolean(string="Is Admin", compute='compute_is_admin')

    @api.depends_context('uid')
    def compute_is_admin(self):
        is_admin = self.env.user.id == SUPERUSER_ID or \
                   self.env.user.has_group('base.group_erp_manager') or \
                   self.env.user.has_group('base.group_system')
        for rec in self:
            rec.is_admin=is_admin

    @api.depends('analytic_distribution')
    def compute_site_address(self):
        for rec in self:
            if not rec.env.context.get('generate_analytic_distribution'):
                rec.site_address = False

    def action_oe_validate(self):
        if self.filtered(lambda aa: aa.state != 'draft'):
            raise UserError(_('Only draft assets can be confirm.'))
        for asset in self:
            asset.validate()

    def write(self, vals):
        res = super(AccountAsset, self).write(vals)
        if 'analytic_distribution' in vals:
            moves = self.depreciation_move_ids.filtered(
                lambda line: line.state == 'draft')
            for move in moves:
                for line in move.line_ids:
                    line.write({
                        'analytic_distribution': self.analytic_distribution if self.analytic_distribution else False,
                    })
        return res

    @api.onchange('model_id')
    def _onchange_model_id(self):
        model = self.model_id
        if model:
            self.method = model.method
            self.method_number = model.method_number
            self.method_period = model.method_period
            self.method_progress_factor = model.method_progress_factor
            if not self.env.context.get('auto_create_asset'):
                self.prorata_date = fields.Date.today()
            if model.analytic_distribution:
                self.analytic_distribution = model.analytic_distribution
            self.account_asset_id = model.account_asset_id.id
            self.account_depreciation_id = model.account_depreciation_id
            self.account_depreciation_expense_id = model.account_depreciation_expense_id
            self.journal_id = model.journal_id

    @api.constrains('original_move_line_ids')
    def check_assets(self):
        for asset in self:
            for line in asset.original_move_line_ids:
                asset.analytic_distribution = line.analytic_distribution

    def _get_disposal_moves(self, invoice_lines_list, disposal_date):
        """Create the move for the disposal of an asset.

        :param invoice_lines_list: list of recordset of `account.move.line`
            Each element of the list corresponds to one record of `self`
            These lines are used to generate the disposal move
        :param disposal_date: the date of the disposal
        """
        def get_line(asset, amount, account):
            return (0, 0, {
                'name': asset.name,
                'account_id': account.id,
                'balance': -amount,
                'analytic_distribution': analytic_distribution,
                'currency_id': asset.currency_id.id,
                'amount_currency': -asset.company_id.currency_id._convert(
                    from_amount=amount,
                    to_currency=asset.currency_id,
                    company=asset.company_id,
                    date=disposal_date,
                )
            })

        move_ids = []
        assert len(self) == len(invoice_lines_list)
        for asset, invoice_line_ids in zip(self, invoice_lines_list):
            asset._create_move_before_date(disposal_date)

            analytic_distribution = asset.analytic_distribution

            dict_invoice = {}
            invoice_amount = 0

            initial_amount = asset.original_value
            initial_account = asset.original_move_line_ids.account_id if len(
                asset.original_move_line_ids.account_id) == 1 else asset.account_asset_id

            all_lines_before_disposal = asset.depreciation_move_ids.filtered(
                lambda x: x.date <= disposal_date)
            depreciated_amount = asset.currency_id.round(copysign(
                sum(all_lines_before_disposal.mapped(
                    'depreciation_value')) + asset.already_depreciated_amount_import,
                -initial_amount,
            ))
            depreciation_account = asset.account_depreciation_id
            for invoice_line in invoice_line_ids:
                dict_invoice[invoice_line.account_id] = copysign(
                    invoice_line.balance, -initial_amount) + dict_invoice.get(
                    invoice_line.account_id, 0)
                invoice_amount += copysign(invoice_line.balance,
                                           -initial_amount)
            list_accounts = [(amount, account) for account, amount in
                             dict_invoice.items()]
            difference = -initial_amount - depreciated_amount - invoice_amount
            difference_account = asset.company_id.gain_account_id if difference > 0 else asset.company_id.loss_account_id
            line_datas = [(initial_amount, initial_account), (
            depreciated_amount, depreciation_account)] + list_accounts + [
                             (difference, difference_account)]
            vals = {
                'asset_id': asset.id,
                'ref': asset.name + ': ' + (
                    _('Disposal') if not invoice_line_ids else _('Sale')),
                'asset_depreciation_beginning_date': disposal_date,
                'date': disposal_date,
                'journal_id': asset.journal_id.id,
                'move_type': 'entry',
                'line_ids': [get_line(asset, amount, account) for
                             amount, account in line_datas if account],
            }
            asset.write({'depreciation_move_ids': [(0, 0, vals)]})
            move_ids += self.env['account.move'].search(
                [('asset_id', '=', asset.id), ('state', '=', 'draft')]).ids

        return move_ids

