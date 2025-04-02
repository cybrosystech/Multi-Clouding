from odoo import _
from math import copysign
from odoo.tools import float_compare, float_round
from odoo.addons.analytic_account_types.models.account_asset import \
    AccountAsset
import logging

_logger = logging.getLogger(__name__)


def _get_disposal_moves(self, invoice_line_ids, disposal_date, partial,
                        partial_amount):
    def get_line(asset, amount, account):
        return (0, 0, {
            'name': asset.name,
            'account_id': account.id,
            'balance': -amount,
            'analytic_distribution': asset.analytic_distribution,
            'analytic_account_id': asset.analytic_account_id.id,
            'business_unit_id': asset.business_unit_id.id,
            'project_site_id': asset.project_site_id.id,
            'currency_id': asset.currency_id.id,
            'amount_currency': -asset.company_id.currency_id._convert(
                from_amount=amount,
                to_currency=asset.currency_id,
                company=asset.company_id,
                date=disposal_date,
            )
        })

    if len(self.leasee_contract_ids) >= 1:
        move_ids = []
        lease = self.env['leasee.contract'].search(
            [('id', 'in', self.leasee_contract_ids.ids)],
            order="id DESC", limit=1)
        ass = self.env['account.asset'].search([('id', 'in', self.ids)],
                                               order="id desc", limit=1)
        assert len(self) == len(invoice_line_ids)
        for asset, invoice_line_ids in zip(ass, invoice_line_ids):
            if lease:
                asset.create_last_termination_move(disposal_date)
            asset._create_move_before_date(disposal_date)

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
            if lease:
                termination_residual = lease.get_interest_amount_termination_amount(
                    disposal_date)
                move = lease.create_interset_move(
                    self.env['leasee.installment'], disposal_date,
                    termination_residual)
                if move:
                    move.auto_post = 'no'
                    move.action_post()
                difference = -initial_amount - depreciated_amount - invoice_amount
                difference_account = asset.company_id.gain_account_id if difference > 0 else asset.company_id.loss_account_id

                short_leasee_account = lease.lease_liability_account_id
                short_lease_liability_amount = lease.remaining_short_lease_liability
                short_remaining_leasee_amount = -1 * short_lease_liability_amount
                long_leasee_account = lease.long_lease_liability_account_id
                remaining_long_lease_liability = -1 * lease.remaining_long_lease_liability
                leasee_difference = initial_amount - abs(
                    depreciated_amount) - abs(
                    remaining_long_lease_liability) - abs(
                    short_remaining_leasee_amount)
                line_datas = [(initial_amount, initial_account),
                              (depreciated_amount,
                               depreciation_account), (
                                  short_remaining_leasee_amount,
                                  short_leasee_account),
                              (remaining_long_lease_liability,
                               long_leasee_account)] + list_accounts + [
                                 (
                                (-1 * leasee_difference),
                                     difference_account),
                             ]

            else:
                difference = -initial_amount - depreciated_amount - invoice_amount
                difference_account = asset.company_id.gain_account_id if difference > 0 else asset.company_id.loss_account_id
                line_datas = [(initial_amount, initial_account), (
                    depreciated_amount,
                    depreciation_account)] + list_accounts + [
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
            lease.process_termination(disposal_date)
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
            if asset.currency_id.id != asset.company_id.currency_id.id:
                initial_amount = float_round(asset.currency_id._convert(
                    initial_amount, self.env.company.currency_id,
                    asset.company_id, disposal_date),
                    precision_digits=asset.currency_id.decimal_places)

                depreciated_amount = float_round(asset.currency_id._convert(
                    depreciated_amount, self.env.company.currency_id,
                    asset.company_id, disposal_date),
                    precision_digits=asset.currency_id.decimal_places)

                invoice_amount = float_round(asset.currency_id._convert(
                    invoice_amount, self.env.company.currency_id,
                    asset.company_id, disposal_date),
                    precision_digits=asset.currency_id.decimal_places)

            difference = -initial_amount - depreciated_amount - invoice_amount
            difference_account = asset.company_id.gain_account_id if difference > 0 else asset.company_id.loss_account_id
            line_datas = [(initial_amount, initial_account), (
                depreciated_amount, depreciation_account)] + [
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

AccountAsset._get_disposal_moves = _get_disposal_moves
