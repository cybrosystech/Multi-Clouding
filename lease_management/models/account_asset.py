# -*- coding: utf-8 -*-
""" init object """
import calendar
from math import copysign
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError
from odoo.tools import float_compare
from dateutil.relativedelta import relativedelta


import logging

LOGGER = logging.getLogger(__name__)


def copy_if_not_zero(a, b):
    if b:
        return a
    else:
        return 0


class AccountAsset(models.Model):
    _inherit = 'account.asset'

    leasee_contract_ids = fields.One2many(comodel_name="leasee.contract", inverse_name="asset_id" )

    def action_set_to_close(self):
        """ Returns an action opening the asset pause wizard."""
        self.ensure_one()
        if self.leasee_contract_ids:
            new_wizard = self.env['account.asset.sell'].create({
                'asset_id': self.id,
                'from_leasee_contract': True,
                'action': 'dispose',
            })
            return {
                'name': _('Sell Asset'),
                'view_mode': 'form',
                'res_model': 'account.asset.sell',
                'type': 'ir.actions.act_window',
                'target': 'new',
                'res_id': new_wizard.id,
            }
        else:
            return super(AccountAsset, self).action_set_to_close()

    def _get_disposal_moves(self, invoice_line_ids, disposal_date):
        def get_line(asset, amount, account):
            return (0, 0, {
                'name': asset.name,
                'account_id': account.id,
                'debit': 0.0 if float_compare(amount, 0.0, precision_digits=prec) > 0 else -amount,
                'credit': amount if float_compare(amount, 0.0, precision_digits=prec) > 0 else 0.0,
                'analytic_account_id': account_analytic_id.id if asset.asset_type == 'sale' or asset.leasee_contract_ids else False,
                'analytic_tag_ids': [(6, 0, analytic_tag_ids.ids)] if asset.asset_type == 'sale' else False,
                'currency_id': current_currency.id,
                'amount_currency': -asset.value_residual,
                'project_site_id': asset.project_site_id.id,
                'type_id': asset.type_id.id,
                'location_id': asset.location_id.id,
            })
        if len(self.leasee_contract_ids) == 1:
            move_ids = []
            assert len(self) == len(invoice_line_ids)
            for asset, invoice_line_id in zip(self, invoice_line_ids):
                if asset.parent_id.leasee_contract_ids:
                    continue
                if disposal_date < max(asset.depreciation_move_ids.filtered(
                        lambda x: not x.reversal_move_id and x.state == 'posted').mapped('date') or [fields.Date.today()]):
                    if invoice_line_id:
                        raise UserError(
                            'There are depreciation posted after the invoice date (%s).\nPlease revert them or change the date of the invoice.' % disposal_date)
                    else:
                        raise UserError('There are depreciation posted in the future, please revert them.')
                disposal_date = self.env.context.get('disposal_date') or disposal_date
                account_analytic_id = asset.account_analytic_id
                analytic_tag_ids = asset.analytic_tag_ids
                company_currency = asset.company_id.currency_id
                current_currency = asset.currency_id
                prec = company_currency.decimal_places
                if self.leasee_contract_ids:
                    self.create_last_termination_move(disposal_date)
                unposted_depreciation_move_ids = asset.depreciation_move_ids.filtered(lambda x: x.state == 'draft')

                old_values = {
                    'method_number': asset.method_number,
                }
                # Remove all unposted depr. lines
                commands = [(2, line_id.id, False) for line_id in unposted_depreciation_move_ids]

                # Create a new depr. line with the residual amount and post it
                asset_sequence = len(asset.depreciation_move_ids) - len(unposted_depreciation_move_ids) + 1

                initial_amount = asset.original_value
                initial_account = asset.original_move_line_ids.account_id if len(
                    asset.original_move_line_ids.account_id) == 1 else asset.account_asset_id
                depreciation_moves = asset.depreciation_move_ids.filtered(
                    lambda r: r.state == 'posted' and not (r.reversal_move_id and r.reversal_move_id[0].state == 'posted'))
                depreciated_amount = copysign(sum(depreciation_moves.mapped('amount_total')), -initial_amount)
                depreciation_account = asset.account_depreciation_id
                invoice_amount = copysign(invoice_line_id.price_subtotal, -initial_amount)
                invoice_account = invoice_line_id.account_id
                difference = -initial_amount - depreciated_amount - invoice_amount
                difference_account = asset.company_id.gain_account_id if difference > 0 else asset.company_id.loss_account_id
                value_residual = asset.value_residual
                if self.leasee_contract_ids:
                    # initial_amount = asset.book_value

                    if asset.children_ids:
                        initial_amount += sum(asset.children_ids.mapped('original_value'))
                        # value_residual += sum(asset.children_ids.mapped('value_residual'))
                        child_depreciation_moves = asset.children_ids.depreciation_move_ids.filtered(lambda r: r.state == 'posted' and not (r.reversal_move_id and r.reversal_move_id[0].state == 'posted'))
                        depreciated_amount += sum(move.amount_total *(-1 if move.asset_id.original_value > 0 else 1) for move in child_depreciation_moves)
                    termination_residual = self.leasee_contract_ids.get_interest_amount_termination_amount(disposal_date)
                    move = self.leasee_contract_ids.create_interset_move(self.env['leasee.installment'] , disposal_date, termination_residual)
                    if move:
                        move.auto_post = False
                        move.action_post()
                    value_residual = initial_amount + depreciated_amount
                    remaining_leasee_amount = -1 * (self.leasee_contract_ids.remaining_lease_liability)
                    leasee_difference = -value_residual - remaining_leasee_amount
                    # leasee_difference = -asset.book_value - remaining_leasee_amount
                    leasee_difference_account = asset.company_id.gain_account_id if difference > 0 else asset.company_id.loss_account_id
                    short_leasee_account = self.leasee_contract_ids.lease_liability_account_id
                    short_lease_liability_amount = self.leasee_contract_ids.remaining_short_lease_liability
                    short_remaining_leasee_amount = -1 * short_lease_liability_amount
                    long_leasee_account = self.leasee_contract_ids.long_lease_liability_account_id
                    remaining_long_lease_liability = -1 * self.leasee_contract_ids.remaining_long_lease_liability
                    line_datas = [(initial_amount, initial_account), (short_remaining_leasee_amount, short_leasee_account),
                                   (remaining_long_lease_liability, long_leasee_account),(invoice_amount, invoice_account),
                                  (leasee_difference, leasee_difference_account),(depreciated_amount, depreciation_account)]
                    if not invoice_line_id:
                        del line_datas[3]
                else:
                    difference = -initial_amount - depreciated_amount - invoice_amount
                    difference_account = asset.company_id.gain_account_id if difference > 0 else asset.company_id.loss_account_id
                    line_datas = [(initial_amount, initial_account), (depreciated_amount, depreciation_account),
                                  (invoice_amount, invoice_account), (difference, difference_account)]
                    if not invoice_line_id:
                        del line_datas[2]
                vals = {
                    'amount_total': current_currency._convert(value_residual, company_currency, asset.company_id,
                                                              disposal_date),
                    'asset_id': asset.id,
                    'ref': asset.name + ': ' + (_('Disposal') if not invoice_line_id else _('Sale')),
                    'asset_remaining_value': 0,
                    'asset_depreciated_value': max(asset.depreciation_move_ids.filtered(lambda x: x.state == 'posted'),
                                                   key=lambda x: x.date,
                                                   default=self.env['account.move']).asset_depreciated_value,
                    'date': disposal_date,
                    'journal_id': asset.journal_id.id,
                    'line_ids': [get_line(asset, amount, account) for amount, account in line_datas if account],
                    'leasee_contract_id': self.leasee_contract_ids.id,
                }
                commands.append((0, 0, vals))
                asset.write({'depreciation_move_ids': commands, 'method_number': asset_sequence})
                tracked_fields = self.env['account.asset'].fields_get(['method_number'])
                changes, tracking_value_ids = asset._message_track(tracked_fields, old_values)
                if changes:
                    asset.message_post(body=_('Asset sold or disposed. Accounting entry awaiting for validation.'),
                                       tracking_value_ids=tracking_value_ids)
                move_ids += self.env['account.move'].search([('asset_id', '=', asset.id), ('state', '=', 'draft')]).ids
            self.leasee_contract_ids.process_termination()
            return move_ids
        else:
            return super(AccountAsset, self)._get_disposal_moves(invoice_line_ids, disposal_date)

    def create_last_termination_move(self, disposal_date):
        end_move = self.depreciation_move_ids.filtered(lambda m: m.date.month == disposal_date.month and m.date.year == disposal_date.year)
        start_month = disposal_date.replace(day=1)
        end_month = start_month + relativedelta(months=1, days=-1)
        ratio = ((disposal_date - start_month).days + 1) / ((end_month - start_month).days + 1)
        if not end_move or not end_move.line_ids:
            raise ValidationError(_('Please post the asset first'))
        new_value = abs(end_move.line_ids[0].debit - end_move.line_ids[0].credit) * ratio
        end_move.write({
            'date': disposal_date,
            'line_ids':[(1, line.id,{'debit': new_value if line.debit else 0,'credit': new_value if line.credit else 0 }) for line in end_move.line_ids]
        })
        end_move.auto_post = False
        end_move.action_post()

    def set_to_close(self, invoice_line_id, date=None):
        if self.env.context.get('disposal_date'):
            date = self.env.context.get('disposal_date')
        return super(AccountAsset, self).set_to_close(invoice_line_id, date)

    def _recompute_board(self, depreciation_number, starting_sequence,
                         amount_to_depreciate, depreciation_date,
                         already_depreciated_amount, amount_change_ids, depreciation_months, total_days):
        move_vals = super(AccountAsset, self)._recompute_board(depreciation_number, starting_sequence,
                         amount_to_depreciate, depreciation_date,
                         already_depreciated_amount, amount_change_ids, depreciation_months, total_days)
        if self._context.get('decrease'):
            if move_vals:
                first_date = self.prorata_date
                if int(self.method_period) % 12 != 0:
                    month_days = calendar.monthrange(first_date.year, first_date.month)[1]
                    days = month_days - first_date.day + 1
                    prorata_factor = days / month_days
                else:
                    total_days = (depreciation_date.year % 4) and 365 or 366
                    days = (self.company_id.compute_fiscalyear_dates(first_date)['date_to'] - first_date).days + 1
                    prorata_factor = days / total_days

                move_vals[1]['line_ids'][0][2]['debit'] = move_vals[-2]['line_ids'][0][2]['debit']
                move_vals[1]['line_ids'][0][2]['credit'] = move_vals[-2]['line_ids'][0][2]['credit']
                move_vals[1]['line_ids'][0][2]['amount_currency'] = move_vals[-2]['line_ids'][0][2]['amount_currency']
                move_vals[1]['line_ids'][1][2]['debit'] = move_vals[-2]['line_ids'][1][2]['debit']
                move_vals[1]['line_ids'][1][2]['credit'] = move_vals[-2]['line_ids'][1][2]['credit']
                move_vals[1]['line_ids'][1][2]['amount_currency'] = move_vals[-2]['line_ids'][1][2]['amount_currency']

                move_vals[0]['line_ids'][0][2]['debit'] = move_vals[-2]['line_ids'][0][2]['debit'] * prorata_factor
                move_vals[0]['line_ids'][0][2]['credit'] = move_vals[-2]['line_ids'][0][2]['credit'] * prorata_factor
                move_vals[0]['line_ids'][0][2]['amount_currency'] = move_vals[-2]['line_ids'][0][2]['amount_currency'] * prorata_factor
                move_vals[0]['line_ids'][1][2]['debit'] = move_vals[-2]['line_ids'][1][2]['debit'] * prorata_factor
                move_vals[0]['line_ids'][1][2]['credit'] = move_vals[-2]['line_ids'][1][2]['credit'] * prorata_factor
                move_vals[0]['line_ids'][1][2]['amount_currency'] = move_vals[-2]['line_ids'][1][2]['amount_currency'] * prorata_factor

                asset_depreciated_value = 0
                for vals in move_vals[:-1]:
                    amount = abs(vals['line_ids'][0][2]['debit'] - vals['line_ids'][0][2]['credit'])
                    asset_depreciated_value -= amount
                    vals['amount_total'] = amount
                    vals['asset_depreciated_value'] = asset_depreciated_value
                    asset_remaining_value = self.original_value - asset_depreciated_value
                    vals['asset_remaining_value'] = asset_remaining_value

                amount = abs(self.original_value - asset_depreciated_value)
                move_vals[-1]['amount_total'] = amount
                move_vals[-1]['asset_depreciated_value'] = self.original_value
                move_vals[-1]['asset_remaining_value'] = 0
                move_vals[-1]['line_ids'][0][2]['debit'] = copy_if_not_zero(amount, move_vals[-2]['line_ids'][0][2]['debit'])
                move_vals[-1]['line_ids'][0][2]['credit'] = copy_if_not_zero(amount, move_vals[-2]['line_ids'][0][2]['credit'])
                move_vals[-1]['line_ids'][0][2]['amount_currency'] = copy_if_not_zero(amount,  move_vals[-2]['line_ids'][0][2]['amount_currency'])
                move_vals[-1]['line_ids'][1][2]['debit'] = copy_if_not_zero(amount, move_vals[-2]['line_ids'][1][2]['debit'])
                move_vals[-1]['line_ids'][1][2]['credit'] = copy_if_not_zero(amount, move_vals[-2]['line_ids'][1][2]['credit'])
                move_vals[-1]['line_ids'][1][2]['amount_currency'] = copy_if_not_zero(amount, move_vals[-2]['line_ids'][1][2]['amount_currency'])

        return move_vals



