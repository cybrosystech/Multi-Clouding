from dateutil.relativedelta import relativedelta
from odoo import models, fields, _, api
from math import copysign
from odoo.tools import float_compare
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_is_zero, formatLang, end_of, \
    float_round
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
        ('other_capex', 'Other CAPEX'),
        ('transferred_capex', 'Transferred CAPEX')])
    partial_disposal = fields.Boolean(copy=False)
    disposal_amount = fields.Float(default=0, readonly=True)
    asset_net = fields.Float(default=0, readonly=True)
    serial_no = fields.Char(string="Serial Number", help="Serial Number")
    currency_id = fields.Many2one(related='', store=True, readonly=False,
                                  default=_get_default_currency)

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

    def _get_disposal_moves(self, invoice_lines_list, disposal_date, partial,
                            partial_amount):
        """Create the move for the disposal of an asset.

        :param invoice_lines_list: list of recordset of `account.move.line`
            Each element of the list corresponds to one record of `self`
            These lines are used to generate the disposal move
        :param disposal_date: the date of the disposal
        """

        def get_line(asset, amount, account):
            if asset.currency_id.id != asset.company_id.currency_id.id:
                return (0, 0, {
                    'name': asset.name,
                    'account_id': account.id,
                    'balance': -asset.currency_id._convert(
                        from_amount=amount,
                        to_currency=asset.company_id.currency_id,
                        company=asset.company_id,
                        date=disposal_date,
                    ),
                    'analytic_distribution': asset.analytic_distribution,
                    'analytic_account_id': asset.analytic_account_id.id,
                    'project_site_id': asset.project_site_id.id,
                    'currency_id': asset.currency_id.id,
                    'amount_currency': -amount,
                })
            else:

                return (0, 0, {
                    'name': asset.name,
                    'account_id': account.id,
                    'balance': -amount,
                    'analytic_distribution': asset.analytic_distribution,
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

        if self.leasee_contract_ids:
            if len(self.leasee_contract_ids.ids) ==1:
                lease = self.env['leasee.contract'].search(
                    [('id', 'in', self.leasee_contract_ids.ids)],
                    order="id ASC", limit=1)
                ass = self.env['account.asset'].search([('id', 'in', self.ids)],
                                                       order="id ASC", limit=1)
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
                            invoice_line.balance,
                            -initial_amount) + dict_invoice.get(
                            invoice_line.account_id, 0)
                        invoice_amount += copysign(invoice_line.balance,
                                                   -initial_amount)
                    list_accounts = [(amount, account) for account, amount in
                                     dict_invoice.items()]

                    if lease and ass.id == asset.id:
                        if disposal_date >= lease.commencement_date:
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
                        line_datas = [(round(initial_amount, 3), initial_account),
                                      (round(depreciated_amount, 3),
                                       depreciation_account), (
                                          round(short_remaining_leasee_amount, 3),
                                          short_leasee_account),
                                      (round(remaining_long_lease_liability, 3),
                                       long_leasee_account)] + list_accounts + [
                                         (
                                             round(-1 * leasee_difference, 3),
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
                    if lease:
                        lease.process_termination(disposal_date)
                return move_ids
            else:
                leases = self.leasee_contract_ids.ids
                move_ids = []
                for ls in leases:
                    index= leases.index(ls)
                    lease = self.env['leasee.contract'].browse(ls)
                    assets =self.ids
                    ass = self.env['account.asset'].search([('id', '=', assets[index])],
                                                           order="id ASC", limit=1)
                    for asset, invoice_line_ids in zip(ass,
                                                       invoice_lines_list):
                        asset._create_move_before_date(disposal_date)

                        analytic_distribution = asset.analytic_distribution

                        dict_invoice = {}
                        invoice_amount = 0

                        initial_amount = asset.original_value
                        if disposal_date < asset.acquisition_date:
                            initial_amount = 0

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
                                invoice_line.balance,
                                -initial_amount) + dict_invoice.get(
                                invoice_line.account_id, 0)
                            invoice_amount += copysign(invoice_line.balance,
                                                       -initial_amount)
                        list_accounts = [(amount, account) for account, amount
                                         in
                                         dict_invoice.items()]

                        if lease:
                            if disposal_date >= lease.commencement_date:
                                termination_residual = lease.get_interest_amount_termination_amount(
                                    disposal_date)
                                if termination_residual!=0:
                                    move = lease.create_interset_move(
                                        self.env['leasee.installment'], disposal_date,
                                        termination_residual)
                                    if move:
                                        move.auto_post = 'no'
                                        move.action_post()
                            difference = -initial_amount - depreciated_amount - invoice_amount
                            # difference_account = asset.company_id.gain_account_id if difference > 0 else asset.company_id.loss_account_id
                            short_leasee_account = lease.lease_liability_account_id
                            short_lease_liability_amount = lease.remaining_short_lease_liability
                            short_remaining_leasee_amount = -1 * short_lease_liability_amount
                            long_leasee_account = lease.long_lease_liability_account_id
                            remaining_long_lease_liability = -1 * lease.remaining_long_lease_liability
                            leasee_difference = initial_amount - abs(
                                depreciated_amount) - abs(
                                remaining_long_lease_liability) - abs(
                                short_remaining_leasee_amount)
                            difference_account = asset.company_id.gain_account_id if difference > 0 else asset.company_id.loss_account_id
                            line_datas = [(round(initial_amount, 3),
                                           initial_account),
                                          (round(depreciated_amount, 3),
                                           depreciation_account), (
                                              round(
                                                  short_remaining_leasee_amount,
                                                  3),
                                              short_leasee_account),
                                          (round(remaining_long_lease_liability,
                                                 3),
                                           long_leasee_account)] + list_accounts + [
                                             (
                                                 round(-1 * leasee_difference,
                                                       3),
                                                 difference_account),
                                         ]
                        else:
                            difference = -initial_amount - depreciated_amount - invoice_amount
                            difference_account = asset.company_id.gain_account_id if difference > 0 else asset.company_id.loss_account_id
                            line_datas = [(initial_amount, initial_account), (
                                depreciated_amount,
                                depreciation_account)] + list_accounts + [
                                             (difference, difference_account)]
                        if initial_amount !=0:
                            vals = {
                                'asset_id': asset.id,
                                'ref': asset.name + ': ' + (
                                    _('Disposal') if not invoice_line_ids else _(
                                        'Sale')),
                                'asset_depreciation_beginning_date': disposal_date,
                                'date': disposal_date,
                                'journal_id': asset.journal_id.id,
                                'move_type': 'entry',
                                'line_ids': [get_line(asset, amount, account) for
                                             amount, account in line_datas if
                                             account],
                            }
                            asset.write({'depreciation_move_ids': [(0, 0, vals)]})
                            move_ids += self.env['account.move'].search(
                                [('asset_id', '=', asset.id),
                                 ('state', '=', 'draft')]).ids
                    if lease:
                        lease.process_termination(disposal_date)
                return move_ids
        else:
            return super(AccountAsset, self)._get_disposal_moves(
                invoice_lines_list, disposal_date, partial, partial_amount)

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
