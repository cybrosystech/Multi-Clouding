from odoo import fields, _
from math import copysign
from odoo.tools import float_compare
from odoo.exceptions import UserError
from odoo.addons.analytic_account_types.models.account_asset import \
    AccountAsset
import logging

_logger = logging.getLogger(__name__)


def _get_disposal_moves(self, invoice_line_ids, disposal_date, partial,
                        partial_amount):
    def get_line(asset, amount, account):
        if company_currency == current_currency:
            amount = round(amount, 2)
            return (0, 0, {
                'name': asset.name,
                'account_id': account.id,
                'debit': 0.0 if float_compare(amount, 0.0,
                                              precision_digits=prec) > 0 else -amount,
                'credit': amount if float_compare(amount, 0.0,
                                                  precision_digits=prec) > 0 else 0.0,
                'analytic_distribution': analytic_distribution,
                'currency_id': current_currency.id,
                'amount_currency': company_currency != current_currency and - 1.0 * asset.value_residual or 0.0,
            })
        else:
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
                'analytic_distribution': analytic_distribution,
                'currency_id': current_currency.id,
                'amount_currency': -amount,
            })

    move_ids = []
    assert len(self) == len(invoice_line_ids)
    for asset, invoice_line_id in zip(self, invoice_line_ids):
        if disposal_date < max(asset.depreciation_move_ids.filtered(
                lambda x: not x.reversal_move_id and x.state == 'posted').mapped(
            'date') or [fields.Date.today()]):
            if invoice_line_id:
                raise UserError(
                    'There are depreciation posted after the invoice date'
                    ' (%s).\nPlease revert them or change the date of the'
                    ' invoice.' % disposal_date)
            else:
                raise UserError(
                    'There are depreciation posted in the future, please revert'
                    ' them.')

        analytic_distribution = asset.analytic_distribution
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
                    lambda r: r.state in ['posted', 'cancel']).mapped(
                    'amount_total')),
                -initial_amount)
            depreciation_account = asset.account_depreciation_id
            invoice_amount = copysign(
                invoice_line_id.amount_total if invoice_line_id._name == 'account.move' else invoice_line_id.price_subtotal,
                -initial_amount)
            invoice_account = invoice_line_id.invoice_line_ids[
                0].account_id if invoice_line_id._name == 'account.move' else invoice_line_id.account_id
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
                asset.disposal_amount = asset.disposal_amount + partial_amount
                asset.asset_net = asset.asset_net + (
                        asset.original_value - partial_amount)
            if not invoice_line_id:
                del line_datas[2]
            if company_currency == current_currency:
                line_records = [get_line(asset, amount, account) for
                                amount, account in line_datas if account]
                difference_current = round(
                    sum(list(map(lambda x: x[2]['debit'], line_records))) - sum(
                        list(map(lambda x: x[2]['credit'], line_records))), 2)
                if difference_current < 1:
                    line_records.append((0, 0, {
                        'name': asset.name,
                        'account_id': asset.account_depreciation_expense_id.id,
                        'debit': 0.0 if float_compare(difference_current, 0.0,
                                                      precision_digits=prec) > 0 else -difference_current,
                        'credit': difference_current if float_compare(
                            difference_current, 0.0,
                            precision_digits=prec) > 0 else 0.0,
                        'analytic_distribution': analytic_distribution,
                        'currency_id': current_currency.id,
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
            else:
                line_records = [get_line(asset, amount, account) for
                                amount, account in line_datas if account]
                difference_current = round(
                    sum(list(map(lambda x: x[2]['debit'], line_records))) - sum(
                        list(map(lambda x: x[2]['credit'], line_records))), 2)
                if difference_current < 1:
                    line_records.append((0, 0, {
                        'name': asset.name,
                        'account_id': asset.account_depreciation_expense_id.id,
                        'debit': 0.0 if float_compare(difference_current, 0.0,
                                                      precision_digits=prec) > 0 else -difference_current,
                        'credit': difference_current if float_compare(
                            difference_current, 0.0,
                            precision_digits=prec) > 0 else 0.0,
                        'analytic_ditribution': analytic_distribution,
                        'currency_id': current_currency.id,
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
                residual_partial = (value_residual * (1 - percent))
                residual_partial = self.update_depreciation(
                    (value_residual * (1 - percent)), asset,
                    asset_sequence)
                asset.write({'depreciation_move_ids': commands,
                             'method_number': asset_sequence if not asset.method_period == 'day' else '',
                             'salvage_value': asset.book_value - residual_partial,
                             'value_residual': residual_partial,
                             'partial_disposal': True})

            else:
                asset.write({'depreciation_move_ids': commands,
                             'method_number': asset_sequence})
            tracked_fields = self.env['account.asset'].fields_get(
                ['method_number'])
            changes, tracking_value_ids = asset._message_track(
                tracked_fields, old_values)
            if changes:
                asset.message_post(body=_(
                    'Asset sold or disposed. Accounting entry awaiting for'
                    ' validation.'),
                    tracking_value_ids=tracking_value_ids)
            move_ids += self.env['account.move'].search(
                [('asset_id', '=', asset.id), ('state', '=', 'draft')]).ids
    return move_ids


AccountAsset._get_disposal_moves = _get_disposal_moves
