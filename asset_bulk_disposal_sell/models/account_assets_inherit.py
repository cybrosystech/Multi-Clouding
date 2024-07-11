from odoo import models, fields, api, _
from math import copysign
from odoo.tools import float_compare
from odoo.tools.misc import formatLang
from odoo.exceptions import UserError


class AccountAssetBulkSaleDisposal(models.Model):
    _inherit = 'account.asset'

    @api.constrains('depreciation_move_ids')
    def _check_depreciations(self):
        for asset in self:
            if (
                    asset.state == 'open'
                    and asset.depreciation_move_ids
                    and not asset.currency_id.is_zero(
                asset.depreciation_move_ids.sorted(lambda x: (x.date, x.id))[
                    -1].asset_remaining_value
            )
            ):
                raise UserError(
                    _("The remaining value on the last depreciation entry must"
                      " be 0 for the asset %s", asset.name))

    def asset_bulk_sale_dispose(self):
        abc = []
        for rec in self:
            if rec.leasee_contract_ids:
                asset_bulk = self.env['asset.sell.disposal.lines'].create({
                    'asset_id': rec.id,
                    'from_leasee_contract': True,
                    'action': 'dispose',
                })
            else:
                asset_bulk = self.env['asset.sell.disposal.lines'].create({
                    'asset_id': rec.id,
                    'action': 'dispose',
                })
            abc.append(asset_bulk.id)
        dd = self.env['asset.bulk.wizard'].create({
            'asset_sell_disposal_ids': [(6,0,abc)]
        })
        # view = self.env.ref('asset_bulk_disposal_sell.asset_sell_bulk_form')
        return {
            'name': 'Asset Bulk sale',
            'view_mode': 'form',
            'res_model': 'asset.bulk.wizard',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'res_id': dd.id,
        }

    def asset_bulk_pause_depreciation(self):
        dd = self.env['asset.bulk.pause.wizard'].create({
            'asset_ids': self.ids,
        })
        return {
            'name': 'Asset Bulk Pause Depreciation',
            'view_mode': 'form',
            'res_model': 'asset.bulk.pause.wizard',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'res_id': dd.id,
        }

    def set_to_close_bulk(self, invoice_line_ids, partial, partial_amount, date=None):
        self.ensure_one()
        disposal_date = date or fields.Date.today()
        if invoice_line_ids and self.children_ids.filtered(
                lambda a: a.state in ('draft', 'open') or a.value_residual > 0):
            raise UserError(
                _("You cannot automate the journal entry for an asset that has "
                  "a running gross increase. Please use 'Dispose' on the "
                  "increase(s)."))
        full_asset = self + self.children_ids

        move_ids = full_asset._get_disposal_moves(
            [invoice_line_ids] * len(full_asset), disposal_date, partial,
            partial_amount)
        if not partial:
            full_asset.write({'state': 'close'})
        if move_ids:
            name = _('Disposal Move')
            view_mode = 'form'
            return {
                'name': name,
                'view_mode': view_mode,
                'res_model': 'account.move',
                'type': 'ir.actions.act_window',
                'target': 'current',
                'res_id': move_ids[0],
                'domain': [('id', 'in', move_ids)]
            }
        # self.ensure_one()
        # disposal_date = date or fields.Date.today()
        # if invoice_line_ids and self.children_ids.filtered(lambda a: a.state in ('draft', 'open') or a.value_residual > 0):
        #     raise UserError(_("You cannot automate the journal entry for an asset that has a running gross increase. Please use 'Dispose' on the increase(s)."))
        # full_asset = self + self.children_ids
        # full_asset._get_disposal_moves_bulk([invoice_line_ids] * len(full_asset), disposal_date, partial, partial_amount)
        # if not partial:
        #     full_asset.write({'state': 'close'})
        # # if move_ids:
        # #     return self._return_disposal_view(move_ids)

    def _get_disposal_moves_bulk(self, invoice_line_ids, disposal_date, partial, partial_amount):
        def get_line(asset, amount, account):
            return (0, 0, {
                'name': asset.name,
                'account_id': account.id,
                'debit': 0.0 if float_compare(amount, 0.0,
                                              precision_digits=prec) > 0 else -amount,
                'credit': amount if float_compare(amount, 0.0,
                                                  precision_digits=prec) > 0 else 0.0,
                # 'analytic_account_id': account_analytic_id.id if asset.leasee_contract_ids else False,
                # 'analytic_tag_ids': [(6, 0,
                #                       analytic_tag_ids.ids)] if asset.asset_type == 'sale' else False,
                'currency_id': current_currency.id,
                # 'amount_currency': asset.value_residual if float_compare(amount, 0.0,
                #                               precision_digits=prec) > 0 else -(asset.value_residual),
                # 'project_site_id': asset.project_site_id.id,
                # 'type_id': asset.type_id.id,
                # 'location_id': asset.location_id.id,
                'analytic_distribution': asset.analytic_distribution,
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
                # account_analytic_id = asset.account_analytic_id
                # analytic_tag_ids = asset.analytic_tag_ids
                company_currency = asset.company_id.currency_id
                current_currency = asset.currency_id
                prec = company_currency.decimal_places
                if self.leasee_contract_ids:
                    self.create_last_termination_move(disposal_date)
                unposted_depreciation_move_ids = asset.depreciation_move_ids.filtered(
                    lambda x: x.state == 'draft')

                old_values = {
                   asset.id : asset.method_number,
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
                    lambda r: r.state in ['posted', 'cancel'] and not (
                            r.reversal_move_id and r.reversal_move_id[
                        0].state == 'posted'))
                depreciated_amount = copysign(
                    sum(depreciation_moves.mapped('amount_total')),
                    -initial_amount)
                depreciation_account = asset.account_depreciation_id
                invoice_amount = copysign(invoice_line_id.amount_total if invoice_line_id._name == 'account.move' else invoice_line_id.price_subtotal,
                                      -initial_amount)
                invoice_account = invoice_line_id.invoice_line_ids[0].account_id if invoice_line_id._name == 'account.move' else invoice_line_id.account_id
                difference = -initial_amount - depreciated_amount - invoice_amount
                difference_account = asset.company_id.gain_account_id if difference > 0 else asset.company_id.loss_account_id
                value_residual = asset.value_residual
                if self.leasee_contract_ids:
                    # initial_amount = asset.book_value

                    if asset.children_ids:
                        initial_amount += sum(
                            asset.children_ids.mapped('original_value'))
                        # value_residual += sum(asset.children_ids.mapped('value_residual'))
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
                    # leasee_difference = -asset.book_value - remaining_leasee_amount
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
            # return move_ids
        else:
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
                # account_analytic_id = asset.account_analytic_id
                # project_site_id = asset.project_site_id
                # type_id = asset.type_id
                # location_id = asset.location_id
                # analytic_tag_ids = asset.analytic_tag_ids
                analytic_distribution = asset.analytic_distribution
                company_currency = asset.company_id.currency_id
                current_currency = asset.currency_id
                prec = company_currency.decimal_places
                unposted_depreciation_move_ids = asset.depreciation_move_ids.filtered(
                    lambda x: x.state == 'draft')
                if unposted_depreciation_move_ids:
                    old_values = {
                        asset.id:{'method_number': asset.method_number},
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
                                      (-depreciated_amount,
                                       depreciation_account),
                                      (invoice_amount, invoice_account),
                                      (-difference, difference_account)]
                        asset_sequence = asset.method_number if not asset.method_period == 'day' else asset.depreciation_mo_number
                        salvage_value = asset.salvage_value + partial_amount
                        value_residual = asset.value_residual
                    if not invoice_line_id:
                        del line_datas[2]

                    vals = {
                        'amount_total': current_currency._convert(
                            asset.value_residual, company_currency,
                            asset.company_id, disposal_date),
                        'asset_id': asset.id,
                        'ref': asset.name + ': ' + (
                            _('Disposal') if not invoice_line_id else _(
                                'Sale')),
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
                                     'value_residual': residual_partial})
                        # asset.compute_depreciation_board()

                    else:
                        asset.write({'depreciation_move_ids': commands,
                                     'method_number': asset_sequence})
                    tracked_fields = self.env['account.asset'].fields_get(
                        ['method_number'])
                    changes = asset._message_track(
                        tracked_fields, old_values)
                    if changes:
                        asset.message_post(body=_(
                            'Asset sold or disposed. Accounting entry awaiting for validation.'),
                            tracking_value_ids=changes[asset.id][1])
                    move_ids += self.env['account.move'].search(
                        [('asset_id', '=', asset.id),
                         ('state', '=', 'draft')]).ids
            # return move_ids


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _log_depreciation_asset(self):
        for move in self.filtered(lambda m: m.asset_id):
            asset = move.asset_id
            msg = _('Depreciation entry %s posted (%s)', move.name,
                    formatLang(self.env, move.depreciation_value,
                               currency_obj=move.company_id.currency_id))
            if not self.env.context.get('is_asset_bulk_disposal'):
                asset.message_post(body=msg)
            else:
                asset.message_post(body=msg,
                                   author_id=self.env.ref('base.partner_root').id)

