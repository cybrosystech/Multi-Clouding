from dateutil.relativedelta import relativedelta
from odoo import models, fields, _, api
from math import copysign
from odoo.tools import float_compare
from odoo.exceptions import UserError
from odoo.addons.lease_management.models.account_asset import AccountAsset


class AccountAssetPartialInherit(models.Model):
    _inherit = 'account.asset'

    def _get_default_currency(self):
        return self.env.company.currency_id.id

    capex_type = fields.Selection(selection=[
        ('replacement_capex', 'Replacement CAPEX'),
        ('tenant_capex', 'Tenant upgrade CAPEX'),
        ('expansion_capex', 'Expansion CAPEX'),
        ('5g_capex', '5G CAPEX'),
        ('other_capex', 'Other CAPEX'), ])
    partial_disposal = fields.Boolean(copy=False)
    disposal_amount = fields.Float(default=0, readonly=True)
    asset_net = fields.Float(default=0, readonly=True)
    serial_no = fields.Char(string="Serial Number", help="Serial Number")
    currency_id = fields.Many2one('res.currency', default=_get_default_currency)

    def set_to_close(self, invoice_line_ids, partial, partial_amount, date=None
                     ):
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

    def _get_disposal_moves(self, invoice_line_ids, disposal_date, partial,
                            partial_amount):
        def get_line(asset, amount, account):
            if asset.currency_id == asset.company_id.currency_id:
                return (0, 0, {
                    'name': asset.name,
                    'account_id': account.id,
                    'debit': 0.0 if float_compare(amount, 0.0,
                                                  precision_digits=prec) > 0 else -amount,
                    'credit': amount if float_compare(amount, 0.0,
                                                      precision_digits=prec) > 0 else 0.0,
                    'analytic_distribution': analytic_distribution,
                    'currency_id': current_currency.id,
                })
            else:
                base_amount = amount
                amount = asset.currency_id._convert(round(amount, 2),
                                                    asset.company_id.currency_id,
                                                    asset.company_id,
                                                    disposal_date)
                return (0, 0, {
                    'name': asset.name,
                    'account_id': account.id,
                    'debit': 0.0 if float_compare(amount, 0.0,
                                                  precision_digits=prec) > 0 else -amount,
                    'credit': amount if float_compare(amount, 0.0,
                                                      precision_digits=prec) > 0 else 0.0,
                    'analytic_distribution': analytic_distribution,
                    'currency_id': current_currency.id,
                    'amount_currency': -base_amount,
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
                analytic_distribution = asset.analytic_distribution
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
                    lambda r: r.state in ['posted', 'cancel'] and not (
                            r.reversal_move_id and r.reversal_move_id[
                        0].state == 'posted'))
                depreciated_amount = copysign(
                    sum(depreciation_moves.mapped('amount_total')),
                    -initial_amount)
                depreciation_account = asset.account_depreciation_id
                invoice_amount = copysign(
                    invoice_line_id.amount_total if invoice_line_id._name == 'account.move' else invoice_line_id.price_subtotal,
                    -initial_amount)
                invoice_account = invoice_line_id.invoice_line_ids[
                    0].account_id if invoice_line_id._name == 'account.move' else invoice_line_id.account_id
                difference = -initial_amount - depreciated_amount - invoice_amount
                difference_account = asset.company_id.gain_account_id if difference > 0 else asset.company_id.loss_account_id
                value_residual = asset.value_residual
                if self.leasee_contract_ids:
                    # initial_amount = asset.book_value

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
                        move.auto_post = 'no'
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
                if company_currency == current_currency:
                    vals = {
                        'amount_total': current_currency._convert(
                            value_residual,
                            company_currency,
                            asset.company_id,
                            disposal_date),
                        'asset_id': asset.id,
                        'ref': asset.name + ': ' + (
                            _('Disposal') if not invoice_line_id else _(
                                'Sale')),
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
                        'currency_id': asset.currency_id.id,
                        # 'auto_post':'at_date',
                    }
                else:
                    line_records = [get_line(asset, amount, account) for
                                    amount, account in line_datas if account]
                    difference_current = round(
                        sum(list(
                            map(lambda x: x[2]['debit'], line_records))) - sum(
                            list(map(lambda x: x[2]['credit'], line_records))),
                        2)
                    if difference_current < 1 and difference_current > -1:
                        line_records.append((0, 0, {
                            'name': asset.name,
                            'account_id': self.leasee_contract_ids.terminate_account_id.id,
                            'debit': 0.0 if float_compare(difference_current,
                                                          0.0,
                                                          precision_digits=prec) > 0 else -difference_current,
                            'credit': difference_current if float_compare(
                                difference_current, 0.0,
                                precision_digits=prec) > 0 else 0.0,
                            'analytic_distribution': analytic_distribution,
                            'currency_id': current_currency.id,
                            'project_site_id': asset.project_site_id.id,
                            'type_id': asset.type_id.id,
                            'location_id': asset.location_id.id,
                        }))
                        vals = {
                            'amount_total': current_currency._convert(
                                value_residual,
                                company_currency,
                                asset.company_id,
                                disposal_date),
                            'asset_id': asset.id,
                            'ref': asset.name + ': ' + (
                                _('Disposal') if not invoice_line_id else _(
                                    'Sale')),
                            'asset_remaining_value': 0,
                            'asset_depreciated_value': max(
                                asset.depreciation_move_ids.filtered(
                                    lambda x: x.state == 'posted'),
                                key=lambda x: x.date,
                                default=self.env[
                                    'account.move']).asset_depreciated_value,
                            'date': disposal_date,
                            'journal_id': asset.journal_id.id,
                            'line_ids': line_records,
                            'leasee_contract_id': self.leasee_contract_ids.id,
                            'currency_id': asset.currency_id.id,
                            # 'auto_post':'at_date',
                        }
                commands.append((0, 0, vals))
                asset.write({'depreciation_move_ids': commands,
                             'method_number': asset_sequence})
                move_ids += self.env['account.move'].search(
                    [('asset_id', '=', asset.id), ('state', '=', 'draft')]).ids
            self.leasee_contract_ids.process_termination(disposal_date)
            return move_ids
        else:
            return super(AccountAsset, self)._get_disposal_moves(
                invoice_line_ids, disposal_date, partial, partial_amount)

    @api.depends('acquisition_date', 'original_move_line_ids', 'method_period',
                 'company_id')
    def _compute_first_depreciation_date(self):
        res = super(AccountAssetPartialInherit,
                    self)._compute_first_depreciation_date()
        for rec in self:
            if rec.prorata:
                rec.prorata_date = rec.acquisition_date
        return res

    @api.onchange('prorata_computation_type')
    def _onchange_prorata(self):
        if self.prorata_computation_type and self.acquisition_date:
            self.prorata_date = self.acquisition_date
        else:
            self.prorata_date = fields.Date.today()

    @api.depends(
        'original_value', 'salvage_value', 'already_depreciated_amount_import',
        'depreciation_move_ids.state',
        'depreciation_move_ids.amount_total',
        'depreciation_move_ids.reversal_move_id'
    )
    def _compute_value_residual(self):
        for record in self:
            posted_depreciation_moves = record.depreciation_move_ids.filtered(
                lambda mv: mv.state == 'posted')
            if record.currency_id != record.env.company.currency_id:
                posted_depreciation_move_ids = record.depreciation_move_ids.filtered(
                    lambda x: x.state == 'posted')
                record.value_residual = (
                        record.original_value
                        - record.salvage_value
                        - record.already_depreciated_amount_import
                        - sum(
                    posted_depreciation_move_ids.mapped('amount_total'))
                )
            else:
                record.value_residual = (
                        record.original_value
                        - record.salvage_value
                        - record.already_depreciated_amount_import
                        - sum(
                    posted_depreciation_moves.mapped('depreciation_value'))
                )

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
        self.env['account.move'].create(newline_vals_list)
        return value_residual
