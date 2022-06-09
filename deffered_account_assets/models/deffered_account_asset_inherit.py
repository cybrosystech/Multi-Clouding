from datetime import timedelta

from odoo import fields, models, _
from dateutil.relativedelta import relativedelta
import pandas as pd
import numpy as np
import calendar
from odoo.tools import float_compare, float_is_zero, float_round


class AccountAssetInherit(models.Model):
    _inherit = 'account.asset'

    method_period = fields.Selection(selection_add=[('day', 'Day')])
    start_date = fields.Date()
    end_date = fields.Date()

    def _compute_board_amount(self, computation_sequence, residual_amount,
                              total_amount_to_depr, max_depreciation_nb,
                              starting_sequence, depreciation_date,
                              depreciation_months, total_days, seq_fro):
        amount = 0
        if computation_sequence == max_depreciation_nb:
            # last depreciation always takes the asset residual amount
            amount = residual_amount
        else:
            if self.method in ('degressive', 'degressive_then_linear'):
                amount = residual_amount * self.method_progress_factor
            if self.method in ('linear', 'degressive_then_linear'):
                nb_depreciation = max_depreciation_nb - starting_sequence
                if self.prorata:
                    nb_depreciation -= 1
                linear_amount = min(total_amount_to_depr / nb_depreciation,
                                    residual_amount)
                if self.method_period == 'day':
                    if starting_sequence == seq_fro:
                        days = depreciation_months[
                                   0].day - self.start_date.day + 1
                        linear_amount = (
                                                    total_amount_to_depr * days) / total_days
                    elif seq_fro == len(depreciation_months):
                        linear_amount = (total_amount_to_depr *
                                         depreciation_months[
                                             seq_fro].day) / total_days
                    else:
                        linear_amount = (total_amount_to_depr *
                                         depreciation_months[
                                             seq_fro].day) / total_days
                if self.method == 'degressive_then_linear':
                    amount = max(linear_amount, amount)
                else:
                    amount = linear_amount

        return amount

    def compute_depreciation_board(self):
        self.ensure_one()
        depreciation_pymonths = ''
        total_days = ''
        amount_change_ids = self.depreciation_move_ids.filtered(
            lambda x: x.asset_value_change and not x.reversal_move_id).sorted(
            key=lambda l: l.date)
        posted_depreciation_move_ids = self.depreciation_move_ids.filtered(
            lambda
                x: x.state == 'posted' and not x.asset_value_change and not x.reversal_move_id).sorted(
            key=lambda l: l.date)
        already_depreciated_amount = sum(
            [m.amount_total for m in posted_depreciation_move_ids])
        depreciation_number = self.method_number
        if self.prorata:
            depreciation_number += 1
        starting_sequence = 0
        amount_to_depreciate = self.value_residual + sum(
            [m.amount_total for m in amount_change_ids])
        depreciation_date = self.first_depreciation_date
        if self.method_period == 'day':
            df = pd.DataFrame({'Date1': np.array([self.end_date]),
                               'Date2': np.array([self.start_date])})
            df['nb_months'] = ((df.Date1 - df.Date2) / np.timedelta64(1,
                                                                      'M')) + 1
            df['nb_months'] = df['nb_months'].astype(int)
            df['nb_days'] = ((df.Date1 - df.Date2) / np.timedelta64(1,
                                                                    'D')) + 1
            df['nb_days'] = df['nb_days'].astype(int)
            depreciation_number = df.loc[0, 'nb_months']
            total_days = df.loc[0, 'nb_days']
            depreciation_months = pd.date_range(self.start_date, self.end_date,
                                                freq='M')
            depreciation_pymonths = depreciation_months.to_pydatetime()
            depreciation_date = self.start_date
        # if we already have some previous validated entries, starting date is last entry + method period
        if posted_depreciation_move_ids and posted_depreciation_move_ids[
            -1].date:
            last_depreciation_date = fields.Date.from_string(
                posted_depreciation_move_ids[-1].date)
            if last_depreciation_date > depreciation_date:  # in case we unpause the asset
                depreciation_date = last_depreciation_date + relativedelta(
                    months=+int(
                        self.method_period if not self.method_period == 'day' else depreciation_number))
        commands = [(2, line_id.id, False) for line_id in
                    self.depreciation_move_ids.filtered(
                        lambda x: x.state == 'draft')]
        newlines = self._recompute_board(depreciation_number, starting_sequence,
                                         amount_to_depreciate,
                                         depreciation_date,
                                         already_depreciated_amount,
                                         amount_change_ids,
                                         depreciation_pymonths, total_days)
        newline_vals_list = []
        for newline_vals in newlines:
            # no need of amount field, as it is computed and we don't want to trigger its inverse function
            del (newline_vals['amount_total'])
            newline_vals_list.append(newline_vals)
        new_moves = self.env['account.move'].create(newline_vals_list)
        for move in new_moves:
            commands.append((4, move.id))
        return self.write({'depreciation_move_ids': commands})

    def _recompute_board(self, depreciation_number, starting_sequence,
                         amount_to_depreciate, depreciation_date,
                         already_depreciated_amount, amount_change_ids,
                         depreciation_months, total_days):
        self.ensure_one()
        residual_amount = amount_to_depreciate
        # Remove old unposted depreciation lines. We cannot use unlink() with One2many field
        move_vals = []
        prorata = self.prorata and not self.env.context.get("ignore_prorata")
        if amount_to_depreciate != 0.0:
            seq_fro = 0
            for asset_sequence in range(starting_sequence + 1,
                                        depreciation_number + 1):
                while amount_change_ids and amount_change_ids[
                    0].date <= depreciation_date:
                    if not amount_change_ids[0].reversal_move_id:
                        residual_amount -= amount_change_ids[0].amount_total
                        amount_to_depreciate -= amount_change_ids[
                            0].amount_total
                        already_depreciated_amount += amount_change_ids[
                            0].amount_total
                    amount_change_ids[0].write({
                        'asset_remaining_value': float_round(residual_amount,
                                                             precision_rounding=self.currency_id.rounding),
                        'asset_depreciated_value': amount_to_depreciate - residual_amount + already_depreciated_amount,
                    })
                    amount_change_ids -= amount_change_ids[0]
                amount = self._compute_board_amount(asset_sequence,
                                                    residual_amount,
                                                    amount_to_depreciate,
                                                    depreciation_number,
                                                    starting_sequence,
                                                    depreciation_date,
                                                    depreciation_months,
                                                    total_days, seq_fro)
                prorata_factor = 1
                move_ref = self.name + ' (%s/%s)' % (
                    prorata and asset_sequence - 1 or asset_sequence,
                    self.method_number)
                if prorata and asset_sequence == 1:
                    move_ref = self.name + ' ' + _('(prorata entry)')
                    first_date = self.prorata_date
                    if int(self.method_period) % 12 != 0:
                        month_days = \
                            calendar.monthrange(first_date.year,
                                                first_date.month)[
                                1]
                        days = month_days - first_date.day + 1
                        prorata_factor = days / month_days
                    else:
                        total_days = (depreciation_date.year % 4) and 365 or 366
                        days = (self.company_id.compute_fiscalyear_dates(
                            first_date)['date_to'] - first_date).days + 1
                        prorata_factor = days / total_days
                amount = self.currency_id.round(amount * prorata_factor)
                if float_is_zero(amount,
                                 precision_rounding=self.currency_id.rounding):
                    continue
                residual_amount -= amount

                move_vals.append(self.env[
                    'account.move']._prepare_move_for_asset_depreciation({
                    'amount': amount,
                    'asset_id': self,
                    'move_ref': move_ref,
                    'date': depreciation_date,
                    'asset_remaining_value': float_round(residual_amount,
                                                         precision_rounding=self.currency_id.rounding),
                    'asset_depreciated_value': amount_to_depreciate - residual_amount + already_depreciated_amount,
                }))
                if depreciation_number:
                    max_day_in_month = \
                        calendar.monthrange(depreciation_date.year,
                                            depreciation_date.month)[1]
                    depreciation_date = depreciation_date + timedelta(days=max_day_in_month)
                else:
                    depreciation_date = depreciation_date + relativedelta(
                        months=+int(
                            self.method_period if not self.method_period == 'day' else depreciation_number))
                    # datetime doesn't take into account that the number of days is not the same for each month
                    if int(self.method_period) % 12 != 0:
                        max_day_in_month = \
                            calendar.monthrange(depreciation_date.year,
                                                depreciation_date.month)[1]
                        depreciation_date = depreciation_date.replace(
                            day=max_day_in_month)
                seq_fro = seq_fro + 1
        return move_vals
