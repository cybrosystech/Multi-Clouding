from odoo import fields, models, _, api
from dateutil.relativedelta import relativedelta
from odoo.tools import float_compare, float_is_zero, float_round

DAYS_PER_MONTH = 30
DAYS_PER_YEAR = DAYS_PER_MONTH * 12


class AccountAssetInherit(models.Model):
    _inherit = 'account.asset'

    method_period = fields.Selection(selection_add=[('day', 'Day')])
    start_date = fields.Date()
    end_date = fields.Date()
    accounting_date = fields.Date(string='Accounting Date')
    cumulative_expense = fields.Monetary(string='Cumulative Expense',
                                         compute='_compute_cumulative_expense')

    @api.onchange('start_date')
    def onchange_start_date(self):
        Date = self.start_date
        self.acquisition_date = Date
        self.prorata_date = Date
    def _compute_board_amount(self, residual_amount, period_start_date,
                              period_end_date, days_already_depreciated,
                              days_left_to_depreciated, residual_declining):
        if self.asset_lifetime_days == 0:
            return 0, 0
        number_days = self._get_delta_days(period_start_date, period_end_date)
        total_days = number_days + days_already_depreciated

        if self.method in ('degressive', 'degressive_then_linear'):
            # Declining by year but divided per month
            # We compute the amount of the period based on ratio how many days there are in the period
            # e.g: monthly period = 30 days --> (30/360) * 12000 * 0.4
            # => For each month in the year we will decline the same amount.
            amount = (
                             number_days / DAYS_PER_YEAR) * residual_declining * self.method_progress_factor
        else:
            computed_linear_amount = (
                                             self.total_depreciable_value * total_days / self.asset_lifetime_days) + residual_amount - self.total_depreciable_value
            if float_compare(residual_amount, 0,
                             precision_rounding=self.currency_id.rounding) >= 0:
                linear_amount = min(computed_linear_amount, residual_amount)
                amount = max(linear_amount, 0)
            else:
                linear_amount = max(computed_linear_amount, residual_amount)
                amount = min(linear_amount, 0)

        if self.method == 'degressive_then_linear' and days_left_to_depreciated != 0:
            linear_amount = number_days * self.total_depreciable_value / self.asset_lifetime_days
            amount = max(linear_amount, amount, key=abs)

        if abs(residual_amount) < abs(
                amount) or total_days >= self.asset_lifetime_days:
            # If the residual amount is less than the computed amount, we keep the residual amount
            # If total_days is greater or equals to asset lifetime days, it should mean that
            # the asset will finish in this period and the value for this period is equals to the residual amount.
            amount = residual_amount
        return number_days, self.currency_id.round(amount)

    def _recompute_board(self,start_depreciation_date=False):
        self.ensure_one()
        # All depreciation moves that are posted
        posted_depreciation_move_ids = self.depreciation_move_ids.filtered(
            lambda mv: mv.state == 'posted' and not mv.asset_value_change
        ).sorted(key=lambda mv: (mv.date, mv.id))

        imported_amount = self.already_depreciated_amount_import
        residual_amount = self.value_residual
        if not posted_depreciation_move_ids:
            residual_amount += imported_amount
        residual_declining = residual_amount

        # Days already depreciated
        days_already_depreciated = sum(
            posted_depreciation_move_ids.mapped('asset_number_days'))
        days_left_to_depreciated = self.asset_lifetime_days - days_already_depreciated
        days_already_added = sum(
            [(mv.date - mv.asset_depreciation_beginning_date).days + 1 for mv in
             posted_depreciation_move_ids])

        start_depreciation_date = self.paused_prorata_date + relativedelta(
            days=days_already_added)
        if self.method_period == 'day':
            number_of_days = self.end_date - self.start_date
            final_depreciation_date = self.paused_prorata_date + relativedelta(
                days=number_of_days.days)
            final_depreciation_date = self._get_end_period_date(
                final_depreciation_date)

        else:
            final_depreciation_date = self.paused_prorata_date + relativedelta(
                months=int(self.method_period) * self.method_number, days=-1)
            final_depreciation_date = self._get_end_period_date(
                final_depreciation_date)

        depreciation_move_values = []
        if not float_is_zero(self.value_residual,
                             precision_rounding=self.currency_id.rounding):
            while days_already_depreciated < self.asset_lifetime_days:
                period_end_depreciation_date = self._get_end_period_date(
                    start_depreciation_date)
                period_end_fiscalyear_date = self.company_id.compute_fiscalyear_dates(
                    period_end_depreciation_date).get('date_to')

                days, amount = self._compute_board_amount(residual_amount,
                                                          start_depreciation_date,
                                                          period_end_depreciation_date,
                                                          days_already_depreciated,
                                                          days_left_to_depreciated,
                                                          residual_declining)
                residual_amount -= amount

                if not posted_depreciation_move_ids:
                    # Subtracts the imported amount from the first depreciation moves until we reach it
                    # (might skip several depreciation entries)
                    if abs(imported_amount) <= abs(amount):
                        amount -= imported_amount
                        imported_amount = 0
                    else:
                        imported_amount -= amount
                        amount = 0

                if self.method == 'degressive_then_linear' and final_depreciation_date < period_end_depreciation_date:
                    period_end_depreciation_date = final_depreciation_date

                if not float_is_zero(amount,
                                     precision_rounding=self.currency_id.rounding):
                    # For deferred revenues, we should invert the amounts.
                    if period_end_depreciation_date:
                        if self.leasee_contract_ids.commencement_date and self.leasee_contract_ids.inception_date and period_end_depreciation_date >= self.leasee_contract_ids.commencement_date and period_end_depreciation_date <= self.leasee_contract_ids.inception_date and self.leasee_contract_ids.commencement_date < self.leasee_contract_ids.inception_date:
                            depreciation_move_values.append(self.env[
                                'account.move']._prepare_move_for_asset_depreciation(
                                {
                                    'amount': amount,
                                    'asset_id': self,
                                    'depreciation_beginning_date': start_depreciation_date,
                                    'date': self.leasee_contract_ids.inception_date,
                                    'asset_number_days': days,
                                }))
                        else:
                            depreciation_move_values.append(self.env[
                                'account.move']._prepare_move_for_asset_depreciation(
                                {
                                    'amount': amount,
                                    'asset_id': self,
                                    'depreciation_beginning_date': start_depreciation_date,
                                    'date': period_end_depreciation_date,
                                    'asset_number_days': days,
                                }))
                    else:
                        depreciation_move_values.append(self.env[
                            'account.move']._prepare_move_for_asset_depreciation(
                            {
                                'amount': amount,
                                'asset_id': self,
                                'depreciation_beginning_date': start_depreciation_date,
                                'date': period_end_depreciation_date,
                                'asset_number_days': days,
                            }))
                days_already_depreciated += days

                if period_end_depreciation_date == period_end_fiscalyear_date:
                    days_left_to_depreciated = self.asset_lifetime_days - days_already_depreciated
                    residual_declining = residual_amount

                start_depreciation_date = period_end_depreciation_date + relativedelta(
                    days=1)
        return depreciation_move_values

    @api.depends('method_number', 'method_period', 'prorata_computation_type')
    def _compute_lifetime_days(self):
        for asset in self:
            if asset.method_period == 'day':
                number_of_days = self.end_date - self.start_date
                asset.asset_lifetime_days = number_of_days.days
            else:
                if asset.prorata_computation_type == 'daily_computation':
                    asset.asset_lifetime_days = (
                            asset.prorata_date + relativedelta(
                        months=int(
                            asset.method_period) * asset.method_number) - asset.prorata_date).days
                else:
                    asset.asset_lifetime_days = int(
                        asset.method_period) * asset.method_number * DAYS_PER_MONTH
