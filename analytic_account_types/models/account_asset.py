# -*- coding: utf-8 -*-

import calendar
from dateutil.relativedelta import relativedelta
from math import copysign

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_is_zero, float_round
import logging
_logger = logging.getLogger(__name__)

class AccountAsset(models.Model):
    _inherit = 'account.asset'

    project_site_id = fields.Many2one(comodel_name="account.analytic.account", string="Project/Site",
                                      domain=[('analytic_account_type', '=', 'project_site')], required=False, )
    type_id = fields.Many2one(comodel_name="account.analytic.account", string="Type",
                              domain=[('analytic_account_type', '=', 'type')], required=False, )
    location_id = fields.Many2one(comodel_name="account.analytic.account", string="Location",
                                  domain=[('analytic_account_type', '=', 'location')], required=False, )


    @api.onchange('project_site_id')
    def _onchange_project_site_id(self):
        for rec in self:
            rec.type_id = rec.project_site_id.analytic_type_filter_id.id
            rec.location_id = rec.project_site_id.analytic_location_id.id

    def write(self, vals):
        res = super(AccountAsset, self).write(vals)
        if 'project_site_id' in vals or 'type_id' in vals or 'location_id' in vals:
            moves = self.depreciation_move_ids.filtered(lambda line: line.state == 'draft')
            for move in moves:
                for line in move.line_ids:
                    line.write({
                        'project_site_id': self.project_site_id.id if self.project_site_id else False,
                        'type_id': self.type_id.id if self.type_id else False,
                        'location_id': self.location_id.id if self.location_id else False,
                    })
        return res

    @api.onchange('model_id')
    def _onchange_model_id(self):
        model = self.model_id
        if model:
            _logger.info("mmmmmmmm")

            self.method = model.method
            self.method_number = model.method_number
            self.method_period = model.method_period
            self.method_progress_factor = model.method_progress_factor
            self.prorata = model.prorata
            self.prorata_date = fields.Date.today()
            if model.account_analytic_id:
                self.account_analytic_id = model.account_analytic_id.id
            if model.project_site_id:
                self.project_site_id = model.project_site_id.id
            if model.type_id:

                self.type_id = model.type_id.id
            if model.location_id:
                self.location_id = model.location_id.id
            self.analytic_tag_ids = [(6, 0, model.analytic_tag_ids.ids)]
            self.account_asset_id = model.account_asset_id.id
            self.account_depreciation_id = model.account_depreciation_id
            self.account_depreciation_expense_id = model.account_depreciation_expense_id
            self.journal_id = model.journal_id

    def _get_disposal_moves(self, invoice_line_ids, disposal_date):
        def get_line(asset, amount, account):
            _logger.info("llllllll")

            return (0, 0, {
                'name': asset.name,
                'account_id': account.id,
                'debit': 0.0 if float_compare(amount, 0.0, precision_digits=prec) > 0 else -amount,
                'credit': amount if float_compare(amount, 0.0, precision_digits=prec) > 0 else 0.0,
                'analytic_account_id': account_analytic_id.id if asset.asset_type == 'sale' else False,
                'project_site_id': project_site_id.id if asset.asset_type == 'sale' else False,
                'type_id': type_id.id if asset.asset_type == 'sale' else False,
                'location_id': location_id.id if asset.asset_type == 'sale' else False,
                'analytic_tag_ids': [(6, 0, analytic_tag_ids.ids)] if asset.asset_type == 'sale' else False,
                'currency_id': company_currency != current_currency and current_currency.id or False,
                'amount_currency': company_currency != current_currency and - 1.0 * asset.value_residual or 0.0,
            })

        move_ids = []
        assert len(self) == len(invoice_line_ids)
        for asset, invoice_line_id in zip(self, invoice_line_ids):
            if disposal_date < max(asset.depreciation_move_ids.filtered(lambda x: not x.reversal_move_id and x.state == 'posted').mapped('date') or [fields.Date.today()]):
                if invoice_line_id:
                    raise UserError('There are depreciation posted after the invoice date (%s).\nPlease revert them or change the date of the invoice.' % disposal_date)
                else:
                    raise UserError('There are depreciation posted in the future, please revert them.')
            account_analytic_id = asset.account_analytic_id
            project_site_id = asset.project_site_id
            type_id = asset.type_id
            location_id = asset.location_id
            analytic_tag_ids = asset.analytic_tag_ids
            company_currency = asset.company_id.currency_id
            current_currency = asset.currency_id
            prec = company_currency.decimal_places
            unposted_depreciation_move_ids = asset.depreciation_move_ids.filtered(lambda x: x.state == 'draft')
            if unposted_depreciation_move_ids:
                old_values = {
                    'method_number': asset.method_number,
                }

                # Remove all unposted depr. lines
                commands = [(2, line_id.id, False) for line_id in unposted_depreciation_move_ids]

                # Create a new depr. line with the residual amount and post it
                asset_sequence = len(asset.depreciation_move_ids) - len(unposted_depreciation_move_ids) + 1

                initial_amount = asset.original_value
                initial_account = asset.original_move_line_ids.account_id if len(asset.original_move_line_ids.account_id) == 1 else asset.account_asset_id
                depreciated_amount = copysign(sum(asset.depreciation_move_ids.filtered(lambda r: r.state == 'posted').mapped('amount_total')), -initial_amount)
                depreciation_account = asset.account_depreciation_id
                invoice_amount = copysign(invoice_line_id.price_subtotal, -initial_amount)
                invoice_account = invoice_line_id.account_id
                difference = -initial_amount - depreciated_amount - invoice_amount
                difference_account = asset.company_id.gain_account_id if difference > 0 else asset.company_id.loss_account_id
                line_datas = [(initial_amount, initial_account), (depreciated_amount, depreciation_account), (invoice_amount, invoice_account), (difference, difference_account)]
                if not invoice_line_id:
                    del line_datas[2]
                vals = {
                    'amount_total': current_currency._convert(asset.value_residual, company_currency, asset.company_id, disposal_date),
                    'asset_id': asset.id,
                    'ref': asset.name + ': ' + (_('Disposal') if not invoice_line_id else _('Sale')),
                    'asset_remaining_value': 0,
                    'asset_depreciated_value': max(asset.depreciation_move_ids.filtered(lambda x: x.state == 'posted'), key=lambda x: x.date, default=self.env['account.move']).asset_depreciated_value,
                    'date': disposal_date,
                    'journal_id': asset.journal_id.id,
                    'line_ids': [get_line(asset, amount, account) for amount, account in line_datas if account],
                }
                commands.append((0, 0, vals))
                asset.write({'depreciation_move_ids': commands, 'method_number': asset_sequence})
                tracked_fields = self.env['account.asset'].fields_get(['method_number'])
                changes, tracking_value_ids = asset._message_track(tracked_fields, old_values)
                if changes:
                    asset.message_post(body=_('Asset sold or disposed. Accounting entry awaiting for validation.'), tracking_value_ids=tracking_value_ids)
                move_ids += self.env['account.move'].search([('asset_id', '=', asset.id), ('state', '=', 'draft')]).ids

        return move_ids

    @api.constrains('original_move_line_ids')
    def check_assets(self):
        _logger.info("uuuuuuu")
        for asset in self:
            for line in asset.original_move_line_ids:
                    asset.account_analytic_id = line.analytic_account_id.id
                    asset.project_site_id = line.project_site_id.id
                    asset.location_id = line.location_id.id
                    asset.type_id = line.type_id.id
                    _logger.info("KKKKKK{}-{}-{}".format(asset.account_analytic_id,asset.project_site_id,asset.location_id))


