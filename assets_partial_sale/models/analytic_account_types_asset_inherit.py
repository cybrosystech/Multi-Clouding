from odoo import models, fields, _
from math import copysign
from odoo.tools import float_compare
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta
from odoo.addons.analytic_account_types.models.account_asset import AccountAsset
import logging

_logger = logging.getLogger(__name__)


def _get_disposal_moves(self, invoice_line_ids, disposal_date, partial,
                        partial_amount):
    def get_line(asset, amount, account):
        _logger.info("llllllll")
        if company_currency == current_currency:
            amount = round(amount, 2)
            return (0, 0, {
                'name': asset.name,
                'account_id': account.id,
                'debit': 0.0 if float_compare(amount, 0.0,
                                              precision_digits=prec) > 0 else -amount,
                'credit': amount if float_compare(amount, 0.0,
                                                  precision_digits=prec) > 0 else 0.0,
                'analytic_account_id': account_analytic_id.id if asset.asset_type == 'sale' else False,
                'project_site_id': project_site_id.id if asset.asset_type == 'sale' else False,
                'type_id': type_id.id if asset.asset_type == 'sale' else False,
                'location_id': location_id.id if asset.asset_type == 'sale' else False,
                'analytic_tag_ids': [(6, 0,
                                      analytic_tag_ids.ids)] if asset.asset_type == 'sale' else False,
                'currency_id': company_currency != current_currency and current_currency.id or False,
                'amount_currency': company_currency != current_currency and - 1.0 * asset.value_residual or 0.0,
            })
        else:
            print('//////', current_currency, company_currency)
            amount_test = current_currency._convert(
                    amount, company_currency,
                    asset.company_id, disposal_date)
            return (0, 0, {
                'name': asset.name,
                'account_id': account.id,
                'debit': 0.0 if float_compare(amount_test, 0.0,
                                              precision_digits=prec) > 0 else -amount_test,
                'credit': amount_test if float_compare(amount_test, 0.0,
                                                  precision_digits=prec) > 0 else 0.0,
                'analytic_account_id': account_analytic_id.id if asset.asset_type == 'sale' else False,
                'project_site_id': project_site_id.id if asset.asset_type == 'sale' else False,
                'type_id': type_id.id if asset.asset_type == 'sale' else False,
                'location_id': location_id.id if asset.asset_type == 'sale' else False,
                'analytic_tag_ids': [(6, 0,
                                      analytic_tag_ids.ids)] if asset.asset_type == 'sale' else False,
                'currency_id': company_currency != current_currency and current_currency.id or False,
                'amount_currency': amount,
            })
    print('lllllllllllllkkkkkkkkkkkkkkkkmmmmmmmmmmmmmm')
    move_ids = []
    assert len(self) == len(invoice_line_ids)
    for asset, invoice_line_id in zip(self, invoice_line_ids):
        if disposal_date < max(asset.depreciation_move_ids.filtered(
                lambda x: not x.reversal_move_id and x.state == 'posted').mapped(
            'date') or [fields.Date.today()]):
            if invoice_line_id:
                raise UserError(
                    'There are depreciation posted after the invoice date (%s).\nPlease revert them or change the date of the invoice.' % disposal_date)
            else:
                raise UserError(
                    'There are depreciation posted in the future, please revert them.')
        account_analytic_id = asset.account_analytic_id
        project_site_id = asset.project_site_id
        type_id = asset.type_id
        location_id = asset.location_id
        analytic_tag_ids = asset.analytic_tag_ids
        company_currency = asset.company_id.currency_id
        current_currency = asset.currency_id
        prec = company_currency.decimal_places
        unposted_depreciation_move_ids = asset.depreciation_move_ids.filtered(
            lambda x: x.state == 'draft')
        if unposted_depreciation_move_ids:
            old_values = {
                'method_number': asset.method_number,
            }

            # Remove all unposted depr. lines
            commands = [(2, line_id.id, False) for line_id in
                        unposted_depreciation_move_ids]

            # Create a new depr. line with the residual amount and post it
            asset_sequence = len(asset.depreciation_move_ids) - len(
                unposted_depreciation_move_ids) + 1

            initial_amount = asset.original_value
            initial_account = asset.original_move_line_ids.account_id if len(
                asset.original_move_line_ids.account_id) == 1 else asset.account_asset_id
            depreciated_amount = copysign(
                sum(asset.depreciation_move_ids.filtered(
                    lambda r: r.state in ['posted', 'cancel']).mapped('amount_total')),
                -initial_amount)
            depreciation_account = asset.account_depreciation_id
            invoice_amount = copysign(invoice_line_id.amount_total if invoice_line_id._name == 'account.move' else invoice_line_id.price_subtotal,
                                      -initial_amount)
            invoice_account = invoice_line_id.invoice_line_ids[0].account_id if invoice_line_id._name == 'account.move' else invoice_line_id.account_id
            difference = -initial_amount - depreciated_amount - invoice_amount
            difference_account = asset.company_id.gain_account_id if difference > 0 else asset.company_id.loss_account_id
            line_datas = [(initial_amount, initial_account),
                          (depreciated_amount, depreciation_account),
                          (invoice_amount, invoice_account),
                          (difference, difference_account)]
            if partial:
                percent = partial_amount / asset.original_value
                cumulative_total = asset.original_value - asset.value_residual
                depreciated_amount = cumulative_total * percent
                difference = partial_amount - depreciated_amount + invoice_amount
                line_datas = [(partial_amount, initial_account),
                              (-depreciated_amount, depreciation_account),
                              (invoice_amount, invoice_account),
                              (-difference, difference_account)]
                asset_sequence = asset.method_number if not asset.method_period == 'day' else asset.depreciation_mo_number
                salvage_value = asset.salvage_value + partial_amount
                value_residual = asset.value_residual
            if not invoice_line_id:
                del line_datas[2]
            if company_currency == current_currency:
                vals = {
                    'amount_total': current_currency._convert(
                        asset.value_residual, company_currency,
                        asset.company_id, disposal_date),
                    'asset_id': asset.id,
                    'ref': asset.name + ': ' + (
                        _('Disposal') if not invoice_line_id else _('Sale')),
                    'asset_remaining_value': 0 if not partial else (
                            value_residual * (1 - percent)),
                    'asset_depreciated_value': max(
                        asset.depreciation_move_ids.filtered(
                            lambda x: x.state == 'posted'),
                        key=lambda x: x.date, default=self.env[
                            'account.move']).asset_depreciated_value if not partial else max(
                        asset.depreciation_move_ids.filtered(
                            lambda x: x.state == 'posted'),
                        key=lambda x: x.date, default=self.env[
                            'account.move']).asset_depreciated_value + partial_amount,
                    'date': disposal_date,
                    'journal_id': asset.journal_id.id,
                    'line_ids': [get_line(asset, amount, account) for
                                 amount, account in line_datas if account],
                    'currency_id': current_currency.id
                }
            else:
                line_records = [get_line(asset, amount, account) for
                                amount, account in line_datas if account]
                difference_current = round(
                    sum(list(map(lambda x: x[2]['debit'], line_records))) - sum(
                        list(map(lambda x: x[2]['credit'], line_records))), 2)
                print('line_records', line_records)
                print('difference_current', difference_current)
                if difference_current < 1:
                    line_records.append((0, 0, {
                        'name': asset.name,
                        'account_id': asset.account_depreciation_expense_id.id,
                        'debit': 0.0 if float_compare(difference_current, 0.0,
                                                      precision_digits=prec) > 0 else -difference_current,
                        'credit': difference_current if float_compare(
                            difference_current, 0.0,
                            precision_digits=prec) > 0 else 0.0,
                        'analytic_account_id': account_analytic_id.id if asset.asset_type == 'sale' else False,
                        'project_site_id': project_site_id.id if asset.asset_type == 'sale' else False,
                        'type_id': type_id.id if asset.asset_type == 'sale' else False,
                        'location_id': location_id.id if asset.asset_type == 'sale' else False,
                        'analytic_tag_ids': [(6, 0,
                                              analytic_tag_ids.ids)] if asset.asset_type == 'sale' else False,
                        'currency_id': company_currency != current_currency and current_currency.id or False,
                    }))
                vals = {
                    'amount_total': current_currency._convert(
                        asset.value_residual, company_currency,
                        asset.company_id, disposal_date),
                    'asset_id': asset.id,
                    'ref': asset.name + ': ' + (
                        _('Disposal') if not invoice_line_id else _('Sale')),
                    'asset_remaining_value': 0 if not partial else (
                            value_residual * (1 - percent)),
                    'asset_depreciated_value': max(
                        asset.depreciation_move_ids.filtered(
                            lambda x: x.state == 'posted'),
                        key=lambda x: x.date, default=self.env[
                            'account.move']).asset_depreciated_value if not partial else max(
                        asset.depreciation_move_ids.filtered(
                            lambda x: x.state == 'posted'),
                        key=lambda x: x.date, default=self.env[
                            'account.move']).asset_depreciated_value + partial_amount,
                    'date': disposal_date,
                    'journal_id': asset.journal_id.id,
                    'line_ids': line_records,
                    'currency_id': current_currency.id
                }
            commands.append((0, 0, vals))
            if partial:
                residual_partial = (value_residual * (1-percent))
                residual_partial = self.update_depreciation((value_residual * (1-percent)), asset,
                                         asset_sequence)
                asset.write({'depreciation_move_ids': commands,
                             'method_number': asset_sequence if not asset.method_period == 'day' else '',
                             'salvage_value': asset.book_value - residual_partial,
                             'value_residual': residual_partial,
                             'partial_disposal': True})
                # asset.compute_depreciation_board()

            else:
                asset.write({'depreciation_move_ids': commands,
                             'method_number': asset_sequence})
            tracked_fields = self.env['account.asset'].fields_get(
                ['method_number'])
            changes, tracking_value_ids = asset._message_track(
                tracked_fields, old_values)
            if changes:
                asset.message_post(body=_(
                    'Asset sold or disposed. Accounting entry awaiting for validation.'),
                    tracking_value_ids=tracking_value_ids)
            move_ids += self.env['account.move'].search(
                [('asset_id', '=', asset.id), ('state', '=', 'draft')]).ids
    return move_ids


