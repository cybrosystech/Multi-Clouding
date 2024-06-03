from odoo import fields, _
from math import copysign
from odoo.tools import float_compare
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_round
from odoo.addons.analytic_account_types.models.account_asset import \
    AccountAsset
import logging

_logger = logging.getLogger(__name__)


def _get_disposal_moves(self, invoice_line_ids, disposal_date, partial,
                      partial_amount):
    def get_line(asset, amount, account):
        prec = asset.company_id.currency_id.decimal_places

        if asset.currency_id.id != asset.company_id.currency_id.id:
            amount_test = float_round(asset.currency_id._convert(
                            amount,  self.env.company.currency_id,
                            asset.company_id, disposal_date),precision_digits=prec)
            return (0, 0, {
                'name': asset.name,
                'account_id': account.id,
                'balance': -amount_test,
                'debit': 0.0 if float_compare(amount_test, 0.0,
                                              precision_digits=prec) > 0 else -amount_test,
                'credit': amount_test if float_compare(amount_test, 0.0,
                                                       precision_digits=prec) > 0 else 0.0,
                'analytic_account_id': asset.analytic_account_id.id,
                'currency_id': asset.currency_id.id,
                'amount_currency': -float_round(amount,precision_digits=prec),
                'project_site_id': asset.project_site_id.id,
                'analytic_distribution': analytic_distribution,
            })
        else:

            return (0, 0, {
                'name': asset.name,
                'account_id': account.id,
                'balance': -amount,
                'analytic_distribution': analytic_distribution,
                'analytic_account_id': asset.analytic_account_id.id,
                'project_site_id': asset.project_site_id.id,
                'currency_id': asset.currency_id.id,
                'amount_currency': -asset.company_id.currency_id._convert(
                    from_amount=amount,
                    to_currency=asset.currency_id,
                    company=asset.company_id,
                    date=disposal_date,
                )
            })

    if len(self.leasee_contract_ids) == 1:
        move_ids = []
        assert len(self) == len(invoice_line_ids)
        for asset, invoice_line_id in zip(self, invoice_line_ids):
            if asset.parent_id.leasee_contract_ids:
                continue
            if disposal_date < max(asset.depreciation_move_ids.filtered(
                    lambda x: not x.reversal_move_id and x.state == 'posted').mapped(
                'date') or [fields.Date.today()]):
                if invoice_line_id:
                    raise UserError(
                        'There are depreciation posted after the invoice date (%s).\nPlease revert them or change the date of the invoice.' % disposal_date)
                else:
                    raise UserError(
                        'There are depreciation posted in the future, please revert them.')
            disposal_date = self.env.context.get(
                'disposal_date') or disposal_date
            account_analytic_id = asset.analytic_account_id
            company_currency = asset.company_id.currency_id
            current_currency = asset.currency_id
            prec = company_currency.decimal_places
            if self.leasee_contract_ids:
                self.create_last_termination_move(disposal_date)
            unposted_depreciation_move_ids = asset.depreciation_move_ids.filtered(
                lambda x: x.state == 'draft')

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
            depreciation_moves = asset.depreciation_move_ids.filtered(
                lambda r: r.state == 'posted' and not (
                        r.reversal_move_id and r.reversal_move_id[
                    0].state == 'posted'))
            depreciated_amount = copysign(
                sum(depreciation_moves.mapped('amount_total')),
                -initial_amount)
            depreciation_account = asset.account_depreciation_id
            invoice_amount = copysign(invoice_line_id.price_subtotal,
                                      -initial_amount)
            invoice_account = invoice_line_id.account_id
            difference = -initial_amount - depreciated_amount - invoice_amount
            difference_account = asset.company_id.gain_account_id if difference > 0 else asset.company_id.loss_account_id
            value_residual = asset.value_residual
            if self.leasee_contract_ids:
                if asset.children_ids:
                    initial_amount += sum(
                        asset.children_ids.mapped('original_value'))
                    child_depreciation_moves = asset.children_ids.depreciation_move_ids.filtered(
                        lambda r: r.state == 'posted' and not (
                                r.reversal_move_id and
                                r.reversal_move_id[
                                    0].state == 'posted'))
                    depreciated_amount += sum(move.amount_total * (
                        -1 if move.asset_id.original_value > 0 else 1) for
                                              move in
                                              child_depreciation_moves)
                termination_residual = self.leasee_contract_ids.get_interest_amount_termination_amount(
                    disposal_date)
                move = self.leasee_contract_ids.create_interset_move(
                    self.env['leasee.installment'], disposal_date,
                    termination_residual)
                if move:
                    move.auto_post = False
                    move.action_post()
                value_residual = initial_amount + depreciated_amount
                remaining_leasee_amount = -1 * (
                    self.leasee_contract_ids.remaining_lease_liability)
                leasee_difference = -value_residual - remaining_leasee_amount
                leasee_difference_account = asset.company_id.gain_account_id if difference > 0 else asset.company_id.loss_account_id
                short_leasee_account = self.leasee_contract_ids.lease_liability_account_id
                short_lease_liability_amount = self.leasee_contract_ids.remaining_short_lease_liability
                short_remaining_leasee_amount = -1 * short_lease_liability_amount
                long_leasee_account = self.leasee_contract_ids.long_lease_liability_account_id
                remaining_long_lease_liability = -1 * self.leasee_contract_ids.remaining_long_lease_liability
                line_datas = [(initial_amount, initial_account), (
                    short_remaining_leasee_amount, short_leasee_account),
                              (remaining_long_lease_liability,
                               long_leasee_account),
                              (invoice_amount, invoice_account),
                              (
                                  leasee_difference,
                                  leasee_difference_account),
                              (depreciated_amount, depreciation_account)]
                if not invoice_line_id:
                    del line_datas[3]
            else:
                difference = -initial_amount - depreciated_amount - invoice_amount
                difference_account = asset.company_id.gain_account_id if difference > 0 else asset.company_id.loss_account_id
                line_datas = [(initial_amount, initial_account),
                              (depreciated_amount, depreciation_account),
                              (invoice_amount, invoice_account),
                              (difference, difference_account)]
                if not invoice_line_id:
                    del line_datas[2]
            vals = {
                'amount_total': current_currency._convert(value_residual,
                                                          company_currency,
                                                          asset.company_id,
                                                          disposal_date),
                'asset_id': asset.id,
                'ref': asset.name + ': ' + (
                    _('Disposal') if not invoice_line_id else _('Sale')),
                'asset_remaining_value': 0,
                'asset_depreciated_value': max(
                    asset.depreciation_move_ids.filtered(
                        lambda x: x.state == 'posted'),
                    key=lambda x: x.date,
                    default=self.env[
                        'account.move']).asset_depreciated_value,
                'date': disposal_date,
                'journal_id': asset.journal_id.id,
                'line_ids': [get_line(asset, amount, account) for
                             amount, account in line_datas if account],
                'leasee_contract_id': self.leasee_contract_ids.id,
            }
            commands.append((0, 0, vals))
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
        self.leasee_contract_ids.process_termination()
        return move_ids
    else:
        move_ids = []
        assert len(self) == len(invoice_line_ids)
        for asset, invoice_line_ids in zip(self, invoice_line_ids):
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
        # return super(AccountAsset, self)._get_disposal_moves(
        #     invoice_line_ids, disposal_date)

AccountAsset._get_disposal_moves = _get_disposal_moves
