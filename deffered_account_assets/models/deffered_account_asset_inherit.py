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

    def _recompute_board(self, start_depreciation_date=False):
        self.ensure_one()
        # All depreciation moves that are posted
        posted_depreciation_move_ids = self.depreciation_move_ids.filtered(
            lambda mv: mv.state == 'posted' and not mv.asset_value_change
        ).sorted(key=lambda mv: (mv.date, mv.id))
        imported_amount = self.already_depreciated_amount_import
        residual_amount = self.value_residual - sum(self.depreciation_move_ids.filtered(lambda mv: mv.state == 'draft').mapped('depreciation_value'))
        if not posted_depreciation_move_ids:
            residual_amount += imported_amount
        residual_declining = residual_at_compute = residual_amount
        # start_yearly_period is needed in the 'degressive' and 'degressive_then_linear' methods to compute the amount when the period is monthly
        start_recompute_date = start_depreciation_date = start_yearly_period = start_depreciation_date or self.paused_prorata_date
        last_day_asset = self._get_last_day_asset()
        final_depreciation_date = self._get_end_period_date(last_day_asset)
        total_lifetime_left = self._get_delta_days(start_depreciation_date, last_day_asset)

        depreciation_move_values = []
        if not float_is_zero(self.value_residual, precision_rounding=self.currency_id.rounding):
            while not self.currency_id.is_zero(residual_amount) and start_depreciation_date < final_depreciation_date:
                period_end_depreciation_date = self._get_end_period_date(start_depreciation_date)
                period_end_fiscalyear_date = self.company_id.compute_fiscalyear_dates(period_end_depreciation_date).get('date_to')
                lifetime_left = self._get_delta_days(start_depreciation_date, last_day_asset)
                days, amount = self._compute_board_amount(residual_amount, start_depreciation_date, period_end_depreciation_date, False, lifetime_left, residual_declining, start_yearly_period, total_lifetime_left, residual_at_compute, start_recompute_date)
                residual_amount -= amount

                if not posted_depreciation_move_ids:
                    # self.already_depreciated_amount_import management.
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

                if not float_is_zero(amount, precision_rounding=self.currency_id.rounding):
                    # For deferred revenues, we should invert the amounts.
                    depreciation_move_values.append(self.env['account.move']._prepare_move_for_asset_depreciation({
                        'amount': amount,
                        'asset_id': self,
                        'depreciation_beginning_date': start_depreciation_date,
                        'date': period_end_depreciation_date,
                        'asset_number_days': days,
                    }))

                if period_end_depreciation_date == period_end_fiscalyear_date:
                    start_yearly_period = self.company_id.compute_fiscalyear_dates(period_end_depreciation_date).get('date_from') + relativedelta(years=1)
                    residual_declining = residual_amount

                start_depreciation_date = period_end_depreciation_date + relativedelta(days=1)

        if self.accounting_date:
            for i in depreciation_move_values:
                if i['date'] < self.accounting_date:
                    i.update({
                        'date': self.accounting_date
                    })

        return depreciation_move_values


    def _get_last_day_asset(self):
        this = self.parent_id if self.parent_id else self
        if self.method_period == 'day':
            number_of_days = self.end_date - self.start_date
            return this.paused_prorata_date + relativedelta(days=number_of_days.days)
        else:
            return this.paused_prorata_date + relativedelta(months=int(this.method_period) * this.method_number, days=-1)

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