AccountAsset._get_disposal_moves = _get_disposal_moves


class AccountAssetPartialAnalyticInherit(models.Model):
    _inherit = 'account.asset'

    def update_depreciation(self, value_residual,
                            asset, asset_sequence):
        posted_depreciation_move_ids = asset.depreciation_move_ids.filtered(
            lambda x: x.state == 'posted').sorted(
            key=lambda l: l.date)
        period = len(posted_depreciation_move_ids) - asset_sequence
        depreciation_date = posted_depreciation_move_ids[-1].date
        newline_vals_list = []
        move_vals = []
        asset_remaining_value = value_residual
        asset_depreciated_value = round(value_residual / abs(period), 2)
        amount1 = 0
        amount = asset_depreciated_value
        for asset_len in range(len(posted_depreciation_move_ids) + 1,
                               asset_sequence + 1):
            move_ref = asset.name + ' (%s/%s)' % (
                asset_len,
                asset_sequence)
            if asset_len == asset_sequence:
                amount = asset_remaining_value
                depreciation_date = depreciation_date + relativedelta(
                    months=1)
                asset_remaining_value = round(
                    (asset_remaining_value - amount), 2)
                amount1 = amount1 + amount
            else:
                amount1 = amount1 + amount
                depreciation_date = depreciation_date + relativedelta(
                    months=1)
                asset_remaining_value = round(
                    (asset_remaining_value - asset_depreciated_value), 2)
            move_vals.append(self.env[
                'account.move']._prepare_move_for_asset_depreciation({
                'amount': amount,
                'asset_id': asset,
                'move_ref': move_ref,
                'date': depreciation_date,
                'asset_remaining_value': asset_remaining_value,
                'asset_depreciated_value': amount1,
            }))
        for newline_vals in move_vals:
            # no need of amount field, as it is computed and we don't want to trigger its inverse function
            del (newline_vals['amount_total'])
            newline_vals_list.append(newline_vals)
        new_moves = self.env['account.move'].create(newline_vals_list)
        return value_residual
        # for move in new_moves:
        #     commands.append((4, move.id))
        # return self.write({'depreciation_move_ids': commands})
