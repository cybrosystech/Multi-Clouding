import json
import io
import datetime
import math
import xlsxwriter
from odoo import api, models, fields, _
from odoo.tools import datetime
from dateutil.relativedelta import relativedelta
from odoo.tools.misc import format_date
from odoo.tools import date_utils, get_lang
from babel.dates import get_quarter_names


class CashFlowStatement(models.Model):
    _name = 'cash.flow.statement'

    comparison = fields.Boolean('Allow comparison', default=True,
                                help='display the comparison filter')

    def _get_templates(self):
        return {
            'main_template': 'cash_flow_statement_report.html_content_view',
            'main_table_header_template': 'account_reports.main_table_header',
            'line_template': 'cash_flow_statement_report.line_template_cash_flow',
            'footnotes_template': 'account_reports.footnotes_template',
            'cash_flow_search_view': 'cash_flow_statement_report.cash_flow_search_view',
        }

    def _get_date_filter(self, options):
        date_from = ''
        date_to = ''
        period_type = ''
        previous_date = ''
        if options:
            if options['date_filter'] == 'this_month':
                date_from, date_to = date_utils.get_month(
                    fields.Date.context_today(self))
                previous_date = date_from - relativedelta(days=1)
                period_type = 'month'
            elif options['date_filter'] == 'this_quarter':
                date_from, date_to = date_utils.get_quarter(
                    fields.Date.context_today(self))
                previous_date = date_from - relativedelta(days=1)
                period_type = 'quarter'
            elif options['date_filter'] == 'this_year':
                company_fiscalyear_dates = self.env.company.compute_fiscalyear_dates(
                    fields.Date.context_today(self))
                date_from = company_fiscalyear_dates['date_from']
                date_to = company_fiscalyear_dates['date_to']
                previous_date = date_from - relativedelta(days=1)
                period_type = 'This financial year'
            elif options['date_filter'] == 'last_month':
                date_from, date_to = date_utils.get_month(
                    fields.Date.context_today(self) - relativedelta(months=1))
                previous_date = date_from - relativedelta(days=1)
                period_type = 'Last month'
            elif options['date_filter'] == 'last_year':
                company_fiscalyear_dates = self.env.company.compute_fiscalyear_dates(
                    fields.Date.context_today(self) - relativedelta(years=1))
                date_from = company_fiscalyear_dates['date_from']
                date_to = company_fiscalyear_dates['date_to']
                previous_date = date_from - relativedelta(days=1)
                period_type = 'Last financial year'
            elif options['date_filter'] == 'last_quarter':
                date_from, date_to = date_utils.get_quarter(
                    fields.Date.context_today(self) - relativedelta(months=3))
                previous_date = date_from - relativedelta(days=1)
                period_type = 'quarter'
            elif options['date_filter'] == 'custom':
                date_from = datetime.strptime(options['custom_from'],
                                              "%Y-%m-%d")
                date_to = datetime.strptime(options['custom_to'],
                                            "%Y-%m-%d")
                previous_date = date_from - relativedelta(days=1)
                period_type = 'custom'
        else:
            date_from, date_to = date_utils.get_month(
                fields.Date.context_today(self))
            previous_date = date_from - relativedelta(days=1)
            period_type = 'month'
            options['entry'] = ''
            options['date_filter'] = 'this_month'
            options['comparison'] = 'no_comparison'

        options['date'] = {
            'date_from': fields.Date.to_string(date_from),
            'date_to': fields.Date.to_string(date_to),
            'previous_date': fields.Date.to_string(previous_date),
            'period_type': period_type
        }

    def get_posted_filter(self, options):
        if not options['entry']:
            options['entry'] = 'posted'

    def get_comparison_filter(self, options):
        date_from = ''
        date_to = ''
        number_period = 1
        comparison_type = ''

        if options:
            if options['comparison'] == 'no_comparison':
                number_period = 1
                comparison_type = 'no_comparison'

            elif options['comparison'] == 'previous_period':
                number_period = options['number_period']
                date_from = options['date']['date_from']
                date_to = options['date']['date_to']
                comparison_type = 'previous_period'
            elif options['comparison'] == 'same_period_last_year':
                number_period = options['number_period']
                date_from = options['date']['date_from']
                date_to = options['date']['date_to']
                comparison_type = 'same_period_last_year'
            elif options['comparison'] == 'custom':
                number_period = 1
                comparison_type = 'custom'
        else:
            date_from, date_to = date_utils.get_month(
                fields.Date.context_today(self))
            previous_date = date_from - relativedelta(days=1)
            period_type = 'month'
            comparison_type = 'no_comparison'
            options['entry'] = ''
            options['date_filter'] = 'this_month'
            options['comparison'] = 'no_comparison'

        # options_filter = previous_filter

        options['comparison'] = {
            # 'filter': options_filter,
            'number_period': number_period,
            'date_from': date_from,
            'date_to': date_to,
            'periods': [],
            'comparison_type': comparison_type,
        }
        date_from_obj = fields.Date.from_string(date_from)
        date_to_obj = fields.Date.from_string(date_to)
        if options['comparison']['comparison_type'] == 'custom':
            options['comparison']['periods'].append(self._get_dates_period(
                options,
                date_from_obj,
                date_to_obj,
                options['date']['mode'],
            ))
        elif options['comparison']['comparison_type'] in ['previous_period',
                                                          'same_period_last_year']:
            previous_period = options['date']
            for index in range(0, int(number_period)):
                if options['comparison']['comparison_type'] == 'previous_period':
                    period_vals = self._get_dates_previous_period(options,
                                                                  previous_period)
                elif options['comparison']['comparison_type'] == 'same_period_last_year':
                    period_vals = self._get_dates_previous_year(options,
                                                                previous_period)
                else:
                    date_from_obj = fields.Date.from_string(date_from)
                    date_to_obj = fields.Date.from_string(date_to)
                    strict_range = previous_period.get('strict_range', False)
                    period_vals = self._get_dates_period(options, date_from_obj,
                                                         date_to_obj,
                                                         previous_period[
                                                             'mode'],
                                                         strict_range=strict_range)
                options['comparison']['periods'].append(period_vals)
                previous_period = period_vals

    @api.model
    def _get_dates_previous_year(self, options, period_vals):
        '''Shift the period to the previous year.
        :param options:     The report options.
        :param period_vals: A dictionary generated by the _get_dates_period method.
        :return:            A dictionary containing:
            * date_from * date_to * string * period_type *
        '''
        period_type = period_vals['period_type']
        # mode = period_vals['mode']
        mode = 'range'

        strict_range = period_vals.get('strict_range', False)
        date_from = fields.Date.from_string(period_vals['date_from'])
        date_from = date_from - relativedelta(years=1)
        date_to = fields.Date.from_string(period_vals['date_to'])
        date_to = date_to - relativedelta(years=1)

        if period_type == 'month':
            date_from, date_to = date_utils.get_month(date_to)
        return self._get_dates_period(options, date_from, date_to, mode,
                                      period_type=period_type,
                                      strict_range=strict_range)

    @api.model
    def _get_dates_previous_period(self, options, period_vals):
        '''Shift the period to the previous one.
        :param period_vals: A dictionary generated by the _get_dates_period method.
        :return:            A dictionary containing:
            * date_from * date_to * string * period_type *
        '''
        period_type = period_vals['period_type']
        mode = 'range'
        strict_range = period_vals.get('strict_range', False)
        date_from = fields.Date.from_string(period_vals['date_from'])
        date_to = date_from - relativedelta(days=1)

        if period_type in ('This financial year', 'today'):
            # Don't pass the period_type to _get_dates_period to be able to retrieve the account.fiscal.year record if
            # necessary.
            company_fiscalyear_dates = self.env.company.compute_fiscalyear_dates(
                date_to)
            return self._get_dates_period(options,
                                          company_fiscalyear_dates['date_from'],
                                          company_fiscalyear_dates['date_to'],
                                          mode, strict_range=strict_range)
        if period_type in ('month', 'custom'):
            return self._get_dates_period(options,
                                          *date_utils.get_month(date_to), mode,
                                          period_type='month',
                                          strict_range=strict_range)
        if period_type == 'quarter':
            return self._get_dates_period(options,
                                          *date_utils.get_quarter(date_to),
                                          mode, period_type='quarter',
                                          strict_range=strict_range)
        if period_type == 'year':
            return self._get_dates_period(options,
                                          *date_utils.get_fiscal_year(date_to),
                                          mode, period_type='year',
                                          strict_range=strict_range)
        return None

    @api.model
    def _get_dates_period(self, options, date_from, date_to, mode,
                          period_type=None, strict_range=False):
        '''Compute some information about the period:
        * The name to display on the report.
        * The period type (e.g. quarter) if not specified explicitly.
        :param date_from:   The starting date of the period.
        :param date_to:     The ending date of the period.
        :param period_type: The type of the interval date_from -> date_to.
        :return:            A dictionary containing:
            * date_from * date_to * string * period_type * mode *
        '''

        def match(dt_from, dt_to):
            return (dt_from, dt_to) == (date_from, date_to)

        string = None
        # If no date_from or not date_to, we are unable to determine a period
        if not period_type or period_type == 'custom':
            date = date_to or date_from
            company_fiscalyear_dates = self.env.company.compute_fiscalyear_dates(
                date)
            if match(company_fiscalyear_dates['date_from'],
                     company_fiscalyear_dates['date_to']):
                period_type = 'This financial year'
                if company_fiscalyear_dates.get('record'):
                    string = company_fiscalyear_dates['record'].name
            elif match(*date_utils.get_month(date)):
                period_type = 'month'
            elif match(*date_utils.get_quarter(date)):
                period_type = 'quarter'
            elif match(*date_utils.get_fiscal_year(date)):
                period_type = 'year'
            elif match(date_utils.get_month(date)[0], fields.Date.today()):
                period_type = 'today'
            else:
                period_type = 'custom'
        elif period_type == 'This financial year':
            date = date_to or date_from
            company_fiscalyear_dates = self.env.company.compute_fiscalyear_dates(
                date)
            record = company_fiscalyear_dates.get('record')
            string = record and record.name

        if not string:
            fy_day = self.env.company.fiscalyear_last_day
            fy_month = int(self.env.company.fiscalyear_last_month)
            if mode == 'single':
                string = _('As of %s') % (
                    format_date(self.env, fields.Date.to_string(date_to)))
            elif period_type == 'year' or (
                    period_type == 'This financial year' and (
                    date_from, date_to) == date_utils.get_fiscal_year(date_to)):
                string = date_to.strftime('%Y')
            elif period_type == 'fiscalyear' and (
                    date_from, date_to) == date_utils.get_fiscal_year(date_to,
                                                                      day=fy_day,
                                                                      month=fy_month):
                string = '%s - %s' % (date_to.year - 1, date_to.year)
            elif period_type == 'month':
                string = format_date(self.env, fields.Date.to_string(date_to),
                                     date_format='MMM yyyy')
            elif period_type == 'quarter':
                quarter_names = get_quarter_names('abbreviated',
                                                  locale=get_lang(
                                                      self.env).code)
                string = u'%s\N{NO-BREAK SPACE}%s' % (
                    quarter_names[date_utils.get_quarter_number(date_to)],
                    date_to.year)
            else:
                dt_from_str = format_date(self.env,
                                          fields.Date.to_string(date_from))
                dt_to_str = format_date(self.env,
                                        fields.Date.to_string(date_to))
                string = _('From %s\nto  %s') % (dt_from_str, dt_to_str)

        return {
            'string': string,
            'period_type': period_type,
            'mode': mode,
            'strict_range': strict_range,
            'date_from': date_from and fields.Date.to_string(
                date_from) or False,
            'date_to': fields.Date.to_string(date_to),
        }

    def _get_cashflow_options(self, options):
        if not options:
            options = {}
        self._get_date_filter(options)
        self.get_posted_filter(options)
        self.get_comparison_filter(options)
        return options

    def get_cash_flow_information(self, filter):
        options = self._get_cashflow_options(filter)
        info = {
            'options': options,
            'main_html': self.get_html_content(options),
            'searchview_html': self.env['ir.ui.view']._render_template(
                self._get_templates().get('cash_flow_search_view',
                                          'cash_flow_statement_report.cash_flow_search_view'),
                values={'options': options}),
            'buttons': self.get_button_cashflow()
        }
        return info

    def get_loss_for_period(self, options, states_args, number_period):
        loss_for_period_list = []
        query = '''select sum(journal_item.credit) as credit, sum(journal_item.debit) as debit 
                    from account_move_line as journal_item
                    left join account_account as account on journal_item.account_id = account.id
                    '''
        if options['comparison']['comparison_type'] == 'previous_period':
            if options['date_filter'] == 'this_month' or options[
                'date_filter'] == 'last_month':
                for i in range(0, number_period + 1):
                    from_date = datetime.strptime(options['date']['date_from'],
                                                  "%Y-%m-%d")
                    from_date = from_date - relativedelta(months=i)
                    to_date = from_date + relativedelta(months=1)
                    to_date = to_date - relativedelta(days=1)
                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                        and journal_item.company_id = %(company_ids)s
                                        and journal_item.date >= %(from_date)s 
                                        and journal_item.date <= %(to_date)s
                                        and {states_args}
                                        '''.format(states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '400000',
                                         'code_end': '699999',
                                         'company_ids': self.env.company.id})
                    loss_for_period = self.env.cr.dictfetchall()
                    loss_for_period_credit = loss_for_period[0]['credit'] if \
                        loss_for_period[0]['credit'] else 0
                    loss_for_period_debit = loss_for_period[0]['debit'] if \
                        loss_for_period[0]['debit'] else 0
                    tot = round(
                        ((loss_for_period_debit - loss_for_period_credit) * -1),
                        2)
                    loss_for_period_list.append(tot)
                return loss_for_period_list
            elif options['date_filter'] == 'this_quarter' or options['date_filter'] == 'last_quarter':
                for i in range(0, number_period + 1):
                    from_date = datetime.strptime(options['date']['date_from'],
                                                  "%Y-%m-%d")
                    from_date = from_date + relativedelta(months=-3 * i)
                    current_quarter = round((from_date.month - 1) / 3 + 1)
                    from_date = datetime(from_date.year,
                                         3 * current_quarter - 2, 1)
                    to_date = datetime(from_date.year,
                                       3 * current_quarter + 1,
                                       1) + relativedelta(days=-1)
                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                            and journal_item.company_id = %(company_ids)s
                                            and journal_item.date >= %(from_date)s 
                                            and journal_item.date <= %(to_date)s
                                            and {states_args}
                                            '''.format(states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '400000',
                                         'code_end': '699999',
                                         'company_ids': self.env.company.id})
                    loss_for_period = self.env.cr.dictfetchall()
                    loss_for_period_credit = loss_for_period[0]['credit'] if \
                        loss_for_period[0]['credit'] else 0
                    loss_for_period_debit = loss_for_period[0]['debit'] if \
                        loss_for_period[0]['debit'] else 0
                    tot = round(
                        ((loss_for_period_debit - loss_for_period_credit) * -1),
                        2)
                    loss_for_period_list.append(tot)
                return loss_for_period_list
            elif options['date_filter'] == 'this_year' or options['date_filter'] == 'last_year':
                for i in range(0, number_period + 1):
                    from_date = datetime.strptime(options['date']['date_from'],
                                                  "%Y-%m-%d")
                    from_date = from_date - relativedelta(years=i)
                    to_date = from_date.replace(month=12, day=31)
                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                and journal_item.company_id = %(company_ids)s
                                                and journal_item.date >= %(from_date)s 
                                                and journal_item.date <= %(to_date)s
                                                and {states_args}
                                                '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '400000',
                                         'code_end': '699999',
                                         'company_ids': self.env.company.id})
                    loss_for_period = self.env.cr.dictfetchall()
                    loss_for_period_credit = loss_for_period[0]['credit'] if \
                        loss_for_period[0]['credit'] else 0
                    loss_for_period_debit = loss_for_period[0]['debit'] if \
                        loss_for_period[0]['debit'] else 0
                    tot = round(
                        ((loss_for_period_debit - loss_for_period_credit) * -1),
                        2)
                    loss_for_period_list.append(tot)
                return loss_for_period_list

        elif options['comparison'][
            'comparison_type'] == 'same_period_last_year':
            if options['date_filter'] == 'this_month' or options[
                'date_filter'] == 'last_month':
                for i in range(0, number_period + 1):
                    from_date = datetime.strptime(options['date']['date_from'],
                                                  "%Y-%m-%d")
                    from_date = from_date - relativedelta(years=i)
                    to_date = from_date + relativedelta(months=1)
                    to_date = to_date - relativedelta(days=1)
                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                            and journal_item.company_id = %(company_ids)s
                                                            and journal_item.date >= %(from_date)s 
                                                            and journal_item.date <= %(to_date)s
                                                            and {states_args}
                                                            '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '400000',
                                         'code_end': '699999',
                                         'company_ids': self.env.company.id})
                    loss_for_period = self.env.cr.dictfetchall()
                    loss_for_period_credit = loss_for_period[0]['credit'] if \
                        loss_for_period[0]['credit'] else 0
                    loss_for_period_debit = loss_for_period[0]['debit'] if \
                        loss_for_period[0]['debit'] else 0
                    tot = round(
                        ((loss_for_period_debit - loss_for_period_credit) * -1),
                        2)
                    loss_for_period_list.append(tot)
                return loss_for_period_list
            elif options['date_filter'] == 'this_quarter' or options['date_filter'] == 'last_quarter':
                for i in range(0, number_period + 1):
                    from_date = datetime.strptime(options['date']['date_from'],
                                                  "%Y-%m-%d")
                    from_date = from_date + relativedelta(years=-i)
                    current_quarter = round((from_date.month - 1) / 3 + 1)
                    from_date = datetime(from_date.year,
                                         3 * current_quarter - 2, 1)
                    to_date = datetime(from_date.year,
                                       3 * current_quarter + 1,
                                       1) + relativedelta(days=-1)
                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                                                and journal_item.company_id = %(company_ids)s
                                                                                and journal_item.date >= %(from_date)s 
                                                                                and journal_item.date <= %(to_date)s
                                                                                and {states_args}
                                                                                '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '400000',
                                         'code_end': '699999',
                                         'company_ids': self.env.company.id})
                    loss_for_period = self.env.cr.dictfetchall()
                    loss_for_period_credit = loss_for_period[0]['credit'] if \
                        loss_for_period[0]['credit'] else 0
                    loss_for_period_debit = loss_for_period[0]['debit'] if \
                        loss_for_period[0]['debit'] else 0
                    tot = round(
                        ((loss_for_period_debit - loss_for_period_credit) * -1),
                        2)
                    loss_for_period_list.append(tot)

                return loss_for_period_list
            elif options['date_filter'] == 'this_year' or options['date_filter'] == 'last_year':
                for i in range(0, number_period + 1):
                    from_date = datetime.strptime(options['date']['date_from'],
                                                  "%Y-%m-%d")
                    from_date = from_date - relativedelta(years=i)
                    to_date = from_date.replace(month=12, day=31)
                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                and journal_item.company_id = %(company_ids)s
                                                and journal_item.date >= %(from_date)s 
                                                and journal_item.date <= %(to_date)s
                                                and {states_args}
                                                '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '400000',
                                         'code_end': '699999',
                                         'company_ids': self.env.company.id})
                    loss_for_period = self.env.cr.dictfetchall()
                    loss_for_period_credit = loss_for_period[0]['credit'] if \
                        loss_for_period[0]['credit'] else 0
                    loss_for_period_debit = loss_for_period[0]['debit'] if \
                        loss_for_period[0]['debit'] else 0
                    tot = round(
                        ((loss_for_period_debit - loss_for_period_credit) * -1),
                        2)
                    loss_for_period_list.append(tot)
                return loss_for_period_list
        else:
            self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                            and journal_item.company_id = %(company_ids)s
                                            and journal_item.date >= %(from_date)s 
                                            and journal_item.date <= %(to_date)s
                                            and {states_args}
                                            '''.format(states_args=states_args),
                                {'from_date': options['date']['date_from'],
                                 'to_date': options['date']['date_to'],
                                 'code_start': '400000', 'code_end': '699999',
                                 'company_ids': self.env.company.id})
            loss_for_period = self.env.cr.dictfetchall()
            loss_for_period_credit = loss_for_period[0]['credit'] if \
                loss_for_period[0]['credit'] else 0
            loss_for_period_debit = loss_for_period[0]['debit'] if \
                loss_for_period[0]['debit'] else 0
            tot = round(
                ((loss_for_period_debit - loss_for_period_credit) * -1), 2)
            loss_for_period_list.append(tot)
            return loss_for_period_list

    def get_amortisation_right_dict(self, query, options, states_args):
        self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                    and journal_item.company_id = %(company_ids)s
                                    and journal_item.date >= %(from_date)s 
                                    and journal_item.date <= %(to_date)s
                                    and {states_args}
                                    '''.format(states_args=states_args),
                            {'from_date': options['date']['date_from'],
                             'to_date': options['date']['date_to'],
                             'code_start': '554101', 'code_end': '554999',
                             'company_ids': self.env.company.id})
        amortisation_right = self.env.cr.dictfetchall()
        amortisation_credit = amortisation_right[0]['credit'] if \
            amortisation_right[0]['credit'] else 0
        amortisation_debit = amortisation_right[0]['debit'] if \
            amortisation_right[0]['debit'] else 0
        amortisation_right_dict = {
            'id': 'amortisation_right_id',
            'name': 'Amortization of right of use assets',
            'level': 2,
            'class': 'cash_flow_line_val_tr',
            'columns': [
                {'name': round(amortisation_debit - amortisation_credit, 2),
                 'class': 'number'}]
        }
        return amortisation_right_dict

    def get_movement_trade_account_sum(self, query, options, states_args):
        self.env.cr.execute(query + '''where account.code in %(account_code)s
                                                    and journal_item.company_id = %(company_ids)s
                                                    and journal_item.date >= %(from_date)s 
                                                    and journal_item.date <= %(to_date)s
                                                    and {states_args}
                                                    '''.format(
            states_args=states_args),
                            {'from_date': options['date']['date_from'],
                             'to_date': options['date']['date_to'],
                             'account_code': ('111110', '116105'),
                             'company_ids': self.env.company.id})
        movement_trade_account = self.env.cr.dictfetchall()
        movement_trade_account_credit = movement_trade_account[0]['credit'] if \
            movement_trade_account[0]['credit'] else 0
        movement_trade_account_debit = movement_trade_account[0]['debit'] if \
            movement_trade_account[0]['debit'] else 0
        return movement_trade_account_debit - movement_trade_account_credit

    def get_movement_trade_dict(self, query, options, states_args,
                                number_period):
        movement_trade_dict ={}
        movement_trade_list = []
        if options['comparison']['comparison_type'] == 'previous_period':
            if options['date_filter'] == 'this_month' or options['date_filter'] == 'last_month':
                for i in range(0, number_period + 1):
                    from_date = datetime.strptime(options['date']['date_from'],
                                                  "%Y-%m-%d")
                    from_date = from_date - relativedelta(months=i)
                    to_date = from_date + relativedelta(months=1)
                    to_date = to_date - relativedelta(days=1)
                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                            and journal_item.company_id = %(company_ids)s
                                                            and journal_item.date >= %(from_date)s 
                                                            and journal_item.date <= %(to_date)s
                                                            and {states_args}
                                                            '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '113101',
                                         'code_end': '113999',
                                         'company_ids': self.env.company.id})
                    movement_trade = self.env.cr.dictfetchall()
                    movement_trade_credit = movement_trade[0]['credit'] if \
                        movement_trade[0]['credit'] else 0
                    movement_trade_debit = movement_trade[0]['debit'] if \
                        movement_trade[0][
                            'debit'] else 0
                    movement_trade_sum = movement_trade_debit - movement_trade_credit

                    self.env.cr.execute(query + '''where account.code in %(account_code)s
                                                                and journal_item.company_id = %(company_ids)s
                                                                and journal_item.date >= %(from_date)s 
                                                                and journal_item.date <= %(to_date)s
                                                                and {states_args}
                                                                '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'account_code': ('111110', '116105'),
                                         'company_ids': self.env.company.id})
                    movement_trade_account = self.env.cr.dictfetchall()
                    movement_trade_account_credit = movement_trade_account[0][
                        'credit'] if \
                        movement_trade_account[0]['credit'] else 0
                    movement_trade_account_debit = movement_trade_account[0][
                        'debit'] if \
                        movement_trade_account[0]['debit'] else 0

                    movement_trade_account_sum = movement_trade_account_debit - movement_trade_account_credit
                    movement = round(((
                                              movement_trade_sum + movement_trade_account_sum) * -1),
                                     2)
                    movement_trade_list.append(movement)

                movement_trade_dict = {
                    'id': 'movement_trade',
                    'name': 'Movement in trade and other receivables',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {
                            'name': '',
                            'class': 'number'}]
                }
                movement_trade_dict['columns'][0]['name'] = movement_trade_list
                return movement_trade_dict
            elif options['date_filter'] == 'this_quarter' or options['date_filter'] == 'last_quarter':
                for i in range(0, number_period + 1):
                    from_date = datetime.strptime(options['date']['date_from'],
                                                  "%Y-%m-%d")
                    from_date = from_date + relativedelta(months=-3 * i)
                    current_quarter = round((from_date.month - 1) / 3 + 1)
                    from_date = datetime(from_date.year,
                                         3 * current_quarter - 2, 1)
                    to_date = datetime(from_date.year,
                                       3 * current_quarter + 1,
                                       1) + relativedelta(days=-1)
                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                                                and journal_item.company_id = %(company_ids)s
                                                                                and journal_item.date >= %(from_date)s 
                                                                                and journal_item.date <= %(to_date)s
                                                                                and {states_args}
                                                                                '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '113101',
                                         'code_end': '113999',
                                         'company_ids': self.env.company.id})
                    movement_trade = self.env.cr.dictfetchall()
                    movement_trade_credit = movement_trade[0]['credit'] if \
                        movement_trade[0]['credit'] else 0
                    movement_trade_debit = movement_trade[0]['debit'] if \
                        movement_trade[0][
                            'debit'] else 0
                    movement_trade_sum = movement_trade_debit - movement_trade_credit

                    self.env.cr.execute(query + '''where account.code in %(account_code)s
                                                                                    and journal_item.company_id = %(company_ids)s
                                                                                    and journal_item.date >= %(from_date)s 
                                                                                    and journal_item.date <= %(to_date)s
                                                                                    and {states_args}
                                                                                    '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'account_code': ('111110', '116105'),
                                         'company_ids': self.env.company.id})
                    movement_trade_account = self.env.cr.dictfetchall()
                    movement_trade_account_credit = movement_trade_account[0][
                        'credit'] if \
                        movement_trade_account[0]['credit'] else 0
                    movement_trade_account_debit = movement_trade_account[0][
                        'debit'] if \
                        movement_trade_account[0]['debit'] else 0

                    movement_trade_account_sum = movement_trade_account_debit - movement_trade_account_credit
                    movement = round(((
                                              movement_trade_sum + movement_trade_account_sum) * -1),
                                     2)
                    movement_trade_list.append(movement)

                movement_trade_dict = {
                    'id': 'movement_trade',
                    'name': 'Movement in trade and other receivables',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {
                            'name': '',
                            'class': 'number'}]
                }
                movement_trade_dict['columns'][0]['name'] = movement_trade_list
                return movement_trade_dict
            elif options['date_filter'] == 'this_year' or options['date_filter'] == 'last_year':
                for i in range(0, number_period + 1):
                    from_date = datetime.strptime(options['date']['date_from'],
                                                  "%Y-%m-%d")
                    from_date = from_date - relativedelta(years=i)
                    to_date = from_date.replace(month=12,day=31)
                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                                                    and journal_item.company_id = %(company_ids)s
                                                                                    and journal_item.date >= %(from_date)s 
                                                                                    and journal_item.date <= %(to_date)s
                                                                                    and {states_args}
                                                                                    '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '113101',
                                         'code_end': '113999',
                                         'company_ids': self.env.company.id})
                    movement_trade = self.env.cr.dictfetchall()
                    movement_trade_credit = movement_trade[0]['credit'] if \
                        movement_trade[0]['credit'] else 0
                    movement_trade_debit = movement_trade[0]['debit'] if \
                        movement_trade[0][
                            'debit'] else 0
                    movement_trade_sum = movement_trade_debit - movement_trade_credit

                    self.env.cr.execute(query + '''where account.code in %(account_code)s
                                                                                        and journal_item.company_id = %(company_ids)s
                                                                                        and journal_item.date >= %(from_date)s 
                                                                                        and journal_item.date <= %(to_date)s
                                                                                        and {states_args}
                                                                                        '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'account_code': ('111110', '116105'),
                                         'company_ids': self.env.company.id})
                    movement_trade_account = self.env.cr.dictfetchall()
                    movement_trade_account_credit = movement_trade_account[0][
                        'credit'] if \
                        movement_trade_account[0]['credit'] else 0
                    movement_trade_account_debit = movement_trade_account[0][
                        'debit'] if \
                        movement_trade_account[0]['debit'] else 0

                    movement_trade_account_sum = movement_trade_account_debit - movement_trade_account_credit
                    movement = round(((
                                              movement_trade_sum + movement_trade_account_sum) * -1),
                                     2)
                    movement_trade_list.append(movement)

                movement_trade_dict = {
                    'id': 'movement_trade',
                    'name': 'Movement in trade and other receivables',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {
                            'name': '',
                            'class': 'number'}]
                }
                movement_trade_dict['columns'][0]['name'] = movement_trade_list
                return movement_trade_dict

            else:
                for i in range(0, number_period + 1):
                    from_date = datetime.strptime(options['date']['date_from'],
                                                  "%Y-%m-%d")
                    from_date = from_date - relativedelta(months=i)
                    to_date = from_date + relativedelta(months=1)
                    to_date = to_date - relativedelta(days=1)
                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                            and journal_item.company_id = %(company_ids)s
                                                            and journal_item.date >= %(from_date)s 
                                                            and journal_item.date <= %(to_date)s
                                                            and {states_args}
                                                            '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '113101',
                                         'code_end': '113999',
                                         'company_ids': self.env.company.id})
                    movement_trade = self.env.cr.dictfetchall()
                    movement_trade_credit = movement_trade[0]['credit'] if \
                        movement_trade[0]['credit'] else 0
                    movement_trade_debit = movement_trade[0]['debit'] if \
                        movement_trade[0][
                            'debit'] else 0
                    movement_trade_sum = movement_trade_debit - movement_trade_credit

                    self.env.cr.execute(query + '''where account.code in %(account_code)s
                                                                and journal_item.company_id = %(company_ids)s
                                                                and journal_item.date >= %(from_date)s 
                                                                and journal_item.date <= %(to_date)s
                                                                and {states_args}
                                                                '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'account_code': ('111110', '116105'),
                                         'company_ids': self.env.company.id})
                    movement_trade_account = self.env.cr.dictfetchall()
                    movement_trade_account_credit = movement_trade_account[0][
                        'credit'] if \
                        movement_trade_account[0]['credit'] else 0
                    movement_trade_account_debit = movement_trade_account[0][
                        'debit'] if \
                        movement_trade_account[0]['debit'] else 0

                    movement_trade_account_sum = movement_trade_account_debit - movement_trade_account_credit
                    movement = round(((
                                              movement_trade_sum + movement_trade_account_sum) * -1),
                                     2)
                    movement_trade_list.append(movement)

                movement_trade_dict = {
                    'id': 'movement_trade',
                    'name': 'Movement in trade and other receivables',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {
                            'name': '',
                            'class': 'number'}]
                }
                movement_trade_dict['columns'][0]['name'] = movement_trade_list
                return movement_trade_dict

        elif options['comparison']['comparison_type'] == 'same_period_last_year':
            if options['date_filter'] == 'this_month' or options[
                'date_filter'] == 'last_month':
                for j in range(0, number_period + 1):
                    from_date = datetime.strptime(options['date']['date_from'],
                                                  "%Y-%m-%d")
                    from_date = from_date - relativedelta(years=j)
                    to_date = from_date + relativedelta(months=1)
                    to_date = to_date - relativedelta(days=1)
                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                                                and journal_item.company_id = %(company_ids)s
                                                                                and journal_item.date >= %(from_date)s 
                                                                                and journal_item.date <= %(to_date)s
                                                                                and {states_args}
                                                                                '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '113101',
                                         'code_end': '113999',
                                         'company_ids': self.env.company.id})
                    movement_trade = self.env.cr.dictfetchall()
                    movement_trade_credit = movement_trade[0]['credit'] if \
                        movement_trade[0]['credit'] else 0
                    movement_trade_debit = movement_trade[0]['debit'] if \
                        movement_trade[0][
                            'debit'] else 0
                    movement_trade_sum = movement_trade_debit - movement_trade_credit

                    self.env.cr.execute(query + '''where account.code in %(account_code)s
                                                                                    and journal_item.company_id = %(company_ids)s
                                                                                    and journal_item.date >= %(from_date)s 
                                                                                    and journal_item.date <= %(to_date)s
                                                                                    and {states_args}
                                                                                    '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'account_code': ('111110', '116105'),
                                         'company_ids': self.env.company.id})
                    movement_trade_account = self.env.cr.dictfetchall()
                    movement_trade_account_credit = movement_trade_account[0][
                        'credit'] if \
                        movement_trade_account[0]['credit'] else 0
                    movement_trade_account_debit = movement_trade_account[0][
                        'debit'] if \
                        movement_trade_account[0]['debit'] else 0

                    movement_trade_account_sum = movement_trade_account_debit - movement_trade_account_credit
                    movement = round(((
                                              movement_trade_sum + movement_trade_account_sum) * -1),
                                     2)
                    movement_trade_list.append(movement)

                movement_trade_dict = {
                    'id': 'movement_trade',
                    'name': 'Movement in trade and other receivables',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {
                            'name': '',
                            'class': 'number'}]
                }
                movement_trade_dict['columns'][0]['name'] = movement_trade_list
                return movement_trade_dict
            elif options['date_filter'] == 'this_quarter' or options['date_filter'] == 'last_quarter':
                for i in range(0, number_period + 1):
                    from_date = datetime.strptime(options['date']['date_from'],
                                                  "%Y-%m-%d")
                    from_date = from_date + relativedelta(years=-i)
                    current_quarter = round((from_date.month - 1) / 3 + 1)
                    from_date = datetime(from_date.year,
                                         3 * current_quarter - 2, 1)
                    to_date = datetime(from_date.year,
                                       3 * current_quarter + 1,
                                       1) + relativedelta(days=-1)
                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                                                and journal_item.company_id = %(company_ids)s
                                                                                and journal_item.date >= %(from_date)s 
                                                                                and journal_item.date <= %(to_date)s
                                                                                and {states_args}
                                                                                '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '113101',
                                         'code_end': '113999',
                                         'company_ids': self.env.company.id})
                    movement_trade = self.env.cr.dictfetchall()
                    movement_trade_credit = movement_trade[0]['credit'] if \
                        movement_trade[0]['credit'] else 0
                    movement_trade_debit = movement_trade[0]['debit'] if \
                        movement_trade[0][
                            'debit'] else 0
                    movement_trade_sum = movement_trade_debit - movement_trade_credit

                    self.env.cr.execute(query + '''where account.code in %(account_code)s
                                                                                    and journal_item.company_id = %(company_ids)s
                                                                                    and journal_item.date >= %(from_date)s 
                                                                                    and journal_item.date <= %(to_date)s
                                                                                    and {states_args}
                                                                                    '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'account_code': ('111110', '116105'),
                                         'company_ids': self.env.company.id})
                    movement_trade_account = self.env.cr.dictfetchall()
                    movement_trade_account_credit = movement_trade_account[0][
                        'credit'] if \
                        movement_trade_account[0]['credit'] else 0
                    movement_trade_account_debit = movement_trade_account[0][
                        'debit'] if \
                        movement_trade_account[0]['debit'] else 0

                    movement_trade_account_sum = movement_trade_account_debit - movement_trade_account_credit
                    movement = round(((
                                              movement_trade_sum + movement_trade_account_sum) * -1),
                                     2)
                    movement_trade_list.append(movement)

                movement_trade_dict = {
                    'id': 'movement_trade',
                    'name': 'Movement in trade and other receivables',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {
                            'name': '',
                            'class': 'number'}]
                }
                movement_trade_dict['columns'][0]['name'] = movement_trade_list
                return movement_trade_dict
            elif options['date_filter'] == 'this_year' or options['date_filter'] == 'last_year':
                for i in range(0, number_period + 1):
                    from_date = datetime.strptime(options['date']['date_from'],
                                                  "%Y-%m-%d")
                    from_date = from_date - relativedelta(years=i)
                    to_date = from_date.replace(month=12,day=31)
                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                                                    and journal_item.company_id = %(company_ids)s
                                                                                    and journal_item.date >= %(from_date)s 
                                                                                    and journal_item.date <= %(to_date)s
                                                                                    and {states_args}
                                                                                    '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '113101',
                                         'code_end': '113999',
                                         'company_ids': self.env.company.id})
                    movement_trade = self.env.cr.dictfetchall()
                    movement_trade_credit = movement_trade[0]['credit'] if \
                        movement_trade[0]['credit'] else 0
                    movement_trade_debit = movement_trade[0]['debit'] if \
                        movement_trade[0][
                            'debit'] else 0
                    movement_trade_sum = movement_trade_debit - movement_trade_credit

                    self.env.cr.execute(query + '''where account.code in %(account_code)s
                                                                                        and journal_item.company_id = %(company_ids)s
                                                                                        and journal_item.date >= %(from_date)s 
                                                                                        and journal_item.date <= %(to_date)s
                                                                                        and {states_args}
                                                                                        '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'account_code': ('111110', '116105'),
                                         'company_ids': self.env.company.id})
                    movement_trade_account = self.env.cr.dictfetchall()
                    movement_trade_account_credit = movement_trade_account[0][
                        'credit'] if \
                        movement_trade_account[0]['credit'] else 0
                    movement_trade_account_debit = movement_trade_account[0][
                        'debit'] if \
                        movement_trade_account[0]['debit'] else 0

                    movement_trade_account_sum = movement_trade_account_debit - movement_trade_account_credit
                    movement = round(((
                                              movement_trade_sum + movement_trade_account_sum) * -1),
                                     2)
                    movement_trade_list.append(movement)

                movement_trade_dict = {
                    'id': 'movement_trade',
                    'name': 'Movement in trade and other receivables',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {
                            'name': '',
                            'class': 'number'}]
                }
                movement_trade_dict['columns'][0]['name'] = movement_trade_list
                return movement_trade_dict
            else:
                for j in range(0, number_period + 1):
                    from_date = datetime.strptime(options['date']['date_from'],
                                                  "%Y-%m-%d")
                    from_date = from_date - relativedelta(years=j)
                    to_date = from_date + relativedelta(months=1)
                    to_date = to_date - relativedelta(days=1)
                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                                                and journal_item.company_id = %(company_ids)s
                                                                                and journal_item.date >= %(from_date)s 
                                                                                and journal_item.date <= %(to_date)s
                                                                                and {states_args}
                                                                                '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '113101',
                                         'code_end': '113999',
                                         'company_ids': self.env.company.id})
                    movement_trade = self.env.cr.dictfetchall()
                    movement_trade_credit = movement_trade[0]['credit'] if \
                        movement_trade[0]['credit'] else 0
                    movement_trade_debit = movement_trade[0]['debit'] if \
                        movement_trade[0][
                            'debit'] else 0
                    movement_trade_sum = movement_trade_debit - movement_trade_credit

                    self.env.cr.execute(query + '''where account.code in %(account_code)s
                                                                                    and journal_item.company_id = %(company_ids)s
                                                                                    and journal_item.date >= %(from_date)s 
                                                                                    and journal_item.date <= %(to_date)s
                                                                                    and {states_args}
                                                                                    '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'account_code': ('111110', '116105'),
                                         'company_ids': self.env.company.id})
                    movement_trade_account = self.env.cr.dictfetchall()
                    movement_trade_account_credit = movement_trade_account[0][
                        'credit'] if \
                        movement_trade_account[0]['credit'] else 0
                    movement_trade_account_debit = movement_trade_account[0][
                        'debit'] if \
                        movement_trade_account[0]['debit'] else 0

                    movement_trade_account_sum = movement_trade_account_debit - movement_trade_account_credit
                    movement = round(((
                                              movement_trade_sum + movement_trade_account_sum) * -1),
                                     2)
                    movement_trade_list.append(movement)

                movement_trade_dict = {
                    'id': 'movement_trade',
                    'name': 'Movement in trade and other receivables',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {
                            'name': '',
                            'class': 'number'}]
                }
                movement_trade_dict['columns'][0]['name'] = movement_trade_list
                return movement_trade_dict
        else:
            self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                        and journal_item.company_id = %(company_ids)s
                                        and journal_item.date >= %(from_date)s 
                                        and journal_item.date <= %(to_date)s
                                        and {states_args}
                                        '''.format(states_args=states_args),
                                {'from_date': options['date']['date_from'],
                                 'to_date': options['date']['date_to'],
                                 'code_start': '113101', 'code_end': '113999',
                                 'company_ids': self.env.company.id})
            movement_trade = self.env.cr.dictfetchall()
            movement_trade_credit = movement_trade[0]['credit'] if \
                movement_trade[0]['credit'] else 0
            movement_trade_debit = movement_trade[0]['debit'] if \
                movement_trade[0][
                    'debit'] else 0
            movement_trade_sum = movement_trade_debit - movement_trade_credit

            movement_trade_account_sum = self.get_movement_trade_account_sum(
                query,
                options,
                states_args)
            movement = round(((
                                      movement_trade_sum + movement_trade_account_sum) * -1),
                             2)
            movement_trade_list.append(movement)

            movement_trade_dict = {
                'id': 'movement_trade',
                'name': 'Movement in trade and other receivables',
                'level': 2,
                'class': 'cash_flow_line_val_tr',
                'columns': [
                    {
                        'name': '',
                        'class': 'number'}]
            }
            movement_trade_dict['columns'][0]['name'] = movement_trade_list
            return movement_trade_dict

    def get_movement_related_dict(self, query, options, states_args,
                                  number_period):
        movement_related_list = []
        if options['comparison']['comparison_type'] == 'previous_period':
            if options['date_filter'] == 'this_month' or options[
                'date_filter'] == 'last_month':
                for i in range(0, number_period + 1):
                    from_date = datetime.strptime(options['date']['date_from'],
                                                  "%Y-%m-%d")
                    from_date = from_date - relativedelta(months=i)
                    to_date = from_date + relativedelta(months=1)
                    to_date = to_date - relativedelta(days=1)
                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                                        and journal_item.company_id = %(company_ids)s
                                                                        and journal_item.date >= %(from_date)s 
                                                                        and journal_item.date <= %(to_date)s
                                                                        and {states_args}
                                                                        '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '114101',
                                         'code_end': '114999',
                                         'company_ids': self.env.company.id})
                    movement_related = self.env.cr.dictfetchall()
                    movement_related_credit = movement_related[0]['credit'] if \
                        movement_related[0]['credit'] else 0
                    movement_related_debit = movement_related[0]['debit'] if \
                        movement_related[0]['debit'] else 0
                    movement_related_val = round(((
                                                          movement_related_debit - movement_related_credit) * -1),
                                                 2)
                    movement_related_list.append(movement_related_val)
                movement_related_dict = {
                    'id': 'movement_related',
                    'name': 'Movement in due from related parties',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {
                            'name': '',
                            'class': 'number'}]
                }
                movement_related_dict['columns'][0][
                    'name'] = movement_related_list
                return movement_related_dict
            elif options['date_filter'] == 'this_quarter' or options['date_filter'] == 'last_quarter':
                for i in range(0, number_period + 1):
                    from_date = datetime.strptime(options['date']['date_from'],
                                                  "%Y-%m-%d")
                    from_date = from_date + relativedelta(months=-3*i)
                    current_quarter = round((from_date.month - 1) / 3 + 1)
                    from_date = datetime(from_date.year,
                                         3 * current_quarter - 2, 1)
                    to_date = datetime(from_date.year,
                                       3 * current_quarter + 1,
                                       1) + relativedelta(days=-1)
                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                                        and journal_item.company_id = %(company_ids)s
                                                                        and journal_item.date >= %(from_date)s 
                                                                        and journal_item.date <= %(to_date)s
                                                                        and {states_args}
                                                                        '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '114101',
                                         'code_end': '114999',
                                         'company_ids': self.env.company.id})
                    movement_related = self.env.cr.dictfetchall()
                    movement_related_credit = movement_related[0]['credit'] if \
                        movement_related[0]['credit'] else 0
                    movement_related_debit = movement_related[0]['debit'] if \
                        movement_related[0]['debit'] else 0
                    movement_related_val = round(((
                                                          movement_related_debit - movement_related_credit) * -1),
                                                 2)
                    movement_related_list.append(movement_related_val)
                movement_related_dict = {
                    'id': 'movement_related',
                    'name': 'Movement in due from related parties',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {
                            'name': '',
                            'class': 'number'}]
                }
                movement_related_dict['columns'][0][
                    'name'] = movement_related_list
                return movement_related_dict
            elif options['date_filter'] == 'this_year' or options['date_filter'] == 'last_year':
                for i in range(0, number_period + 1):
                    from_date = datetime.strptime(options['date']['date_from'],
                                                  "%Y-%m-%d")
                    from_date = from_date - relativedelta(years=i)
                    to_date = from_date.replace(month=12, day=31)
                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                                            and journal_item.company_id = %(company_ids)s
                                                                            and journal_item.date >= %(from_date)s 
                                                                            and journal_item.date <= %(to_date)s
                                                                            and {states_args}
                                                                            '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '114101',
                                         'code_end': '114999',
                                         'company_ids': self.env.company.id})
                    movement_related = self.env.cr.dictfetchall()
                    movement_related_credit = movement_related[0]['credit'] if \
                        movement_related[0]['credit'] else 0
                    movement_related_debit = movement_related[0]['debit'] if \
                        movement_related[0]['debit'] else 0
                    movement_related_val = round(((
                                                          movement_related_debit - movement_related_credit) * -1),
                                                 2)
                    movement_related_list.append(movement_related_val)
                movement_related_dict = {
                    'id': 'movement_related',
                    'name': 'Movement in due from related parties',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {
                            'name': '',
                            'class': 'number'}]
                }
                movement_related_dict['columns'][0][
                    'name'] = movement_related_list
                return movement_related_dict

        elif options['comparison'][
            'comparison_type'] == 'same_period_last_year':
            if options['date_filter'] == 'this_month' or options[
                'date_filter'] == 'last_month':
                for j in range(0, number_period + 1):
                    from_date = datetime.strptime(options['date']['date_from'],
                                                  "%Y-%m-%d")
                    from_date = from_date - relativedelta(years=j)
                    to_date = from_date + relativedelta(months=1)
                    to_date = to_date - relativedelta(days=1)
                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                                                            and journal_item.company_id = %(company_ids)s
                                                                                            and journal_item.date >= %(from_date)s 
                                                                                            and journal_item.date <= %(to_date)s
                                                                                            and {states_args}
                                                                                            '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '114101',
                                         'code_end': '114999',
                                         'company_ids': self.env.company.id})
                    movement_related = self.env.cr.dictfetchall()
                    movement_related_credit = movement_related[0]['credit'] if \
                        movement_related[0]['credit'] else 0
                    movement_related_debit = movement_related[0]['debit'] if \
                        movement_related[0]['debit'] else 0
                    movement_related_val = round(((
                                                          movement_related_debit - movement_related_credit) * -1),
                                                 2)
                    movement_related_list.append(movement_related_val)
                movement_related_dict = {
                    'id': 'movement_related',
                    'name': 'Movement in due from related parties',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {
                            'name': '',
                            'class': 'number'}]
                }
                movement_related_dict['columns'][0][
                    'name'] = movement_related_list
                return movement_related_dict
            elif options['date_filter'] == 'this_quarter' or options['date_filter'] == 'last_quarter':
                for i in range(0, number_period + 1):
                    from_date = datetime.strptime(options['date']['date_from'],
                                                  "%Y-%m-%d")
                    from_date = from_date + relativedelta(years=-i)
                    current_quarter = round((from_date.month - 1) / 3 + 1)
                    from_date = datetime(from_date.year,
                                         3 * current_quarter - 2, 1)

                    to_date = datetime(from_date.year,
                                       3 * current_quarter + 1,
                                       1) + relativedelta(days=-1)
                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                                        and journal_item.company_id = %(company_ids)s
                                                                        and journal_item.date >= %(from_date)s 
                                                                        and journal_item.date <= %(to_date)s
                                                                        and {states_args}
                                                                        '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '114101',
                                         'code_end': '114999',
                                         'company_ids': self.env.company.id})
                    movement_related = self.env.cr.dictfetchall()
                    movement_related_credit = movement_related[0]['credit'] if \
                        movement_related[0]['credit'] else 0
                    movement_related_debit = movement_related[0]['debit'] if \
                        movement_related[0]['debit'] else 0
                    movement_related_val = round(((
                                                          movement_related_debit - movement_related_credit) * -1),
                                                 2)
                    movement_related_list.append(movement_related_val)
                movement_related_dict = {
                    'id': 'movement_related',
                    'name': 'Movement in due from related parties',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {
                            'name': '',
                            'class': 'number'}]
                }
                movement_related_dict['columns'][0][
                    'name'] = movement_related_list
                return movement_related_dict
            elif options['date_filter'] == 'this_year' or options['date_filter'] == 'last_year':
                for i in range(0, number_period + 1):
                    from_date = datetime.strptime(options['date']['date_from'],
                                                  "%Y-%m-%d")
                    from_date = from_date - relativedelta(years=i)
                    to_date = from_date.replace(month=12, day=31)
                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                                            and journal_item.company_id = %(company_ids)s
                                                                            and journal_item.date >= %(from_date)s 
                                                                            and journal_item.date <= %(to_date)s
                                                                            and {states_args}
                                                                            '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '114101',
                                         'code_end': '114999',
                                         'company_ids': self.env.company.id})
                    movement_related = self.env.cr.dictfetchall()
                    movement_related_credit = movement_related[0]['credit'] if \
                        movement_related[0]['credit'] else 0
                    movement_related_debit = movement_related[0]['debit'] if \
                        movement_related[0]['debit'] else 0
                    movement_related_val = round(((
                                                          movement_related_debit - movement_related_credit) * -1),
                                                 2)
                    movement_related_list.append(movement_related_val)
                movement_related_dict = {
                    'id': 'movement_related',
                    'name': 'Movement in due from related parties',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {
                            'name': '',
                            'class': 'number'}]
                }
                movement_related_dict['columns'][0][
                    'name'] = movement_related_list
                return movement_related_dict
        else:
            self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                    and journal_item.company_id = %(company_ids)s
                                                    and journal_item.date >= %(from_date)s 
                                                    and journal_item.date <= %(to_date)s
                                                    and {states_args}
                                                    '''.format(
                states_args=states_args),
                                {'from_date': options['date']['date_from'],
                                 'to_date': options['date']['date_to'],
                                 'code_start': '114101', 'code_end': '114999',
                                 'company_ids': self.env.company.id})
            movement_related = self.env.cr.dictfetchall()
            movement_related_credit = movement_related[0]['credit'] if \
                movement_related[0]['credit'] else 0
            movement_related_debit = movement_related[0]['debit'] if \
                movement_related[0]['debit'] else 0
            movement_related_val = round(((
                                                  movement_related_debit - movement_related_credit) * -1),
                                         2)
            movement_related_list.append(movement_related_val)
            movement_related_dict = {
                'id': 'movement_related',
                'name': 'Movement in due from related parties',
                'level': 2,
                'class': 'cash_flow_line_val_tr',
                'columns': [
                    {
                        'name': '',
                        'class': 'number'}]
            }
            movement_related_dict['columns'][0]['name'] = movement_related_list
            return movement_related_dict

    def get_movement_trade_payable_account_sum(self, query, options,
                                               states_args):
        self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                        and journal_item.company_id in (%(company_ids)s)
                                        and journal_item.date >= %(from_date)s 
                                        and journal_item.date <= %(to_date)s
                                        and {states_args}
                                        '''.format(states_args=states_args),
                            {'from_date': options['date']['date_from'],
                             'to_date': options['date']['date_to'],
                             'code_start': '213101', 'code_end': '213399',
                             'company_ids': self.env.company.id})
        movement_trade_payable_account = self.env.cr.dictfetchall()
        movement_trade_payable_account_credit = \
            movement_trade_payable_account[0]['credit'] if \
                movement_trade_payable_account[0]['credit'] else 0
        movement_trade_payable_account_debit = \
            movement_trade_payable_account[0]['debit'] if \
                movement_trade_payable_account[0]['debit'] else 0

        return movement_trade_payable_account_debit - movement_trade_payable_account_credit

    def get_movement_trade_payable_account1_sum(self, query, options,
                                                states_args):
        self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                        and journal_item.company_id in (%(company_ids)s)
                                        and journal_item.date >= %(from_date)s 
                                        and journal_item.date <= %(to_date)s
                                        and {states_args}
                                        '''.format(states_args=states_args),
                            {'from_date': options['date']['date_from'],
                             'to_date': options['date']['date_to'],
                             'code_start': '213501', 'code_end': '213599',
                             'company_ids': self.env.company.id})
        movement_trade_payable_account1 = self.env.cr.dictfetchall()
        movement_trade_payable_account1_credit = \
            movement_trade_payable_account1[0]['credit'] if \
                movement_trade_payable_account1[0]['credit'] else 0
        movement_trade_payable_account1_debit = \
            movement_trade_payable_account1[0]['debit'] if \
                movement_trade_payable_account1[0]['debit'] else 0

        return movement_trade_payable_account1_debit - movement_trade_payable_account1_credit

    def get_movement_trade_payable_account2_sum(self, query, options,
                                                states_args):
        self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                        and journal_item.company_id in (%(company_ids)s)
                                        and journal_item.date >= %(from_date)s 
                                        and journal_item.date <= %(to_date)s
                                        and {states_args}
                                        '''.format(states_args=states_args),
                            {'from_date': options['date']['date_from'],
                             'to_date': options['date']['date_to'],
                             'code_start': '218101', 'code_end': '218999',
                             'company_ids': self.env.company.id})
        movement_trade_payable_account2 = self.env.cr.dictfetchall()
        movement_trade_payable_account2_credit = \
            movement_trade_payable_account2[0]['credit'] if \
                movement_trade_payable_account2[0]['credit'] else 0
        movement_trade_payable_account2_debit = \
            movement_trade_payable_account2[0]['debit'] if \
                movement_trade_payable_account2[0]['debit'] else 0

        return movement_trade_payable_account2_debit - movement_trade_payable_account2_credit

    def sub_movement_trade_payable_account3_sum(self, query, options,
                                                states_args):
        self.env.cr.execute(query + '''where account.code = %(account_code)s
                                                and journal_item.company_id in (%(company_ids)s)
                                                and journal_item.date >= %(from_date)s 
                                                and journal_item.date <= %(to_date)s
                                                and {states_args}
                                                '''.format(
            states_args=states_args),
                            {'from_date': options['date']['date_from'],
                             'to_date': options['date']['date_to'],
                             'account_code': '581103',
                             'company_ids': self.env.company.id})
        sub_movement_trade = self.env.cr.dictfetchall()
        sub_movement_trade_credit = sub_movement_trade[0]['credit'] if \
            sub_movement_trade[0]['credit'] else 0
        sub_movement_trade_debit = sub_movement_trade[0]['debit'] if \
            sub_movement_trade[0]['debit'] else 0
        return sub_movement_trade_debit - sub_movement_trade_credit

    def sub_movement_trade_payable_account3_sum1(self, query, options,
                                                 states_args):
        self.env.cr.execute(query + '''where account.code = %(account_code)s
                                                        and journal_item.company_id in (%(company_ids)s)
                                                        and journal_item.date >= %(from_date)s 
                                                        and journal_item.date <= %(to_date)s
                                                        and {states_args}
                                                        '''.format(
            states_args=states_args),
                            {'from_date': options['date']['date_from'],
                             'to_date': options['date']['date_to'],
                             'account_code': '213403',
                             'company_ids': self.env.company.id})
        sub_movement_trade1 = self.env.cr.dictfetchall()
        sub_movement_trade1_credit = sub_movement_trade1[0]['credit'] if \
            sub_movement_trade1[0]['credit'] else 0
        return sub_movement_trade1_credit

    def get_movement_trade_payable_dict(self, query, options, states_args,
                                        number_period):
        movement_trade_payable_list = []
        movement_trade_payable_dict = {}
        if options['comparison']['comparison_type'] == 'previous_period':
            if options['date_filter'] == 'this_month' or options[
                'date_filter'] == 'last_month':
                for i in range(0, number_period + 1):
                    from_date = datetime.strptime(options['date']['date_from'],
                                                  "%Y-%m-%d")
                    from_date = from_date - relativedelta(months=i)
                    to_date = from_date + relativedelta(months=1)
                    to_date = to_date - relativedelta(days=1)

                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                                    and journal_item.company_id = %(company_ids)s
                                                                    and journal_item.date >= %(from_date)s 
                                                                    and journal_item.date <= %(to_date)s
                                                                    and {states_args}
                                                                    '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '211101',
                                         'code_end': '211402',
                                         'company_ids': self.env.company.id})
                    movement_trade_payable = self.env.cr.dictfetchall()
                    movement_trade_payable_credit = movement_trade_payable[0][
                        'credit'] if \
                        movement_trade_payable[0]['credit'] else 0
                    movement_trade_payable_debit = movement_trade_payable[0][
                        'debit'] if \
                        movement_trade_payable[0]['debit'] else 0

                    movement_trade_payable_sum = movement_trade_payable_debit - movement_trade_payable_credit

                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                            and journal_item.company_id in (%(company_ids)s)
                                                            and journal_item.date >= %(from_date)s 
                                                            and journal_item.date <= %(to_date)s
                                                            and {states_args}
                                                            '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '213101',
                                         'code_end': '213399',
                                         'company_ids': self.env.company.id})
                    movement_trade_payable_account = self.env.cr.dictfetchall()
                    movement_trade_payable_account_credit = \
                        movement_trade_payable_account[0]['credit'] if \
                            movement_trade_payable_account[0]['credit'] else 0
                    movement_trade_payable_account_debit = \
                        movement_trade_payable_account[0]['debit'] if \
                            movement_trade_payable_account[0]['debit'] else 0

                    movement_trade_payable_account_sum = movement_trade_payable_account_debit - movement_trade_payable_account_credit

                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                    and journal_item.company_id in (%(company_ids)s)
                                                    and journal_item.date >= %(from_date)s 
                                                    and journal_item.date <= %(to_date)s
                                                    and {states_args}
                                                    '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '213501',
                                         'code_end': '213599',
                                         'company_ids': self.env.company.id})
                    movement_trade_payable_account1 = self.env.cr.dictfetchall()
                    movement_trade_payable_account1_credit = \
                        movement_trade_payable_account1[0]['credit'] if \
                            movement_trade_payable_account1[0]['credit'] else 0
                    movement_trade_payable_account1_debit = \
                        movement_trade_payable_account1[0]['debit'] if \
                            movement_trade_payable_account1[0]['debit'] else 0

                    movement_trade_payable_account1_sum = movement_trade_payable_account1_debit - movement_trade_payable_account1_credit

                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                    and journal_item.company_id in (%(company_ids)s)
                                                    and journal_item.date >= %(from_date)s 
                                                    and journal_item.date <= %(to_date)s
                                                    and {states_args}
                                                    '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '218101',
                                         'code_end': '218999',
                                         'company_ids': self.env.company.id})
                    movement_trade_payable_account2 = self.env.cr.dictfetchall()
                    movement_trade_payable_account2_credit = \
                        movement_trade_payable_account2[0]['credit'] if \
                            movement_trade_payable_account2[0]['credit'] else 0
                    movement_trade_payable_account2_debit = \
                        movement_trade_payable_account2[0]['debit'] if \
                            movement_trade_payable_account2[0]['debit'] else 0

                    movement_trade_payable_account2_sum = movement_trade_payable_account2_debit - movement_trade_payable_account2_credit

                    self.env.cr.execute(query + '''where account.code = %(account_code)s
                                                                    and journal_item.company_id in (%(company_ids)s)
                                                                    and journal_item.date >= %(from_date)s 
                                                                    and journal_item.date <= %(to_date)s
                                                                    and {states_args}
                                                                    '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'account_code': '581103',
                                         'company_ids': self.env.company.id})
                    sub_movement_trade = self.env.cr.dictfetchall()
                    sub_movement_trade_credit = sub_movement_trade[0][
                        'credit'] if \
                        sub_movement_trade[0]['credit'] else 0
                    sub_movement_trade_debit = sub_movement_trade[0]['debit'] if \
                        sub_movement_trade[0]['debit'] else 0
                    movement_trade_payable_account3_sum = sub_movement_trade_debit - sub_movement_trade_credit

                    self.env.cr.execute(query + '''where account.code = %(account_code)s
                                                                            and journal_item.company_id in (%(company_ids)s)
                                                                            and journal_item.date >= %(from_date)s 
                                                                            and journal_item.date <= %(to_date)s
                                                                            and {states_args}
                                                                            '''.format(
                        states_args=states_args),
                                        {'from_date': options['date'][
                                            'date_from'],
                                         'to_date': options['date']['date_to'],
                                         'account_code': '213403',
                                         'company_ids': self.env.company.id})
                    sub_movement_trade1 = self.env.cr.dictfetchall()
                    movement_trade_payable_account4_sum = \
                        sub_movement_trade1[0][
                            'credit'] if \
                            sub_movement_trade1[0]['credit'] else 0

                    movement_trade_payable_val = round((((
                                                                 movement_trade_payable_sum + movement_trade_payable_account_sum + movement_trade_payable_account1_sum + movement_trade_payable_account2_sum) * -1) - movement_trade_payable_account3_sum) + movement_trade_payable_account4_sum,
                                                       2)
                    movement_trade_payable_list.append(
                        movement_trade_payable_val)
                movement_trade_payable_dict = {
                    'id': 'movement_trade_payable',
                    'name': 'Movement trade and other payables',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {
                            'name': '',
                            'class': 'number'}]
                }
                movement_trade_payable_dict['columns'][0][
                    'name'] = movement_trade_payable_list
            elif options['date_filter'] == 'this_quarter' or options['date_filter'] == 'last_quarter':
                for i in range(0, number_period + 1):
                    from_date = datetime.strptime(options['date']['date_from'],
                                                  "%Y-%m-%d")
                    from_date = from_date + relativedelta(months=-3 * i)
                    current_quarter = round((from_date.month - 1) / 3 + 1)
                    from_date = datetime(from_date.year,
                                         3 * current_quarter - 2, 1)
                    to_date = datetime(from_date.year,
                                       3 * current_quarter + 1,
                                       1) + relativedelta(days=-1)
                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                                                        and journal_item.company_id = %(company_ids)s
                                                                                        and journal_item.date >= %(from_date)s 
                                                                                        and journal_item.date <= %(to_date)s
                                                                                        and {states_args}
                                                                                        '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '211101',
                                         'code_end': '211402',
                                         'company_ids': self.env.company.id})
                    movement_trade_payable = self.env.cr.dictfetchall()
                    movement_trade_payable_credit = movement_trade_payable[0][
                        'credit'] if \
                        movement_trade_payable[0]['credit'] else 0
                    movement_trade_payable_debit = movement_trade_payable[0][
                        'debit'] if \
                        movement_trade_payable[0]['debit'] else 0

                    movement_trade_payable_sum = movement_trade_payable_debit - movement_trade_payable_credit

                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                                                and journal_item.company_id in (%(company_ids)s)
                                                                                and journal_item.date >= %(from_date)s 
                                                                                and journal_item.date <= %(to_date)s
                                                                                and {states_args}
                                                                                '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '213101',
                                         'code_end': '213399',
                                         'company_ids': self.env.company.id})
                    movement_trade_payable_account = self.env.cr.dictfetchall()
                    movement_trade_payable_account_credit = \
                        movement_trade_payable_account[0]['credit'] if \
                            movement_trade_payable_account[0]['credit'] else 0
                    movement_trade_payable_account_debit = \
                        movement_trade_payable_account[0]['debit'] if \
                            movement_trade_payable_account[0]['debit'] else 0

                    movement_trade_payable_account_sum = movement_trade_payable_account_debit - movement_trade_payable_account_credit

                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                                        and journal_item.company_id in (%(company_ids)s)
                                                                        and journal_item.date >= %(from_date)s 
                                                                        and journal_item.date <= %(to_date)s
                                                                        and {states_args}
                                                                        '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '213501',
                                         'code_end': '213599',
                                         'company_ids': self.env.company.id})
                    movement_trade_payable_account1 = self.env.cr.dictfetchall()
                    movement_trade_payable_account1_credit = \
                        movement_trade_payable_account1[0]['credit'] if \
                            movement_trade_payable_account1[0]['credit'] else 0
                    movement_trade_payable_account1_debit = \
                        movement_trade_payable_account1[0]['debit'] if \
                            movement_trade_payable_account1[0]['debit'] else 0

                    movement_trade_payable_account1_sum = movement_trade_payable_account1_debit - movement_trade_payable_account1_credit

                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                                        and journal_item.company_id in (%(company_ids)s)
                                                                        and journal_item.date >= %(from_date)s 
                                                                        and journal_item.date <= %(to_date)s
                                                                        and {states_args}
                                                                        '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '218101',
                                         'code_end': '218999',
                                         'company_ids': self.env.company.id})
                    movement_trade_payable_account2 = self.env.cr.dictfetchall()
                    movement_trade_payable_account2_credit = \
                        movement_trade_payable_account2[0]['credit'] if \
                            movement_trade_payable_account2[0]['credit'] else 0
                    movement_trade_payable_account2_debit = \
                        movement_trade_payable_account2[0]['debit'] if \
                            movement_trade_payable_account2[0]['debit'] else 0

                    movement_trade_payable_account2_sum = movement_trade_payable_account2_debit - movement_trade_payable_account2_credit

                    self.env.cr.execute(query + '''where account.code = %(account_code)s
                                                                                        and journal_item.company_id in (%(company_ids)s)
                                                                                        and journal_item.date >= %(from_date)s 
                                                                                        and journal_item.date <= %(to_date)s
                                                                                        and {states_args}
                                                                                        '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'account_code': '581103',
                                         'company_ids': self.env.company.id})
                    sub_movement_trade = self.env.cr.dictfetchall()
                    sub_movement_trade_credit = sub_movement_trade[0][
                        'credit'] if \
                        sub_movement_trade[0]['credit'] else 0
                    sub_movement_trade_debit = sub_movement_trade[0]['debit'] if \
                        sub_movement_trade[0]['debit'] else 0
                    movement_trade_payable_account3_sum = sub_movement_trade_debit - sub_movement_trade_credit

                    self.env.cr.execute(query + '''where account.code = %(account_code)s
                                                                                                and journal_item.company_id in (%(company_ids)s)
                                                                                                and journal_item.date >= %(from_date)s 
                                                                                                and journal_item.date <= %(to_date)s
                                                                                                and {states_args}
                                                                                                '''.format(
                        states_args=states_args),
                                        {'from_date': options['date'][
                                            'date_from'],
                                         'to_date': options['date']['date_to'],
                                         'account_code': '213403',
                                         'company_ids': self.env.company.id})
                    sub_movement_trade1 = self.env.cr.dictfetchall()
                    movement_trade_payable_account4_sum = \
                        sub_movement_trade1[0][
                            'credit'] if \
                            sub_movement_trade1[0]['credit'] else 0

                    movement_trade_payable_val = round((((
                                                                 movement_trade_payable_sum + movement_trade_payable_account_sum + movement_trade_payable_account1_sum + movement_trade_payable_account2_sum) * -1) - movement_trade_payable_account3_sum) + movement_trade_payable_account4_sum,
                                                       2)
                    movement_trade_payable_list.append(
                        movement_trade_payable_val)
                movement_trade_payable_dict = {
                    'id': 'movement_trade_payable',
                    'name': 'Movement trade and other payables',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {
                            'name': '',
                            'class': 'number'}]
                }
                movement_trade_payable_dict['columns'][0][
                    'name'] = movement_trade_payable_list
            elif options['date_filter'] == 'this_year' or options['date_filter'] == 'last_year':
                for i in range(0, number_period + 1):
                    from_date = datetime.strptime(options['date']['date_from'],
                                                  "%Y-%m-%d")
                    from_date = from_date - relativedelta(years=i)
                    to_date = from_date.replace(month=12, day=31)
                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                                            and journal_item.company_id = %(company_ids)s
                                                                            and journal_item.date >= %(from_date)s 
                                                                            and journal_item.date <= %(to_date)s
                                                                            and {states_args}
                                                                            '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '211101',
                                         'code_end': '211402',
                                         'company_ids': self.env.company.id})
                    movement_trade_payable = self.env.cr.dictfetchall()
                    movement_trade_payable_credit = movement_trade_payable[0][
                        'credit'] if \
                        movement_trade_payable[0]['credit'] else 0
                    movement_trade_payable_debit = movement_trade_payable[0][
                        'debit'] if \
                        movement_trade_payable[0]['debit'] else 0

                    movement_trade_payable_sum = movement_trade_payable_debit - movement_trade_payable_credit

                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                                    and journal_item.company_id in (%(company_ids)s)
                                                                    and journal_item.date >= %(from_date)s 
                                                                    and journal_item.date <= %(to_date)s
                                                                    and {states_args}
                                                                    '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '213101',
                                         'code_end': '213399',
                                         'company_ids': self.env.company.id})
                    movement_trade_payable_account = self.env.cr.dictfetchall()
                    movement_trade_payable_account_credit = \
                        movement_trade_payable_account[0]['credit'] if \
                            movement_trade_payable_account[0]['credit'] else 0
                    movement_trade_payable_account_debit = \
                        movement_trade_payable_account[0]['debit'] if \
                            movement_trade_payable_account[0]['debit'] else 0

                    movement_trade_payable_account_sum = movement_trade_payable_account_debit - movement_trade_payable_account_credit

                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                            and journal_item.company_id in (%(company_ids)s)
                                                            and journal_item.date >= %(from_date)s 
                                                            and journal_item.date <= %(to_date)s
                                                            and {states_args}
                                                            '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '213501',
                                         'code_end': '213599',
                                         'company_ids': self.env.company.id})
                    movement_trade_payable_account1 = self.env.cr.dictfetchall()
                    movement_trade_payable_account1_credit = \
                        movement_trade_payable_account1[0]['credit'] if \
                            movement_trade_payable_account1[0]['credit'] else 0
                    movement_trade_payable_account1_debit = \
                        movement_trade_payable_account1[0]['debit'] if \
                            movement_trade_payable_account1[0]['debit'] else 0

                    movement_trade_payable_account1_sum = movement_trade_payable_account1_debit - movement_trade_payable_account1_credit

                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                            and journal_item.company_id in (%(company_ids)s)
                                                            and journal_item.date >= %(from_date)s 
                                                            and journal_item.date <= %(to_date)s
                                                            and {states_args}
                                                            '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '218101',
                                         'code_end': '218999',
                                         'company_ids': self.env.company.id})
                    movement_trade_payable_account2 = self.env.cr.dictfetchall()
                    movement_trade_payable_account2_credit = \
                        movement_trade_payable_account2[0]['credit'] if \
                            movement_trade_payable_account2[0]['credit'] else 0
                    movement_trade_payable_account2_debit = \
                        movement_trade_payable_account2[0]['debit'] if \
                            movement_trade_payable_account2[0]['debit'] else 0

                    movement_trade_payable_account2_sum = movement_trade_payable_account2_debit - movement_trade_payable_account2_credit

                    self.env.cr.execute(query + '''where account.code = %(account_code)s
                                                                            and journal_item.company_id in (%(company_ids)s)
                                                                            and journal_item.date >= %(from_date)s 
                                                                            and journal_item.date <= %(to_date)s
                                                                            and {states_args}
                                                                            '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'account_code': '581103',
                                         'company_ids': self.env.company.id})
                    sub_movement_trade = self.env.cr.dictfetchall()
                    sub_movement_trade_credit = sub_movement_trade[0][
                        'credit'] if \
                        sub_movement_trade[0]['credit'] else 0
                    sub_movement_trade_debit = sub_movement_trade[0]['debit'] if \
                        sub_movement_trade[0]['debit'] else 0
                    movement_trade_payable_account3_sum = sub_movement_trade_debit - sub_movement_trade_credit

                    self.env.cr.execute(query + '''where account.code = %(account_code)s
                                                                                    and journal_item.company_id in (%(company_ids)s)
                                                                                    and journal_item.date >= %(from_date)s 
                                                                                    and journal_item.date <= %(to_date)s
                                                                                    and {states_args}
                                                                                    '''.format(
                        states_args=states_args),
                                        {'from_date': options['date'][
                                            'date_from'],
                                         'to_date': options['date']['date_to'],
                                         'account_code': '213403',
                                         'company_ids': self.env.company.id})
                    sub_movement_trade1 = self.env.cr.dictfetchall()
                    movement_trade_payable_account4_sum = \
                        sub_movement_trade1[0][
                            'credit'] if \
                            sub_movement_trade1[0]['credit'] else 0

                    movement_trade_payable_val = round((((
                                                                 movement_trade_payable_sum + movement_trade_payable_account_sum + movement_trade_payable_account1_sum + movement_trade_payable_account2_sum) * -1) - movement_trade_payable_account3_sum) + movement_trade_payable_account4_sum,
                                                       2)
                    movement_trade_payable_list.append(
                        movement_trade_payable_val)
                movement_trade_payable_dict = {
                    'id': 'movement_trade_payable',
                    'name': 'Movement trade and other payables',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {
                            'name': '',
                            'class': 'number'}]
                }
                movement_trade_payable_dict['columns'][0][
                    'name'] = movement_trade_payable_list
            elif options['date_filter'] == 'this_quarter' or options[
                'date_filter'] == 'last_quarter':
                for i in range(0, number_period + 1):
                    from_date = datetime.strptime(options['date']['date_from'],
                                                  "%Y-%m-%d")
                    from_date = from_date + relativedelta(months=-3 * i)
                    current_quarter = round((from_date.month - 1) / 3 + 1)
                    from_date = datetime(from_date.year,
                                         3 * current_quarter - 2, 1)
                    to_date = datetime(from_date.year,
                                       3 * current_quarter + 1,
                                       1) + relativedelta(days=-1)
                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                                                                and journal_item.company_id = %(company_ids)s
                                                                                                and journal_item.date >= %(from_date)s 
                                                                                                and journal_item.date <= %(to_date)s
                                                                                                and {states_args}
                                                                                                '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '211101',
                                         'code_end': '211402',
                                         'company_ids': self.env.company.id})
                    movement_trade_payable = self.env.cr.dictfetchall()
                    movement_trade_payable_credit = movement_trade_payable[0][
                        'credit'] if \
                        movement_trade_payable[0]['credit'] else 0
                    movement_trade_payable_debit = movement_trade_payable[0][
                        'debit'] if \
                        movement_trade_payable[0]['debit'] else 0

                    movement_trade_payable_sum = movement_trade_payable_debit - movement_trade_payable_credit

                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                                                        and journal_item.company_id in (%(company_ids)s)
                                                                                        and journal_item.date >= %(from_date)s 
                                                                                        and journal_item.date <= %(to_date)s
                                                                                        and {states_args}
                                                                                        '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '213101',
                                         'code_end': '213399',
                                         'company_ids': self.env.company.id})
                    movement_trade_payable_account = self.env.cr.dictfetchall()
                    movement_trade_payable_account_credit = \
                        movement_trade_payable_account[0]['credit'] if \
                            movement_trade_payable_account[0]['credit'] else 0
                    movement_trade_payable_account_debit = \
                        movement_trade_payable_account[0]['debit'] if \
                            movement_trade_payable_account[0]['debit'] else 0

                    movement_trade_payable_account_sum = movement_trade_payable_account_debit - movement_trade_payable_account_credit

                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                                                and journal_item.company_id in (%(company_ids)s)
                                                                                and journal_item.date >= %(from_date)s 
                                                                                and journal_item.date <= %(to_date)s
                                                                                and {states_args}
                                                                                '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '213501',
                                         'code_end': '213599',
                                         'company_ids': self.env.company.id})
                    movement_trade_payable_account1 = self.env.cr.dictfetchall()
                    movement_trade_payable_account1_credit = \
                        movement_trade_payable_account1[0]['credit'] if \
                            movement_trade_payable_account1[0]['credit'] else 0
                    movement_trade_payable_account1_debit = \
                        movement_trade_payable_account1[0]['debit'] if \
                            movement_trade_payable_account1[0]['debit'] else 0

                    movement_trade_payable_account1_sum = movement_trade_payable_account1_debit - movement_trade_payable_account1_credit

                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                                                and journal_item.company_id in (%(company_ids)s)
                                                                                and journal_item.date >= %(from_date)s 
                                                                                and journal_item.date <= %(to_date)s
                                                                                and {states_args}
                                                                                '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '218101',
                                         'code_end': '218999',
                                         'company_ids': self.env.company.id})
                    movement_trade_payable_account2 = self.env.cr.dictfetchall()
                    movement_trade_payable_account2_credit = \
                        movement_trade_payable_account2[0]['credit'] if \
                            movement_trade_payable_account2[0]['credit'] else 0
                    movement_trade_payable_account2_debit = \
                        movement_trade_payable_account2[0]['debit'] if \
                            movement_trade_payable_account2[0]['debit'] else 0

                    movement_trade_payable_account2_sum = movement_trade_payable_account2_debit - movement_trade_payable_account2_credit

                    self.env.cr.execute(query + '''where account.code = %(account_code)s
                                                                                                and journal_item.company_id in (%(company_ids)s)
                                                                                                and journal_item.date >= %(from_date)s 
                                                                                                and journal_item.date <= %(to_date)s
                                                                                                and {states_args}
                                                                                                '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'account_code': '581103',
                                         'company_ids': self.env.company.id})
                    sub_movement_trade = self.env.cr.dictfetchall()
                    sub_movement_trade_credit = sub_movement_trade[0][
                        'credit'] if \
                        sub_movement_trade[0]['credit'] else 0
                    sub_movement_trade_debit = sub_movement_trade[0]['debit'] if \
                        sub_movement_trade[0]['debit'] else 0
                    movement_trade_payable_account3_sum = sub_movement_trade_debit - sub_movement_trade_credit
                    self.env.cr.execute(query + '''where account.code = %(account_code)s
                                                                                                        and journal_item.company_id in (%(company_ids)s)
                                                                                                        and journal_item.date >= %(from_date)s 
                                                                                                        and journal_item.date <= %(to_date)s
                                                                                                        and {states_args}
                                                                                                        '''.format(
                        states_args=states_args),
                                        {'from_date': options['date'][
                                            'date_from'],
                                         'to_date': options['date']['date_to'],
                                         'account_code': '213403',
                                         'company_ids': self.env.company.id})
                    sub_movement_trade1 = self.env.cr.dictfetchall()
                    movement_trade_payable_account4_sum = \
                        sub_movement_trade1[0][
                            'credit'] if \
                            sub_movement_trade1[0]['credit'] else 0

                    movement_trade_payable_val = round((((
                                                                 movement_trade_payable_sum + movement_trade_payable_account_sum + movement_trade_payable_account1_sum + movement_trade_payable_account2_sum) * -1) - movement_trade_payable_account3_sum) + movement_trade_payable_account4_sum,
                                                       2)
                    movement_trade_payable_list.append(
                        movement_trade_payable_val)
                movement_trade_payable_dict = {
                    'id': 'movement_trade_payable',
                    'name': 'Movement trade and other payables',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {
                            'name': '',
                            'class': 'number'}]
                }
                movement_trade_payable_dict['columns'][0][
                    'name'] = movement_trade_payable_list

        elif options['comparison'][
            'comparison_type'] == 'same_period_last_year':
            if options['date_filter'] == 'this_month' or options[
                'date_filter'] == 'last_month':
                for j in range(0, number_period + 1):
                    from_date = datetime.strptime(options['date']['date_from'],
                                                  "%Y-%m-%d")
                    from_date = from_date - relativedelta(years=j)
                    to_date = from_date + relativedelta(months=1)
                    to_date = to_date - relativedelta(days=1)
                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                                        and journal_item.company_id = %(company_ids)s
                                                                        and journal_item.date >= %(from_date)s 
                                                                        and journal_item.date <= %(to_date)s
                                                                        and {states_args}
                                                                        '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '211101',
                                         'code_end': '211402',
                                         'company_ids': self.env.company.id})
                    movement_trade_payable = self.env.cr.dictfetchall()
                    movement_trade_payable_credit = movement_trade_payable[0][
                        'credit'] if \
                        movement_trade_payable[0]['credit'] else 0
                    movement_trade_payable_debit = movement_trade_payable[0][
                        'debit'] if \
                        movement_trade_payable[0]['debit'] else 0

                    movement_trade_payable_sum = movement_trade_payable_debit - movement_trade_payable_credit

                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                                and journal_item.company_id in (%(company_ids)s)
                                                                and journal_item.date >= %(from_date)s 
                                                                and journal_item.date <= %(to_date)s
                                                                and {states_args}
                                                                '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '213101',
                                         'code_end': '213399',
                                         'company_ids': self.env.company.id})
                    movement_trade_payable_account = self.env.cr.dictfetchall()
                    movement_trade_payable_account_credit = \
                        movement_trade_payable_account[0]['credit'] if \
                            movement_trade_payable_account[0]['credit'] else 0
                    movement_trade_payable_account_debit = \
                        movement_trade_payable_account[0]['debit'] if \
                            movement_trade_payable_account[0]['debit'] else 0

                    movement_trade_payable_account_sum = movement_trade_payable_account_debit - movement_trade_payable_account_credit

                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                        and journal_item.company_id in (%(company_ids)s)
                                                        and journal_item.date >= %(from_date)s 
                                                        and journal_item.date <= %(to_date)s
                                                        and {states_args}
                                                        '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '213501',
                                         'code_end': '213599',
                                         'company_ids': self.env.company.id})
                    movement_trade_payable_account1 = self.env.cr.dictfetchall()
                    movement_trade_payable_account1_credit = \
                        movement_trade_payable_account1[0]['credit'] if \
                            movement_trade_payable_account1[0]['credit'] else 0
                    movement_trade_payable_account1_debit = \
                        movement_trade_payable_account1[0]['debit'] if \
                            movement_trade_payable_account1[0]['debit'] else 0

                    movement_trade_payable_account1_sum = movement_trade_payable_account1_debit - movement_trade_payable_account1_credit

                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                        and journal_item.company_id in (%(company_ids)s)
                                                        and journal_item.date >= %(from_date)s 
                                                        and journal_item.date <= %(to_date)s
                                                        and {states_args}
                                                        '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '218101',
                                         'code_end': '218999',
                                         'company_ids': self.env.company.id})
                    movement_trade_payable_account2 = self.env.cr.dictfetchall()
                    movement_trade_payable_account2_credit = \
                        movement_trade_payable_account2[0]['credit'] if \
                            movement_trade_payable_account2[0]['credit'] else 0
                    movement_trade_payable_account2_debit = \
                        movement_trade_payable_account2[0]['debit'] if \
                            movement_trade_payable_account2[0]['debit'] else 0

                    movement_trade_payable_account2_sum = movement_trade_payable_account2_debit - movement_trade_payable_account2_credit

                    self.env.cr.execute(query + '''where account.code = %(account_code)s
                                                                        and journal_item.company_id in (%(company_ids)s)
                                                                        and journal_item.date >= %(from_date)s 
                                                                        and journal_item.date <= %(to_date)s
                                                                        and {states_args}
                                                                        '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'account_code': '581103',
                                         'company_ids': self.env.company.id})
                    sub_movement_trade = self.env.cr.dictfetchall()
                    sub_movement_trade_credit = sub_movement_trade[0][
                        'credit'] if \
                        sub_movement_trade[0]['credit'] else 0
                    sub_movement_trade_debit = sub_movement_trade[0]['debit'] if \
                        sub_movement_trade[0]['debit'] else 0
                    movement_trade_payable_account3_sum = sub_movement_trade_debit - sub_movement_trade_credit

                    self.env.cr.execute(query + '''where account.code = %(account_code)s
                                                                                and journal_item.company_id in (%(company_ids)s)
                                                                                and journal_item.date >= %(from_date)s 
                                                                                and journal_item.date <= %(to_date)s
                                                                                and {states_args}
                                                                                '''.format(
                        states_args=states_args),
                                        {'from_date': options['date'][
                                            'date_from'],
                                         'to_date': options['date']['date_to'],
                                         'account_code': '213403',
                                         'company_ids': self.env.company.id})
                    sub_movement_trade1 = self.env.cr.dictfetchall()
                    movement_trade_payable_account4_sum = \
                        sub_movement_trade1[0][
                            'credit'] if \
                            sub_movement_trade1[0]['credit'] else 0

                    movement_trade_payable_val = round((((
                                                                 movement_trade_payable_sum + movement_trade_payable_account_sum + movement_trade_payable_account1_sum + movement_trade_payable_account2_sum) * -1) - movement_trade_payable_account3_sum) + movement_trade_payable_account4_sum,
                                                       2)
                    movement_trade_payable_list.append(
                        movement_trade_payable_val)
                movement_trade_payable_dict = {
                    'id': 'movement_trade_payable',
                    'name': 'Movement trade and other payables',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {
                            'name': '',
                            'class': 'number'}]
                }
                movement_trade_payable_dict['columns'][0][
                    'name'] = movement_trade_payable_list
            elif options['date_filter'] == 'this_quarter' or options['date_filter'] == 'last_quarter':
                for i in range(0, number_period + 1):
                    from_date = datetime.strptime(options['date']['date_from'],
                                                  "%Y-%m-%d")
                    from_date = from_date + relativedelta(years=-i)
                    current_quarter = round((from_date.month - 1) / 3 + 1)
                    from_date = datetime(from_date.year,
                                         3 * current_quarter - 2, 1)
                    to_date = datetime(from_date.year,
                                       3 * current_quarter + 1,
                                       1) + relativedelta(days=-1)
                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                                                            and journal_item.company_id = %(company_ids)s
                                                                                            and journal_item.date >= %(from_date)s 
                                                                                            and journal_item.date <= %(to_date)s
                                                                                            and {states_args}
                                                                                            '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '211101',
                                         'code_end': '211402',
                                         'company_ids': self.env.company.id})
                    movement_trade_payable = self.env.cr.dictfetchall()
                    movement_trade_payable_credit = movement_trade_payable[0][
                        'credit'] if \
                        movement_trade_payable[0]['credit'] else 0
                    movement_trade_payable_debit = movement_trade_payable[0][
                        'debit'] if \
                        movement_trade_payable[0]['debit'] else 0

                    movement_trade_payable_sum = movement_trade_payable_debit - movement_trade_payable_credit

                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                                                    and journal_item.company_id in (%(company_ids)s)
                                                                                    and journal_item.date >= %(from_date)s 
                                                                                    and journal_item.date <= %(to_date)s
                                                                                    and {states_args}
                                                                                    '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '213101',
                                         'code_end': '213399',
                                         'company_ids': self.env.company.id})
                    movement_trade_payable_account = self.env.cr.dictfetchall()
                    movement_trade_payable_account_credit = \
                        movement_trade_payable_account[0]['credit'] if \
                            movement_trade_payable_account[0]['credit'] else 0
                    movement_trade_payable_account_debit = \
                        movement_trade_payable_account[0]['debit'] if \
                            movement_trade_payable_account[0]['debit'] else 0

                    movement_trade_payable_account_sum = movement_trade_payable_account_debit - movement_trade_payable_account_credit

                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                                            and journal_item.company_id in (%(company_ids)s)
                                                                            and journal_item.date >= %(from_date)s 
                                                                            and journal_item.date <= %(to_date)s
                                                                            and {states_args}
                                                                            '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '213501',
                                         'code_end': '213599',
                                         'company_ids': self.env.company.id})
                    movement_trade_payable_account1 = self.env.cr.dictfetchall()
                    movement_trade_payable_account1_credit = \
                        movement_trade_payable_account1[0]['credit'] if \
                            movement_trade_payable_account1[0]['credit'] else 0
                    movement_trade_payable_account1_debit = \
                        movement_trade_payable_account1[0]['debit'] if \
                            movement_trade_payable_account1[0]['debit'] else 0

                    movement_trade_payable_account1_sum = movement_trade_payable_account1_debit - movement_trade_payable_account1_credit

                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                                            and journal_item.company_id in (%(company_ids)s)
                                                                            and journal_item.date >= %(from_date)s 
                                                                            and journal_item.date <= %(to_date)s
                                                                            and {states_args}
                                                                            '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '218101',
                                         'code_end': '218999',
                                         'company_ids': self.env.company.id})
                    movement_trade_payable_account2 = self.env.cr.dictfetchall()
                    movement_trade_payable_account2_credit = \
                        movement_trade_payable_account2[0]['credit'] if \
                            movement_trade_payable_account2[0]['credit'] else 0
                    movement_trade_payable_account2_debit = \
                        movement_trade_payable_account2[0]['debit'] if \
                            movement_trade_payable_account2[0]['debit'] else 0

                    movement_trade_payable_account2_sum = movement_trade_payable_account2_debit - movement_trade_payable_account2_credit

                    self.env.cr.execute(query + '''where account.code = %(account_code)s
                                                                                            and journal_item.company_id in (%(company_ids)s)
                                                                                            and journal_item.date >= %(from_date)s 
                                                                                            and journal_item.date <= %(to_date)s
                                                                                            and {states_args}
                                                                                            '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'account_code': '581103',
                                         'company_ids': self.env.company.id})
                    sub_movement_trade = self.env.cr.dictfetchall()
                    sub_movement_trade_credit = sub_movement_trade[0][
                        'credit'] if \
                        sub_movement_trade[0]['credit'] else 0
                    sub_movement_trade_debit = sub_movement_trade[0]['debit'] if \
                        sub_movement_trade[0]['debit'] else 0
                    movement_trade_payable_account3_sum = sub_movement_trade_debit - sub_movement_trade_credit

                    self.env.cr.execute(query + '''where account.code = %(account_code)s
                                                                                                    and journal_item.company_id in (%(company_ids)s)
                                                                                                    and journal_item.date >= %(from_date)s 
                                                                                                    and journal_item.date <= %(to_date)s
                                                                                                    and {states_args}
                                                                                                    '''.format(
                        states_args=states_args),
                                        {'from_date': options['date'][
                                            'date_from'],
                                         'to_date': options['date']['date_to'],
                                         'account_code': '213403',
                                         'company_ids': self.env.company.id})
                    sub_movement_trade1 = self.env.cr.dictfetchall()
                    movement_trade_payable_account4_sum = \
                        sub_movement_trade1[0][
                            'credit'] if \
                            sub_movement_trade1[0]['credit'] else 0

                    movement_trade_payable_val = round((((
                                                                 movement_trade_payable_sum + movement_trade_payable_account_sum + movement_trade_payable_account1_sum + movement_trade_payable_account2_sum) * -1) - movement_trade_payable_account3_sum) + movement_trade_payable_account4_sum,
                                                       2)
                    movement_trade_payable_list.append(
                        movement_trade_payable_val)
                movement_trade_payable_dict = {
                    'id': 'movement_trade_payable',
                    'name': 'Movement trade and other payables',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {
                            'name': '',
                            'class': 'number'}]
                }
                movement_trade_payable_dict['columns'][0][
                    'name'] = movement_trade_payable_list
            elif options['date_filter'] == 'this_year' or options['date_filter'] == 'last_year':
                for i in range(0, number_period + 1):
                    from_date = datetime.strptime(options['date']['date_from'],
                                                  "%Y-%m-%d")
                    from_date = from_date - relativedelta(years=i)
                    to_date = from_date.replace(month=12, day=31)
                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                                                                and journal_item.company_id = %(company_ids)s
                                                                                                and journal_item.date >= %(from_date)s 
                                                                                                and journal_item.date <= %(to_date)s
                                                                                                and {states_args}
                                                                                                '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '211101',
                                         'code_end': '211402',
                                         'company_ids': self.env.company.id})
                    movement_trade_payable = self.env.cr.dictfetchall()
                    movement_trade_payable_credit = movement_trade_payable[0][
                        'credit'] if \
                        movement_trade_payable[0]['credit'] else 0
                    movement_trade_payable_debit = movement_trade_payable[0][
                        'debit'] if \
                        movement_trade_payable[0]['debit'] else 0

                    movement_trade_payable_sum = movement_trade_payable_debit - movement_trade_payable_credit

                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                                                        and journal_item.company_id in (%(company_ids)s)
                                                                                        and journal_item.date >= %(from_date)s 
                                                                                        and journal_item.date <= %(to_date)s
                                                                                        and {states_args}
                                                                                        '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '213101',
                                         'code_end': '213399',
                                         'company_ids': self.env.company.id})
                    movement_trade_payable_account = self.env.cr.dictfetchall()
                    movement_trade_payable_account_credit = \
                        movement_trade_payable_account[0]['credit'] if \
                            movement_trade_payable_account[0]['credit'] else 0
                    movement_trade_payable_account_debit = \
                        movement_trade_payable_account[0]['debit'] if \
                            movement_trade_payable_account[0]['debit'] else 0

                    movement_trade_payable_account_sum = movement_trade_payable_account_debit - movement_trade_payable_account_credit

                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                                                and journal_item.company_id in (%(company_ids)s)
                                                                                and journal_item.date >= %(from_date)s 
                                                                                and journal_item.date <= %(to_date)s
                                                                                and {states_args}
                                                                                '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '213501',
                                         'code_end': '213599',
                                         'company_ids': self.env.company.id})
                    movement_trade_payable_account1 = self.env.cr.dictfetchall()
                    movement_trade_payable_account1_credit = \
                        movement_trade_payable_account1[0]['credit'] if \
                            movement_trade_payable_account1[0]['credit'] else 0
                    movement_trade_payable_account1_debit = \
                        movement_trade_payable_account1[0]['debit'] if \
                            movement_trade_payable_account1[0]['debit'] else 0

                    movement_trade_payable_account1_sum = movement_trade_payable_account1_debit - movement_trade_payable_account1_credit

                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                                                and journal_item.company_id in (%(company_ids)s)
                                                                                and journal_item.date >= %(from_date)s 
                                                                                and journal_item.date <= %(to_date)s
                                                                                and {states_args}
                                                                                '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '218101',
                                         'code_end': '218999',
                                         'company_ids': self.env.company.id})
                    movement_trade_payable_account2 = self.env.cr.dictfetchall()
                    movement_trade_payable_account2_credit = \
                        movement_trade_payable_account2[0]['credit'] if \
                            movement_trade_payable_account2[0]['credit'] else 0
                    movement_trade_payable_account2_debit = \
                        movement_trade_payable_account2[0]['debit'] if \
                            movement_trade_payable_account2[0]['debit'] else 0

                    movement_trade_payable_account2_sum = movement_trade_payable_account2_debit - movement_trade_payable_account2_credit

                    self.env.cr.execute(query + '''where account.code = %(account_code)s
                                                                                                and journal_item.company_id in (%(company_ids)s)
                                                                                                and journal_item.date >= %(from_date)s 
                                                                                                and journal_item.date <= %(to_date)s
                                                                                                and {states_args}
                                                                                                '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'account_code': '581103',
                                         'company_ids': self.env.company.id})
                    sub_movement_trade = self.env.cr.dictfetchall()
                    sub_movement_trade_credit = sub_movement_trade[0][
                        'credit'] if \
                        sub_movement_trade[0]['credit'] else 0
                    sub_movement_trade_debit = sub_movement_trade[0]['debit'] if \
                        sub_movement_trade[0]['debit'] else 0
                    movement_trade_payable_account3_sum = sub_movement_trade_debit - sub_movement_trade_credit

                    self.env.cr.execute(query + '''where account.code = %(account_code)s
                                                                                                        and journal_item.company_id in (%(company_ids)s)
                                                                                                        and journal_item.date >= %(from_date)s 
                                                                                                        and journal_item.date <= %(to_date)s
                                                                                                        and {states_args}
                                                                                                        '''.format(
                        states_args=states_args),
                                        {'from_date': options['date'][
                                            'date_from'],
                                         'to_date': options['date']['date_to'],
                                         'account_code': '213403',
                                         'company_ids': self.env.company.id})
                    sub_movement_trade1 = self.env.cr.dictfetchall()
                    movement_trade_payable_account4_sum = \
                        sub_movement_trade1[0][
                            'credit'] if \
                            sub_movement_trade1[0]['credit'] else 0

                    movement_trade_payable_val = round((((
                                                                 movement_trade_payable_sum + movement_trade_payable_account_sum + movement_trade_payable_account1_sum + movement_trade_payable_account2_sum) * -1) - movement_trade_payable_account3_sum) + movement_trade_payable_account4_sum,
                                                       2)
                    movement_trade_payable_list.append(
                        movement_trade_payable_val)
                movement_trade_payable_dict = {
                    'id': 'movement_trade_payable',
                    'name': 'Movement trade and other payables',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {
                            'name': '',
                            'class': 'number'}]
                }
                movement_trade_payable_dict['columns'][0][
                    'name'] = movement_trade_payable_list
        else:
            self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                and journal_item.company_id = %(company_ids)s
                                                and journal_item.date >= %(from_date)s 
                                                and journal_item.date <= %(to_date)s
                                                and {states_args}
                                                '''.format(
                states_args=states_args),
                                {'from_date': options['date']['date_from'],
                                 'to_date': options['date']['date_to'],
                                 'code_start': '211101', 'code_end': '211402',
                                 'company_ids': self.env.company.id})
            movement_trade_payable = self.env.cr.dictfetchall()
            movement_trade_payable_credit = movement_trade_payable[0][
                'credit'] if \
                movement_trade_payable[0]['credit'] else 0
            movement_trade_payable_debit = movement_trade_payable[0]['debit'] if \
                movement_trade_payable[0]['debit'] else 0

            movement_trade_payable_sum = movement_trade_payable_debit - movement_trade_payable_credit

            movement_trade_payable_account_sum = self.get_movement_trade_payable_account_sum(
                query, options, states_args)
            movement_trade_payable_account1_sum = self.get_movement_trade_payable_account1_sum(
                query, options, states_args)

            movement_trade_payable_account2_sum = self.get_movement_trade_payable_account2_sum(
                query, options, states_args)
            movement_trade_payable_account3_sum = self.sub_movement_trade_payable_account3_sum(
                query, options,
                states_args)
            movement_trade_payable_account4_sum = self.sub_movement_trade_payable_account3_sum1(
                query, options,
                states_args)
            movement_trade_payable_val = round((((
                                                         movement_trade_payable_sum + movement_trade_payable_account_sum + movement_trade_payable_account1_sum + movement_trade_payable_account2_sum) * -1) - movement_trade_payable_account3_sum) + movement_trade_payable_account4_sum,
                                               2)
            movement_trade_payable_list.append(movement_trade_payable_val)
            movement_trade_payable_dict = {
                'id': 'movement_trade_payable',
                'name': 'Movement trade and other payables',
                'level': 2,
                'class': 'cash_flow_line_val_tr',
                'columns': [
                    {
                        'name': '',
                        'class': 'number'}]
            }
            movement_trade_payable_dict['columns'][0][
                'name'] = movement_trade_payable_list

        return movement_trade_payable_dict

    def adjustment_1(self, options, states_args, number_periods):
        depreciation_of_ppe = []
        amortisation_list = []
        amort_right_list = []
        adjustment_list = []
        interest_lease_liability_list = []
        finance_zain_list = []
        query = '''select sum(journal_item.credit) as credit, sum(journal_item.debit) as debit 
                    from account_move_line as journal_item
                    left join account_account as account on journal_item.account_id = account.id
                    '''
        if options['comparison']['comparison_type'] == 'previous_period':
            if options['date_filter'] == 'this_month' or options[
                'date_filter'] == 'last_month':
                for j in range(0, number_periods + 1):
                    amort = 0
                    amort_right = 0
                    from_date = datetime.strptime(options['date']['date_from'],
                                                  "%Y-%m-%d")
                    from_date = from_date - relativedelta(months=j)
                    to_date = from_date + relativedelta(months=1)
                    to_date = to_date - relativedelta(days=1)

                    # computation for depreciation ppe

                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                and journal_item.company_id = %(company_ids)s
                                and journal_item.date >= %(from_date)s 
                                and journal_item.date <= %(to_date)s
                                and {states_args}
                                '''.format(states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '553101',
                                         'code_end': '553299',
                                         'company_ids': self.env.company.id})
                    depreciation = self.env.cr.dictfetchall()
                    depreciation_credit = depreciation[0]['credit'] if \
                        depreciation[0][
                            'credit'] else 0
                    depreciation_debit = depreciation[0]['debit'] if \
                        depreciation[0][
                            'debit'] else 0
                    dep = round((depreciation_debit - depreciation_credit), 2)
                    depreciation_of_ppe.append(dep)

                    # computation for amortization

                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                and journal_item.company_id = %(company_ids)s
                                and journal_item.date >= %(from_date)s
                                and journal_item.date <= %(to_date)s
                                and {states_args}
                                '''.format(states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '553301',
                                         'code_end': '553399',
                                         'company_ids': self.env.company.id})
                    amortisation = self.env.cr.dictfetchall()
                    amortisation_credit = amortisation[0]['credit'] if \
                        amortisation[0][
                            'credit'] else 0
                    amortisation_debit = amortisation[0]['debit'] if \
                        amortisation[0][
                            'debit'] else 0
                    amort = round((amortisation_debit - amortisation_credit), 2)
                    amortisation_list.append(amort)

                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                and journal_item.company_id = %(company_ids)s
                                                and journal_item.date >= %(from_date)s 
                                                and journal_item.date <= %(to_date)s
                                                and {states_args}
                                                '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '554101',
                                         'code_end': '554999',
                                         'company_ids': self.env.company.id})
                    amortisation_right = self.env.cr.dictfetchall()
                    amortisation_credit = amortisation_right[0]['credit'] if \
                        amortisation_right[0]['credit'] else 0
                    amortisation_debit = amortisation_right[0]['debit'] if \
                        amortisation_right[0]['debit'] else 0
                    amort_right = round(
                        amortisation_debit - amortisation_credit, 2)
                    amort_right_list.append(amort_right)
                    # computation for interest lease liability

                    self.env.cr.execute(query + '''where account.code = %(account_code)s
                                                            and journal_item.company_id = %(company_ids)s
                                                            and journal_item.date >= %(from_date)s
                                                            and journal_item.date <= %(to_date)s
                                                            and {states_args}
                                                            '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'account_code': '224101',
                                         'company_ids': self.env.company.id})
                    interest_lease_liability = self.env.cr.dictfetchall()
                    interest_lease_liability_credit = \
                        interest_lease_liability[0][
                            'credit'] if interest_lease_liability[0][
                            'credit'] else 0
                    interest_lease_liability_debit = \
                        interest_lease_liability[0]['debit'] if \
                            interest_lease_liability[0]['debit'] else 0

                    interest_lease_liability_val = round(((
                                                                  interest_lease_liability_debit - interest_lease_liability_credit) * -1),
                                                         2)
                    interest_lease_liability_list.append(
                        interest_lease_liability_val)

                    # computation for finance zain

                    self.env.cr.execute(query + '''where account.code = %(code_start)s
                                                        and journal_item.company_id = %(company_ids)s
                                                        and journal_item.date >= %(from_date)s
                                                        and journal_item.date <= %(to_date)s
                                                        and {states_args}
                                                        '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '581103',
                                         'company_ids': self.env.company.id})
                    finance_zain = self.env.cr.dictfetchall()
                    finance_zain_credit = finance_zain[0]['credit'] if \
                        finance_zain[0][
                            'credit'] else 0
                    finance_zain_debit = finance_zain[0]['debit'] if \
                        finance_zain[0][
                            'debit'] else 0
                    finance_zain_val = round(
                        (finance_zain_debit - finance_zain_credit), 2)
                    finance_zain_list.append(finance_zain_val)

                # computation for depreciation ppe

                depreciation_of_ppe_dict = {
                    'id': 'depreciation_of_ppe',
                    'name': 'Depreciation of PPE',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {'name': '',
                         'class': 'number'}]
                }
                depreciation_of_ppe_dict['columns'][0][
                    'name'] = depreciation_of_ppe
                adjustment_list.append(depreciation_of_ppe_dict)

                # computation for amortization

                amortisation_dict = {
                    'id': 'amortisation_id',
                    'name': 'Amortisation of intangible assets',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {'name': '',
                         'class': 'number'}]
                }
                amortisation_dict['columns'][0][
                    'name'] = amortisation_list
                adjustment_list.append(amortisation_dict)

                # computation for amortization right

                amortisation_right_dict = {
                    'id': 'amortisation_right_id',
                    'name': 'Amortization of right of use assets',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {'name': '',
                         'class': 'number'}]
                }
                amortisation_right_dict['columns'][0]['name'] = amort_right_list
                adjustment_list.append((amortisation_right_dict))

                # computation for  interest lease liability

                interest_lease_liability_dict = {
                    'id': 'interest_lease_liability',
                    'name': 'Interest on lease liability',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {
                            'name': '',
                            'class': 'number'}]
                }
                interest_lease_liability_dict['columns'][0][
                    'name'] = interest_lease_liability_list
                adjustment_list.append(interest_lease_liability_dict)

                # computation for finance zain

                finance_zain_dict = {
                    'id': 'finance_zain_id',
                    'name': 'Finance costs on Zain`s loan',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {
                            'name': '',
                            'class': 'number'}]
                }
                finance_zain_dict['columns'][0]['name'] = finance_zain_list
                adjustment_list.append(finance_zain_dict)
            elif options['date_filter'] == 'this_quarter' or options['date_filter'] == 'last_quarter':
                for i in range(0, number_periods + 1):
                    from_date = datetime.strptime(options['date']['date_from'],
                                                  "%Y-%m-%d")
                    from_date = from_date + relativedelta(months=-3 * i)
                    current_quarter = round((from_date.month - 1) / 3 + 1)
                    from_date = datetime(from_date.year,
                                         3 * current_quarter - 2, 1)

                    to_date = datetime(from_date.year,
                                       3 * current_quarter + 1,
                                       1) + relativedelta(days=-1)

                    # computation for depreciation ppe

                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                    and journal_item.company_id = %(company_ids)s
                                    and journal_item.date >= %(from_date)s 
                                    and journal_item.date <= %(to_date)s
                                    and {states_args}
                                    '''.format(states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '553101',
                                         'code_end': '553299',
                                         'company_ids': self.env.company.id})
                    depreciation = self.env.cr.dictfetchall()
                    depreciation_credit = depreciation[0]['credit'] if \
                        depreciation[0][
                            'credit'] else 0
                    depreciation_debit = depreciation[0]['debit'] if \
                        depreciation[0][
                            'debit'] else 0
                    dep = round((depreciation_debit - depreciation_credit), 2)
                    depreciation_of_ppe.append(dep)

                    # computation for amortization

                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                    and journal_item.company_id = %(company_ids)s
                                    and journal_item.date >= %(from_date)s
                                    and journal_item.date <= %(to_date)s
                                    and {states_args}
                                    '''.format(states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '553301',
                                         'code_end': '553399',
                                         'company_ids': self.env.company.id})
                    amortisation = self.env.cr.dictfetchall()
                    amortisation_credit = amortisation[0]['credit'] if \
                        amortisation[0][
                            'credit'] else 0
                    amortisation_debit = amortisation[0]['debit'] if \
                        amortisation[0][
                            'debit'] else 0
                    amort = round((amortisation_debit - amortisation_credit), 2)
                    amortisation_list.append(amort)

                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                    and journal_item.company_id = %(company_ids)s
                                                    and journal_item.date >= %(from_date)s 
                                                    and journal_item.date <= %(to_date)s
                                                    and {states_args}
                                                    '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '554101',
                                         'code_end': '554999',
                                         'company_ids': self.env.company.id})
                    amortisation_right = self.env.cr.dictfetchall()
                    amortisation_credit = amortisation_right[0]['credit'] if \
                        amortisation_right[0]['credit'] else 0
                    amortisation_debit = amortisation_right[0]['debit'] if \
                        amortisation_right[0]['debit'] else 0
                    amort_right = round(
                        amortisation_debit - amortisation_credit, 2)
                    amort_right_list.append(amort_right)
                    # computation for interest lease liability

                    self.env.cr.execute(query + '''where account.code = %(account_code)s
                                                                and journal_item.company_id = %(company_ids)s
                                                                and journal_item.date >= %(from_date)s
                                                                and journal_item.date <= %(to_date)s
                                                                and {states_args}
                                                                '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'account_code': '224101',
                                         'company_ids': self.env.company.id})
                    interest_lease_liability = self.env.cr.dictfetchall()
                    interest_lease_liability_credit = \
                        interest_lease_liability[0][
                            'credit'] if interest_lease_liability[0][
                            'credit'] else 0
                    interest_lease_liability_debit = \
                        interest_lease_liability[0]['debit'] if \
                            interest_lease_liability[0]['debit'] else 0

                    interest_lease_liability_val = round(((
                                                                  interest_lease_liability_debit - interest_lease_liability_credit) * -1),
                                                         2)
                    interest_lease_liability_list.append(
                        interest_lease_liability_val)

                    # computation for finance zain

                    self.env.cr.execute(query + '''where account.code = %(code_start)s
                                                            and journal_item.company_id = %(company_ids)s
                                                            and journal_item.date >= %(from_date)s
                                                            and journal_item.date <= %(to_date)s
                                                            and {states_args}
                                                            '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '581103',
                                         'company_ids': self.env.company.id})
                    finance_zain = self.env.cr.dictfetchall()
                    finance_zain_credit = finance_zain[0]['credit'] if \
                        finance_zain[0][
                            'credit'] else 0
                    finance_zain_debit = finance_zain[0]['debit'] if \
                        finance_zain[0][
                            'debit'] else 0
                    finance_zain_val = round(
                        (finance_zain_debit - finance_zain_credit), 2)
                    finance_zain_list.append(finance_zain_val)

                # computation for depreciation ppe

                depreciation_of_ppe_dict = {
                    'id': 'depreciation_of_ppe',
                    'name': 'Depreciation of PPE',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {'name': '',
                         'class': 'number'}]
                }
                depreciation_of_ppe_dict['columns'][0][
                    'name'] = depreciation_of_ppe
                adjustment_list.append(depreciation_of_ppe_dict)

                # computation for amortization

                amortisation_dict = {
                    'id': 'amortisation_id',
                    'name': 'Amortisation of intangible assets',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {'name': '',
                         'class': 'number'}]
                }
                amortisation_dict['columns'][0][
                    'name'] = amortisation_list
                adjustment_list.append(amortisation_dict)

                # computation for amortization right

                amortisation_right_dict = {
                    'id': 'amortisation_right_id',
                    'name': 'Amortization of right of use assets',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {'name': '',
                         'class': 'number'}]
                }
                amortisation_right_dict['columns'][0]['name'] = amort_right_list
                adjustment_list.append((amortisation_right_dict))

                # computation for  interest lease liability

                interest_lease_liability_dict = {
                    'id': 'interest_lease_liability',
                    'name': 'Interest on lease liability',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {
                            'name': '',
                            'class': 'number'}]
                }
                interest_lease_liability_dict['columns'][0][
                    'name'] = interest_lease_liability_list
                adjustment_list.append(interest_lease_liability_dict)

                # computation for finance zain

                finance_zain_dict = {
                    'id': 'finance_zain_id',
                    'name': 'Finance costs on Zain`s loan',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {
                            'name': '',
                            'class': 'number'}]
                }
                finance_zain_dict['columns'][0]['name'] = finance_zain_list
                adjustment_list.append(finance_zain_dict)
            elif options['date_filter'] == 'this_year'or options['date_filter'] == 'last_year':
                for i in range(0, number_periods + 1):
                    from_date = datetime.strptime(options['date']['date_from'],
                                                  "%Y-%m-%d")
                    from_date = from_date - relativedelta(years=i)
                    to_date = from_date.replace(month=12, day=31)
                    # computation for depreciation ppe

                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                        and journal_item.company_id = %(company_ids)s
                                        and journal_item.date >= %(from_date)s 
                                        and journal_item.date <= %(to_date)s
                                        and {states_args}
                                        '''.format(states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '553101',
                                         'code_end': '553299',
                                         'company_ids': self.env.company.id})
                    depreciation = self.env.cr.dictfetchall()
                    depreciation_credit = depreciation[0]['credit'] if \
                        depreciation[0][
                            'credit'] else 0
                    depreciation_debit = depreciation[0]['debit'] if \
                        depreciation[0][
                            'debit'] else 0
                    dep = round((depreciation_debit - depreciation_credit), 2)
                    depreciation_of_ppe.append(dep)

                    # computation for amortization

                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                        and journal_item.company_id = %(company_ids)s
                                        and journal_item.date >= %(from_date)s
                                        and journal_item.date <= %(to_date)s
                                        and {states_args}
                                        '''.format(states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '553301',
                                         'code_end': '553399',
                                         'company_ids': self.env.company.id})
                    amortisation = self.env.cr.dictfetchall()
                    amortisation_credit = amortisation[0]['credit'] if \
                        amortisation[0][
                            'credit'] else 0
                    amortisation_debit = amortisation[0]['debit'] if \
                        amortisation[0][
                            'debit'] else 0
                    amort = round((amortisation_debit - amortisation_credit), 2)
                    amortisation_list.append(amort)

                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                        and journal_item.company_id = %(company_ids)s
                                                        and journal_item.date >= %(from_date)s 
                                                        and journal_item.date <= %(to_date)s
                                                        and {states_args}
                                                        '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '554101',
                                         'code_end': '554999',
                                         'company_ids': self.env.company.id})
                    amortisation_right = self.env.cr.dictfetchall()
                    amortisation_credit = amortisation_right[0]['credit'] if \
                        amortisation_right[0]['credit'] else 0
                    amortisation_debit = amortisation_right[0]['debit'] if \
                        amortisation_right[0]['debit'] else 0
                    amort_right = round(
                        amortisation_debit - amortisation_credit, 2)
                    amort_right_list.append(amort_right)
                    # computation for interest lease liability

                    self.env.cr.execute(query + '''where account.code = %(account_code)s
                                                                    and journal_item.company_id = %(company_ids)s
                                                                    and journal_item.date >= %(from_date)s
                                                                    and journal_item.date <= %(to_date)s
                                                                    and {states_args}
                                                                    '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'account_code': '224101',
                                         'company_ids': self.env.company.id})
                    interest_lease_liability = self.env.cr.dictfetchall()
                    interest_lease_liability_credit = \
                        interest_lease_liability[0][
                            'credit'] if interest_lease_liability[0][
                            'credit'] else 0
                    interest_lease_liability_debit = \
                        interest_lease_liability[0]['debit'] if \
                            interest_lease_liability[0]['debit'] else 0

                    interest_lease_liability_val = round(((
                                                                  interest_lease_liability_debit - interest_lease_liability_credit) * -1),
                                                         2)
                    interest_lease_liability_list.append(
                        interest_lease_liability_val)

                    # computation for finance zain

                    self.env.cr.execute(query + '''where account.code = %(code_start)s
                                                                and journal_item.company_id = %(company_ids)s
                                                                and journal_item.date >= %(from_date)s
                                                                and journal_item.date <= %(to_date)s
                                                                and {states_args}
                                                                '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '581103',
                                         'company_ids': self.env.company.id})
                    finance_zain = self.env.cr.dictfetchall()
                    finance_zain_credit = finance_zain[0]['credit'] if \
                        finance_zain[0][
                            'credit'] else 0
                    finance_zain_debit = finance_zain[0]['debit'] if \
                        finance_zain[0][
                            'debit'] else 0
                    finance_zain_val = round(
                        (finance_zain_debit - finance_zain_credit), 2)
                    finance_zain_list.append(finance_zain_val)

                # computation for depreciation ppe

                depreciation_of_ppe_dict = {
                    'id': 'depreciation_of_ppe',
                    'name': 'Depreciation of PPE',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {'name': '',
                         'class': 'number'}]
                }
                depreciation_of_ppe_dict['columns'][0][
                    'name'] = depreciation_of_ppe
                adjustment_list.append(depreciation_of_ppe_dict)

                # computation for amortization

                amortisation_dict = {
                    'id': 'amortisation_id',
                    'name': 'Amortisation of intangible assets',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {'name': '',
                         'class': 'number'}]
                }
                amortisation_dict['columns'][0][
                    'name'] = amortisation_list
                adjustment_list.append(amortisation_dict)

                # computation for amortization right

                amortisation_right_dict = {
                    'id': 'amortisation_right_id',
                    'name': 'Amortization of right of use assets',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {'name': '',
                         'class': 'number'}]
                }
                amortisation_right_dict['columns'][0]['name'] = amort_right_list
                adjustment_list.append((amortisation_right_dict))

                # computation for  interest lease liability

                interest_lease_liability_dict = {
                    'id': 'interest_lease_liability',
                    'name': 'Interest on lease liability',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {
                            'name': '',
                            'class': 'number'}]
                }
                interest_lease_liability_dict['columns'][0][
                    'name'] = interest_lease_liability_list
                adjustment_list.append(interest_lease_liability_dict)

                # computation for finance zain

                finance_zain_dict = {
                    'id': 'finance_zain_id',
                    'name': 'Finance costs on Zain`s loan',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {
                            'name': '',
                            'class': 'number'}]
                }
                finance_zain_dict['columns'][0]['name'] = finance_zain_list
                adjustment_list.append(finance_zain_dict)
        elif options['comparison'][
            'comparison_type'] == 'same_period_last_year':
            if options['date_filter'] == 'this_month' or options[
                'date_filter'] == 'last_month':
                for j in range(0, number_periods + 1):
                    amort = 0
                    amort_right = 0
                    from_date = datetime.strptime(options['date']['date_from'],
                                                  "%Y-%m-%d")
                    from_date = from_date - relativedelta(years=j)
                    to_date = from_date + relativedelta(months=1)
                    to_date = to_date - relativedelta(days=1)
                    # computation for depreciation ppe

                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                    and journal_item.company_id = %(company_ids)s
                                                    and journal_item.date >= %(from_date)s 
                                                    and journal_item.date <= %(to_date)s
                                                    and {states_args}
                                                    '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '553101',
                                         'code_end': '553299',
                                         'company_ids': self.env.company.id})
                    depreciation = self.env.cr.dictfetchall()
                    depreciation_credit = depreciation[0]['credit'] if \
                        depreciation[0][
                            'credit'] else 0
                    depreciation_debit = depreciation[0]['debit'] if \
                        depreciation[0][
                            'debit'] else 0
                    dep = round(
                        (depreciation_debit - depreciation_credit), 2)
                    depreciation_of_ppe.append(dep)

                    # computation for amortization

                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                and journal_item.company_id = %(company_ids)s
                                and journal_item.date >= %(from_date)s
                                and journal_item.date <= %(to_date)s
                                and {states_args}
                                '''.format(states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '553301',
                                         'code_end': '553399',
                                         'company_ids': self.env.company.id})
                    amortisation = self.env.cr.dictfetchall()
                    amortisation_credit = amortisation[0]['credit'] if \
                        amortisation[0][
                            'credit'] else 0
                    amortisation_debit = amortisation[0]['debit'] if \
                        amortisation[0][
                            'debit'] else 0
                    amort = round((amortisation_debit - amortisation_credit), 2)
                    amortisation_list.append(amort)

                    # computation for amortization right

                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                and journal_item.company_id = %(company_ids)s
                                                and journal_item.date >= %(from_date)s 
                                                and journal_item.date <= %(to_date)s
                                                and {states_args}
                                                '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '554101',
                                         'code_end': '554999',
                                         'company_ids': self.env.company.id})
                    amortisation_right = self.env.cr.dictfetchall()
                    amortisation_credit = amortisation_right[0]['credit'] if \
                        amortisation_right[0]['credit'] else 0
                    amortisation_debit = amortisation_right[0]['debit'] if \
                        amortisation_right[0]['debit'] else 0
                    amort_right = round(
                        amortisation_debit - amortisation_credit, 2)
                    amort_right_list.append(amort_right)

                    # computation for interest lease liability

                    self.env.cr.execute(query + '''where account.code = %(account_code)s
                                                            and journal_item.company_id = %(company_ids)s
                                                            and journal_item.date >= %(from_date)s
                                                            and journal_item.date <= %(to_date)s
                                                            and {states_args}
                                                            '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'account_code': '224101',
                                         'company_ids': self.env.company.id})
                    interest_lease_liability = self.env.cr.dictfetchall()
                    interest_lease_liability_credit = \
                        interest_lease_liability[0][
                            'credit'] if interest_lease_liability[0][
                            'credit'] else 0
                    interest_lease_liability_debit = \
                        interest_lease_liability[0]['debit'] if \
                            interest_lease_liability[0]['debit'] else 0

                    interest_lease_liability_val = round(((
                                                                  interest_lease_liability_debit - interest_lease_liability_credit) * -1),
                                                         2)
                    interest_lease_liability_list.append(
                        interest_lease_liability_val)

                    # computation for finance zain

                    self.env.cr.execute(query + '''where account.code = %(code_start)s
                                                        and journal_item.company_id = %(company_ids)s
                                                        and journal_item.date >= %(from_date)s
                                                        and journal_item.date <= %(to_date)s
                                                        and {states_args}
                                                        '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '581103',
                                         'company_ids': self.env.company.id})
                    finance_zain = self.env.cr.dictfetchall()
                    finance_zain_credit = finance_zain[0]['credit'] if \
                        finance_zain[0][
                            'credit'] else 0
                    finance_zain_debit = finance_zain[0]['debit'] if \
                        finance_zain[0][
                            'debit'] else 0
                    finance_zain_val = round(
                        (finance_zain_debit - finance_zain_credit), 2)
                    finance_zain_list.append(finance_zain_val)

                # computation for depreciation ppe

                depreciation_of_ppe_dict = {
                    'id': 'depreciation_of_ppe',
                    'name': 'Depreciation of PPE',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {'name': '',
                         'class': 'number'}]
                }
                depreciation_of_ppe_dict['columns'][0][
                    'name'] = depreciation_of_ppe
                adjustment_list.append(depreciation_of_ppe_dict)

                # computation for amortization

                amortisation_dict = {
                    'id': 'amortisation_id',
                    'name': 'Amortisation of intangible assets',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {'name': '',
                         'class': 'number'}]
                }
                amortisation_dict['columns'][0][
                    'name'] = amortisation_list
                adjustment_list.append(amortisation_dict)

                # computation for amortization right

                amortisation_right_dict = {
                    'id': 'amortisation_right_id',
                    'name': 'Amortization of right of use assets',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {'name': '',
                         'class': 'number'}]
                }
                amortisation_right_dict['columns'][0]['name'] = amort_right_list
                adjustment_list.append((amortisation_right_dict))

                # computation for  interest lease liability

                interest_lease_liability_dict = {
                    'id': 'interest_lease_liability',
                    'name': 'Interest on lease liability',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {
                            'name': '',
                            'class': 'number'}]
                }
                interest_lease_liability_dict['columns'][0][
                    'name'] = interest_lease_liability_list
                adjustment_list.append(interest_lease_liability_dict)

                # computation for finance zain

                finance_zain_dict = {
                    'id': 'finance_zain_id',
                    'name': 'Finance costs on Zain`s loan',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {
                            'name': '',
                            'class': 'number'}]
                }
                finance_zain_dict['columns'][0]['name'] = finance_zain_list
                adjustment_list.append(finance_zain_dict)
            elif options['date_filter'] == 'this_quarter' or options['date_filter'] == 'last_quarter':
                for i in range(0, number_periods + 1):
                    from_date = datetime.strptime(options['date']['date_from'],
                                                  "%Y-%m-%d")
                    from_date = from_date + relativedelta(years=-i)
                    current_quarter = round((from_date.month - 1) / 3 + 1)
                    from_date = datetime(from_date.year,
                                         3 * current_quarter - 2, 1)

                    to_date = datetime(from_date.year,
                                       3 * current_quarter + 1,
                                       1) + relativedelta(days=-1)
                    # computation for depreciation ppe

                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                        and journal_item.company_id = %(company_ids)s
                                                        and journal_item.date >= %(from_date)s 
                                                        and journal_item.date <= %(to_date)s
                                                        and {states_args}
                                                        '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '553101',
                                         'code_end': '553299',
                                         'company_ids': self.env.company.id})
                    depreciation = self.env.cr.dictfetchall()
                    depreciation_credit = depreciation[0]['credit'] if \
                        depreciation[0][
                            'credit'] else 0
                    depreciation_debit = depreciation[0]['debit'] if \
                        depreciation[0][
                            'debit'] else 0
                    dep = round(
                        (depreciation_debit - depreciation_credit), 2)
                    depreciation_of_ppe.append(dep)

                    # computation for amortization

                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                    and journal_item.company_id = %(company_ids)s
                                    and journal_item.date >= %(from_date)s
                                    and journal_item.date <= %(to_date)s
                                    and {states_args}
                                    '''.format(states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '553301',
                                         'code_end': '553399',
                                         'company_ids': self.env.company.id})
                    amortisation = self.env.cr.dictfetchall()
                    amortisation_credit = amortisation[0]['credit'] if \
                        amortisation[0][
                            'credit'] else 0
                    amortisation_debit = amortisation[0]['debit'] if \
                        amortisation[0][
                            'debit'] else 0
                    amort = round((amortisation_debit - amortisation_credit), 2)
                    amortisation_list.append(amort)

                    # computation for amortization right

                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                    and journal_item.company_id = %(company_ids)s
                                                    and journal_item.date >= %(from_date)s 
                                                    and journal_item.date <= %(to_date)s
                                                    and {states_args}
                                                    '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '554101',
                                         'code_end': '554999',
                                         'company_ids': self.env.company.id})
                    amortisation_right = self.env.cr.dictfetchall()
                    amortisation_credit = amortisation_right[0]['credit'] if \
                        amortisation_right[0]['credit'] else 0
                    amortisation_debit = amortisation_right[0]['debit'] if \
                        amortisation_right[0]['debit'] else 0
                    amort_right = round(
                        amortisation_debit - amortisation_credit, 2)
                    amort_right_list.append(amort_right)

                    # computation for interest lease liability

                    self.env.cr.execute(query + '''where account.code = %(account_code)s
                                                                and journal_item.company_id = %(company_ids)s
                                                                and journal_item.date >= %(from_date)s
                                                                and journal_item.date <= %(to_date)s
                                                                and {states_args}
                                                                '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'account_code': '224101',
                                         'company_ids': self.env.company.id})
                    interest_lease_liability = self.env.cr.dictfetchall()
                    interest_lease_liability_credit = \
                        interest_lease_liability[0][
                            'credit'] if interest_lease_liability[0][
                            'credit'] else 0
                    interest_lease_liability_debit = \
                        interest_lease_liability[0]['debit'] if \
                            interest_lease_liability[0]['debit'] else 0

                    interest_lease_liability_val = round(((
                                                                  interest_lease_liability_debit - interest_lease_liability_credit) * -1),
                                                         2)
                    interest_lease_liability_list.append(
                        interest_lease_liability_val)

                    # computation for finance zain

                    self.env.cr.execute(query + '''where account.code = %(code_start)s
                                                            and journal_item.company_id = %(company_ids)s
                                                            and journal_item.date >= %(from_date)s
                                                            and journal_item.date <= %(to_date)s
                                                            and {states_args}
                                                            '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '581103',
                                         'company_ids': self.env.company.id})
                    finance_zain = self.env.cr.dictfetchall()
                    finance_zain_credit = finance_zain[0]['credit'] if \
                        finance_zain[0][
                            'credit'] else 0
                    finance_zain_debit = finance_zain[0]['debit'] if \
                        finance_zain[0][
                            'debit'] else 0
                    finance_zain_val = round(
                        (finance_zain_debit - finance_zain_credit), 2)
                    finance_zain_list.append(finance_zain_val)

                # computation for depreciation ppe

                depreciation_of_ppe_dict = {
                    'id': 'depreciation_of_ppe',
                    'name': 'Depreciation of PPE',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {'name': '',
                         'class': 'number'}]
                }
                depreciation_of_ppe_dict['columns'][0][
                    'name'] = depreciation_of_ppe
                adjustment_list.append(depreciation_of_ppe_dict)

                # computation for amortization

                amortisation_dict = {
                    'id': 'amortisation_id',
                    'name': 'Amortisation of intangible assets',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {'name': '',
                         'class': 'number'}]
                }
                amortisation_dict['columns'][0][
                    'name'] = amortisation_list
                adjustment_list.append(amortisation_dict)

                # computation for amortization right

                amortisation_right_dict = {
                    'id': 'amortisation_right_id',
                    'name': 'Amortization of right of use assets',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {'name': '',
                         'class': 'number'}]
                }
                amortisation_right_dict['columns'][0]['name'] = amort_right_list
                adjustment_list.append((amortisation_right_dict))

                # computation for  interest lease liability

                interest_lease_liability_dict = {
                    'id': 'interest_lease_liability',
                    'name': 'Interest on lease liability',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {
                            'name': '',
                            'class': 'number'}]
                }
                interest_lease_liability_dict['columns'][0][
                    'name'] = interest_lease_liability_list
                adjustment_list.append(interest_lease_liability_dict)

                # computation for finance zain

                finance_zain_dict = {
                    'id': 'finance_zain_id',
                    'name': 'Finance costs on Zain`s loan',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {
                            'name': '',
                            'class': 'number'}]
                }
                finance_zain_dict['columns'][0]['name'] = finance_zain_list
                adjustment_list.append(finance_zain_dict)
            elif options['date_filter'] == 'this_year' or options['date_filter'] == 'last_year':
                for i in range(0, number_periods + 1):
                    from_date = datetime.strptime(options['date']['date_from'],
                                                  "%Y-%m-%d")
                    from_date = from_date - relativedelta(years=i)
                    to_date = from_date.replace(month=12, day=31)
                    # to_date = to_date - relativedelta(days=1)
                    # computation for depreciation ppe

                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                            and journal_item.company_id = %(company_ids)s
                                                            and journal_item.date >= %(from_date)s 
                                                            and journal_item.date <= %(to_date)s
                                                            and {states_args}
                                                            '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '553101',
                                         'code_end': '553299',
                                         'company_ids': self.env.company.id})
                    depreciation = self.env.cr.dictfetchall()
                    depreciation_credit = depreciation[0]['credit'] if \
                        depreciation[0][
                            'credit'] else 0
                    depreciation_debit = depreciation[0]['debit'] if \
                        depreciation[0][
                            'debit'] else 0
                    dep = round(
                        (depreciation_debit - depreciation_credit), 2)
                    depreciation_of_ppe.append(dep)

                    # computation for amortization

                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                        and journal_item.company_id = %(company_ids)s
                                        and journal_item.date >= %(from_date)s
                                        and journal_item.date <= %(to_date)s
                                        and {states_args}
                                        '''.format(states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '553301',
                                         'code_end': '553399',
                                         'company_ids': self.env.company.id})
                    amortisation = self.env.cr.dictfetchall()
                    amortisation_credit = amortisation[0]['credit'] if \
                        amortisation[0][
                            'credit'] else 0
                    amortisation_debit = amortisation[0]['debit'] if \
                        amortisation[0][
                            'debit'] else 0
                    amort = round((amortisation_debit - amortisation_credit), 2)
                    amortisation_list.append(amort)

                    # computation for amortization right

                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                        and journal_item.company_id = %(company_ids)s
                                                        and journal_item.date >= %(from_date)s 
                                                        and journal_item.date <= %(to_date)s
                                                        and {states_args}
                                                        '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '554101',
                                         'code_end': '554999',
                                         'company_ids': self.env.company.id})
                    amortisation_right = self.env.cr.dictfetchall()
                    amortisation_credit = amortisation_right[0]['credit'] if \
                        amortisation_right[0]['credit'] else 0
                    amortisation_debit = amortisation_right[0]['debit'] if \
                        amortisation_right[0]['debit'] else 0
                    amort_right = round(
                        amortisation_debit - amortisation_credit, 2)
                    amort_right_list.append(amort_right)

                    # computation for interest lease liability

                    self.env.cr.execute(query + '''where account.code = %(account_code)s
                                                                    and journal_item.company_id = %(company_ids)s
                                                                    and journal_item.date >= %(from_date)s
                                                                    and journal_item.date <= %(to_date)s
                                                                    and {states_args}
                                                                    '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'account_code': '224101',
                                         'company_ids': self.env.company.id})
                    interest_lease_liability = self.env.cr.dictfetchall()
                    interest_lease_liability_credit = \
                        interest_lease_liability[0][
                            'credit'] if interest_lease_liability[0][
                            'credit'] else 0
                    interest_lease_liability_debit = \
                        interest_lease_liability[0]['debit'] if \
                            interest_lease_liability[0]['debit'] else 0

                    interest_lease_liability_val = round(((
                                                                  interest_lease_liability_debit - interest_lease_liability_credit) * -1),
                                                         2)
                    interest_lease_liability_list.append(
                        interest_lease_liability_val)

                    # computation for finance zain

                    self.env.cr.execute(query + '''where account.code = %(code_start)s
                                                                and journal_item.company_id = %(company_ids)s
                                                                and journal_item.date >= %(from_date)s
                                                                and journal_item.date <= %(to_date)s
                                                                and {states_args}
                                                                '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '581103',
                                         'company_ids': self.env.company.id})
                    finance_zain = self.env.cr.dictfetchall()
                    finance_zain_credit = finance_zain[0]['credit'] if \
                        finance_zain[0][
                            'credit'] else 0
                    finance_zain_debit = finance_zain[0]['debit'] if \
                        finance_zain[0][
                            'debit'] else 0
                    finance_zain_val = round(
                        (finance_zain_debit - finance_zain_credit), 2)
                    finance_zain_list.append(finance_zain_val)

                # computation for depreciation ppe

                depreciation_of_ppe_dict = {
                    'id': 'depreciation_of_ppe',
                    'name': 'Depreciation of PPE',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {'name': '',
                         'class': 'number'}]
                }
                depreciation_of_ppe_dict['columns'][0][
                    'name'] = depreciation_of_ppe
                adjustment_list.append(depreciation_of_ppe_dict)

                # computation for amortization

                amortisation_dict = {
                    'id': 'amortisation_id',
                    'name': 'Amortisation of intangible assets',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {'name': '',
                         'class': 'number'}]
                }
                amortisation_dict['columns'][0][
                    'name'] = amortisation_list
                adjustment_list.append(amortisation_dict)

                # computation for amortization right

                amortisation_right_dict = {
                    'id': 'amortisation_right_id',
                    'name': 'Amortization of right of use assets',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {'name': '',
                         'class': 'number'}]
                }
                amortisation_right_dict['columns'][0]['name'] = amort_right_list
                adjustment_list.append((amortisation_right_dict))

                # computation for  interest lease liability

                interest_lease_liability_dict = {
                    'id': 'interest_lease_liability',
                    'name': 'Interest on lease liability',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {
                            'name': '',
                            'class': 'number'}]
                }
                interest_lease_liability_dict['columns'][0][
                    'name'] = interest_lease_liability_list
                adjustment_list.append(interest_lease_liability_dict)

                # computation for finance zain

                finance_zain_dict = {
                    'id': 'finance_zain_id',
                    'name': 'Finance costs on Zain`s loan',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {
                            'name': '',
                            'class': 'number'}]
                }
                finance_zain_dict['columns'][0]['name'] = finance_zain_list
                adjustment_list.append(finance_zain_dict)
        else:
            amort = 0
            amort_right = 0
            self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                                and journal_item.company_id = %(company_ids)s
                                                                and journal_item.date >= %(from_date)s 
                                                                and journal_item.date <= %(to_date)s
                                                                and {states_args}
                                                                '''.format(
                states_args=states_args),
                                {'from_date': options['date']['date_from'],
                                 'to_date': options['date']['date_to'],
                                 'code_start': '553101',
                                 'code_end': '553299',
                                 'company_ids': self.env.company.id})
            depreciation = self.env.cr.dictfetchall()
            depreciation_credit = depreciation[0]['credit'] if \
                depreciation[0][
                    'credit'] else 0
            depreciation_debit = depreciation[0]['debit'] if \
                depreciation[0][
                    'debit'] else 0
            dep = round(
                (depreciation_debit - depreciation_credit), 2)
            depreciation_of_ppe.append(dep)

            # computation for depreciation ppe

            depreciation_of_ppe_dict = {
                'id': 'depreciation_of_ppe',
                'name': 'Depreciation of PPE',
                'level': 2,
                'class': 'cash_flow_line_val_tr',
                'columns': [
                    {'name': '',
                     'class': 'number'}]
            }
            depreciation_of_ppe_dict['columns'][0]['name'] = depreciation_of_ppe
            adjustment_list.append(depreciation_of_ppe_dict)

            # computation for amortisation
            self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                        and journal_item.company_id = %(company_ids)s
                        and journal_item.date >= %(from_date)s
                        and journal_item.date <= %(to_date)s
                        and {states_args}
                        '''.format(states_args=states_args),
                                {'from_date': options['date']['date_from'],
                                 'to_date': options['date']['date_to'],
                                 'code_start': '553301', 'code_end': '553399',
                                 'company_ids': self.env.company.id})
            amortisation = self.env.cr.dictfetchall()
            amortisation_credit = amortisation[0]['credit'] if amortisation[0][
                'credit'] else 0
            amortisation_debit = amortisation[0]['debit'] if amortisation[0][
                'debit'] else 0

            amort = round((amortisation_debit - amortisation_credit), 2)
            amortisation_list.append(amort)
            amortisation_dict = {
                'id': 'amortisation_id',
                'name': 'Amortisation of intangible assets',
                'level': 2,
                'class': 'cash_flow_line_val_tr',
                'columns': [
                    {'name': '',
                     'class': 'number'}]
            }
            amortisation_dict['columns'][0]['name'] = amortisation_list
            adjustment_list.append(amortisation_dict)

            # computation for amortisation right

            self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                            and journal_item.company_id = %(company_ids)s
                                                            and journal_item.date >= %(from_date)s 
                                                            and journal_item.date <= %(to_date)s
                                                            and {states_args}
                                                            '''.format(
                states_args=states_args),
                                {'from_date': options['date']['date_from'],
                                 'to_date': options['date']['date_to'],
                                 'code_start': '554101',
                                 'code_end': '554999',
                                 'company_ids': self.env.company.id})
            amortisation_right = self.env.cr.dictfetchall()
            amortisation_credit = amortisation_right[0]['credit'] if \
                amortisation_right[0]['credit'] else 0
            amortisation_debit = amortisation_right[0]['debit'] if \
                amortisation_right[0]['debit'] else 0
            amort_right = round(
                amortisation_debit - amortisation_credit, 2)
            amort_right_list.append(amort_right)
            amortisation_right_dict = {
                'id': 'amortisation_right_id',
                'name': 'Amortization of right of use assets',
                'level': 2,
                'class': 'cash_flow_line_val_tr',
                'columns': [
                    {'name': '',
                     'class': 'number'}]
            }
            amortisation_right_dict['columns'][0]['name'] = amort_right_list
            adjustment_list.append((amortisation_right_dict))

            # computation for interest lease liability

            self.env.cr.execute(query + '''where account.code = %(account_code)s
                                        and journal_item.company_id = %(company_ids)s
                                        and journal_item.date >= %(from_date)s
                                        and journal_item.date <= %(to_date)s
                                        and {states_args}
                                        '''.format(states_args=states_args),
                                {'from_date': options['date']['date_from'],
                                 'to_date': options['date']['date_to'],
                                 'account_code': '224101',
                                 'company_ids': self.env.company.id})
            interest_lease_liability = self.env.cr.dictfetchall()
            interest_lease_liability_credit = interest_lease_liability[0][
                'credit'] if interest_lease_liability[0]['credit'] else 0
            interest_lease_liability_debit = interest_lease_liability[0][
                'debit'] if \
                interest_lease_liability[0]['debit'] else 0

            interest_lease_liability_val = round(((
                                                          interest_lease_liability_debit - interest_lease_liability_credit) * -1),
                                                 2)
            interest_lease_liability_list.append(interest_lease_liability_val)
            interest_lease_liability_dict = {
                'id': 'interest_lease_liability',
                'name': 'Interest on lease liability',
                'level': 2,
                'class': 'cash_flow_line_val_tr',
                'columns': [
                    {
                        'name': '',
                        'class': 'number'}]
            }
            interest_lease_liability_dict['columns'][0][
                'name'] = interest_lease_liability_list
            adjustment_list.append(interest_lease_liability_dict)

            # computation for finance zain

            self.env.cr.execute(query + '''where account.code = %(code_start)s
                                                and journal_item.company_id = %(company_ids)s
                                                and journal_item.date >= %(from_date)s
                                                and journal_item.date <= %(to_date)s
                                                and {states_args}
                                                '''.format(
                states_args=states_args),
                                {'from_date': options['date']['date_from'],
                                 'to_date': options['date']['date_to'],
                                 'code_start': '581103',
                                 'company_ids': self.env.company.id})
            finance_zain = self.env.cr.dictfetchall()
            finance_zain_credit = finance_zain[0]['credit'] if finance_zain[0][
                'credit'] else 0
            finance_zain_debit = finance_zain[0]['debit'] if finance_zain[0][
                'debit'] else 0
            finance_zain_val = round(
                (finance_zain_debit - finance_zain_credit), 2)
            finance_zain_list.append(finance_zain_val)

            finance_zain_dict = {
                'id': 'finance_zain_id',
                'name': 'Finance costs on Zain`s loan',
                'level': 2,
                'class': 'cash_flow_line_val_tr',
                'columns': [
                    {
                        'name': '',
                        'class': 'number'}]
            }
            finance_zain_dict['columns'][0]['name'] = finance_zain_list
            adjustment_list.append(finance_zain_dict)
        return adjustment_list

    def get_movement_related_parties_dict(self, query, options, states_args,
                                          number_period):
        movement_related_parties_dict = {}
        movement_related_parties_list = []
        if options['comparison']['comparison_type'] == 'previous_period':
            if options['date_filter'] == 'this_month' or options[
                'date_filter'] == 'last_month':
                for i in range(0, number_period + 1):
                    from_date = datetime.strptime(options['date']['date_from'],
                                                  "%Y-%m-%d")
                    from_date = from_date - relativedelta(months=i)
                    to_date = from_date + relativedelta(months=1)
                    to_date = to_date - relativedelta(days=1)
                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                                                and journal_item.company_id = %(company_ids)s
                                                                                and journal_item.date >= %(from_date)s 
                                                                                and journal_item.date <= %(to_date)s
                                                                                and {states_args}
                                                                                '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '212101',
                                         'code_end': '212169',
                                         'company_ids': self.env.company.id})
                    movement_related_parties = self.env.cr.dictfetchall()
                    movement_related_parties_credit = \
                        movement_related_parties[0][
                            'credit'] if movement_related_parties[0][
                            'credit'] else 0
                    movement_related_parties_debit = \
                        movement_related_parties[0]['debit'] if \
                            movement_related_parties[0]['debit'] else 0
                    movement_related_parties_sum = movement_related_parties_debit - movement_related_parties_credit
                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                                            and journal_item.company_id = %(company_ids)s
                                                                            and journal_item.date >= %(from_date)s 
                                                                            and journal_item.date <= %(to_date)s
                                                                            and {states_args}
                                                                            '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '212171',
                                         'code_end': '212999',
                                         'company_ids': self.env.company.id})
                    movement_related_parties_account = self.env.cr.dictfetchall()
                    movement_related_parties_account_credit = \
                        movement_related_parties_account[0]['credit'] if \
                            movement_related_parties_account[0]['credit'] else 0
                    movement_related_parties_account_debit = \
                        movement_related_parties_account[0]['debit'] if \
                            movement_related_parties_account[0]['debit'] else 0
                    movement_related_parties_account = movement_related_parties_account_debit - movement_related_parties_account_credit
                    movement_related_partiess = round(((
                                                               movement_related_parties_sum + movement_related_parties_account) * -1),
                                                      2)
                    movement_related_parties_list.append(
                        movement_related_partiess)

                    movement_related_parties_dict = {
                        'id': 'movement_related_parties',
                        'name': 'Movement in due to related parties',
                        'level': 2,
                        'class': 'cash_flow_line_val_tr',
                        'columns': [
                            {
                                'name': '',
                                'class': 'number'}]
                    }
                    movement_related_parties_dict['columns'][0][
                        'name'] = movement_related_parties_list
            elif options['date_filter'] == 'this_quarter' or options['date_filter'] == 'last_quarter':
                for i in range(0, number_period + 1):
                    from_date = datetime.strptime(
                        options['date']['date_from'],
                        "%Y-%m-%d")
                    from_date = from_date + relativedelta(months=-3 * i)
                    current_quarter = round((from_date.month - 1) / 3 + 1)
                    from_date = datetime(from_date.year,
                                         3 * current_quarter - 2, 1)

                    to_date = datetime(from_date.year,
                                       3 * current_quarter + 1,
                                       1) + relativedelta(days=-1)
                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                                                                    and journal_item.company_id = %(company_ids)s
                                                                                                    and journal_item.date >= %(from_date)s 
                                                                                                    and journal_item.date <= %(to_date)s
                                                                                                    and {states_args}
                                                                                                    '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '212101',
                                         'code_end': '212169',
                                         'company_ids': self.env.company.id})
                    movement_related_parties = self.env.cr.dictfetchall()
                    movement_related_parties_credit = \
                        movement_related_parties[0][
                            'credit'] if movement_related_parties[0][
                            'credit'] else 0
                    movement_related_parties_debit = \
                        movement_related_parties[0]['debit'] if \
                            movement_related_parties[0]['debit'] else 0
                    movement_related_parties_sum = movement_related_parties_debit - movement_related_parties_credit
                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                                                                and journal_item.company_id = %(company_ids)s
                                                                                                and journal_item.date >= %(from_date)s 
                                                                                                and journal_item.date <= %(to_date)s
                                                                                                and {states_args}
                                                                                                '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '212171',
                                         'code_end': '212999',
                                         'company_ids': self.env.company.id})
                    movement_related_parties_account = self.env.cr.dictfetchall()
                    movement_related_parties_account_credit = \
                        movement_related_parties_account[0]['credit'] if \
                            movement_related_parties_account[0]['credit'] else 0
                    movement_related_parties_account_debit = \
                        movement_related_parties_account[0]['debit'] if \
                            movement_related_parties_account[0]['debit'] else 0
                    movement_related_parties_account = movement_related_parties_account_debit - movement_related_parties_account_credit
                    movement_related_partiess = round(((
                                                               movement_related_parties_sum + movement_related_parties_account) * -1),
                                                      2)
                    movement_related_parties_list.append(
                        movement_related_partiess)

                    movement_related_parties_dict = {
                        'id': 'movement_related_parties',
                        'name': 'Movement in due to related parties',
                        'level': 2,
                        'class': 'cash_flow_line_val_tr',
                        'columns': [
                            {
                                'name': '',
                                'class': 'number'}]
                    }
                    movement_related_parties_dict['columns'][0][
                        'name'] = movement_related_parties_list
            elif options['date_filter'] == 'this_year' or options['date_filter'] == 'last_year':
                for i in range(0, number_period + 1):
                    from_date = datetime.strptime(options['date']['date_from'],
                                                  "%Y-%m-%d")
                    from_date = from_date - relativedelta(years=i)
                    to_date = from_date.replace(month=12, day=31)
                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                                                                    and journal_item.company_id = %(company_ids)s
                                                                                                    and journal_item.date >= %(from_date)s 
                                                                                                    and journal_item.date <= %(to_date)s
                                                                                                    and {states_args}
                                                                                                    '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '212101',
                                         'code_end': '212169',
                                         'company_ids': self.env.company.id})
                    movement_related_parties = self.env.cr.dictfetchall()
                    movement_related_parties_credit = \
                        movement_related_parties[0][
                            'credit'] if movement_related_parties[0][
                            'credit'] else 0
                    movement_related_parties_debit = \
                        movement_related_parties[0]['debit'] if \
                            movement_related_parties[0]['debit'] else 0
                    movement_related_parties_sum = movement_related_parties_debit - movement_related_parties_credit
                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                                                                and journal_item.company_id = %(company_ids)s
                                                                                                and journal_item.date >= %(from_date)s 
                                                                                                and journal_item.date <= %(to_date)s
                                                                                                and {states_args}
                                                                                                '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '212171',
                                         'code_end': '212999',
                                         'company_ids': self.env.company.id})
                    movement_related_parties_account = self.env.cr.dictfetchall()
                    movement_related_parties_account_credit = \
                        movement_related_parties_account[0]['credit'] if \
                            movement_related_parties_account[0]['credit'] else 0
                    movement_related_parties_account_debit = \
                        movement_related_parties_account[0]['debit'] if \
                            movement_related_parties_account[0]['debit'] else 0
                    movement_related_parties_account = movement_related_parties_account_debit - movement_related_parties_account_credit
                    movement_related_partiess = round(((
                                                               movement_related_parties_sum + movement_related_parties_account) * -1),
                                                      2)
                    movement_related_parties_list.append(
                        movement_related_partiess)

                    movement_related_parties_dict = {
                        'id': 'movement_related_parties',
                        'name': 'Movement in due to related parties',
                        'level': 2,
                        'class': 'cash_flow_line_val_tr',
                        'columns': [
                            {
                                'name': '',
                                'class': 'number'}]
                    }
                    movement_related_parties_dict['columns'][0][
                        'name'] = movement_related_parties_list

        elif options['comparison'][
            'comparison_type'] == 'same_period_last_year':
            if options['date_filter'] == 'this_month' or options[
                'date_filter'] == 'last_month':
                for j in range(0, number_period + 1):
                    from_date = datetime.strptime(options['date']['date_from'],
                                                  "%Y-%m-%d")
                    from_date = from_date - relativedelta(years=j)
                    to_date = from_date + relativedelta(months=1)
                    to_date = to_date - relativedelta(days=1)
                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                                                and journal_item.company_id = %(company_ids)s
                                                                                and journal_item.date >= %(from_date)s 
                                                                                and journal_item.date <= %(to_date)s
                                                                                and {states_args}
                                                                                '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '212101',
                                         'code_end': '212169',
                                         'company_ids': self.env.company.id})
                    movement_related_parties = self.env.cr.dictfetchall()
                    movement_related_parties_credit = \
                        movement_related_parties[0][
                            'credit'] if movement_related_parties[0][
                            'credit'] else 0
                    movement_related_parties_debit = \
                        movement_related_parties[0]['debit'] if \
                            movement_related_parties[0]['debit'] else 0
                    movement_related_parties_sum = movement_related_parties_debit - movement_related_parties_credit
                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                                            and journal_item.company_id = %(company_ids)s
                                                                            and journal_item.date >= %(from_date)s 
                                                                            and journal_item.date <= %(to_date)s
                                                                            and {states_args}
                                                                            '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '212171',
                                         'code_end': '212999',
                                         'company_ids': self.env.company.id})
                    movement_related_parties_account = self.env.cr.dictfetchall()
                    movement_related_parties_account_credit = \
                        movement_related_parties_account[0]['credit'] if \
                            movement_related_parties_account[0]['credit'] else 0
                    movement_related_parties_account_debit = \
                        movement_related_parties_account[0]['debit'] if \
                            movement_related_parties_account[0]['debit'] else 0
                    movement_related_parties_account = movement_related_parties_account_debit - movement_related_parties_account_credit
                    movement_related_partiess = round(((
                                                               movement_related_parties_sum + movement_related_parties_account) * -1),
                                                      2)
                    movement_related_parties_list.append(
                        movement_related_partiess)

                    movement_related_parties_dict = {
                        'id': 'movement_related_parties',
                        'name': 'Movement in due to related parties',
                        'level': 2,
                        'class': 'cash_flow_line_val_tr',
                        'columns': [
                            {
                                'name': '',
                                'class': 'number'}]
                    }
                    movement_related_parties_dict['columns'][0][
                        'name'] = movement_related_parties_list

            elif options['date_filter'] == 'this_quarter' or options['date_filter'] == 'last_quarter':
                for i in range(0, number_period + 1):
                    from_date = datetime.strptime(options['date']['date_from'],
                                                  "%Y-%m-%d")
                    from_date = from_date + relativedelta(years=-i)
                    current_quarter = round((from_date.month - 1) / 3 + 1)
                    from_date = datetime(from_date.year,
                                         3 * current_quarter - 2, 1)
                    to_date = datetime(from_date.year,
                                       3 * current_quarter + 1,
                                       1) + relativedelta(days=-1)
                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                                                                    and journal_item.company_id = %(company_ids)s
                                                                                                    and journal_item.date >= %(from_date)s 
                                                                                                    and journal_item.date <= %(to_date)s
                                                                                                    and {states_args}
                                                                                                    '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '212101',
                                         'code_end': '212169',
                                         'company_ids': self.env.company.id})
                    movement_related_parties = self.env.cr.dictfetchall()
                    movement_related_parties_credit = \
                        movement_related_parties[0][
                            'credit'] if movement_related_parties[0][
                            'credit'] else 0
                    movement_related_parties_debit = \
                        movement_related_parties[0]['debit'] if \
                            movement_related_parties[0]['debit'] else 0
                    movement_related_parties_sum = movement_related_parties_debit - movement_related_parties_credit
                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                                                                and journal_item.company_id = %(company_ids)s
                                                                                                and journal_item.date >= %(from_date)s 
                                                                                                and journal_item.date <= %(to_date)s
                                                                                                and {states_args}
                                                                                                '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '212171',
                                         'code_end': '212999',
                                         'company_ids': self.env.company.id})
                    movement_related_parties_account = self.env.cr.dictfetchall()
                    movement_related_parties_account_credit = \
                        movement_related_parties_account[0]['credit'] if \
                            movement_related_parties_account[0]['credit'] else 0
                    movement_related_parties_account_debit = \
                        movement_related_parties_account[0]['debit'] if \
                            movement_related_parties_account[0]['debit'] else 0
                    movement_related_parties_account = movement_related_parties_account_debit - movement_related_parties_account_credit
                    movement_related_partiess = round(((
                                                               movement_related_parties_sum + movement_related_parties_account) * -1),
                                                      2)
                    movement_related_parties_list.append(
                        movement_related_partiess)

                    movement_related_parties_dict = {
                        'id': 'movement_related_parties',
                        'name': 'Movement in due to related parties',
                        'level': 2,
                        'class': 'cash_flow_line_val_tr',
                        'columns': [
                            {
                                'name': '',
                                'class': 'number'}]
                    }
                    movement_related_parties_dict['columns'][0][
                        'name'] = movement_related_parties_list
            elif options['date_filter'] == 'this_year' or options['date_filter'] == 'last_year':
                for i in range(0, number_period + 1):
                    from_date = datetime.strptime(options['date']['date_from'],
                                                  "%Y-%m-%d")
                    from_date = from_date - relativedelta(years=i)
                    to_date = from_date.replace(month=12, day=31)
                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                                                                    and journal_item.company_id = %(company_ids)s
                                                                                                    and journal_item.date >= %(from_date)s 
                                                                                                    and journal_item.date <= %(to_date)s
                                                                                                    and {states_args}
                                                                                                    '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '212101',
                                         'code_end': '212169',
                                         'company_ids': self.env.company.id})
                    movement_related_parties = self.env.cr.dictfetchall()
                    movement_related_parties_credit = \
                        movement_related_parties[0][
                            'credit'] if movement_related_parties[0][
                            'credit'] else 0
                    movement_related_parties_debit = \
                        movement_related_parties[0]['debit'] if \
                            movement_related_parties[0]['debit'] else 0
                    movement_related_parties_sum = movement_related_parties_debit - movement_related_parties_credit
                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                                                                and journal_item.company_id = %(company_ids)s
                                                                                                and journal_item.date >= %(from_date)s 
                                                                                                and journal_item.date <= %(to_date)s
                                                                                                and {states_args}
                                                                                                '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '212171',
                                         'code_end': '212999',
                                         'company_ids': self.env.company.id})
                    movement_related_parties_account = self.env.cr.dictfetchall()
                    movement_related_parties_account_credit = \
                        movement_related_parties_account[0]['credit'] if \
                            movement_related_parties_account[0]['credit'] else 0
                    movement_related_parties_account_debit = \
                        movement_related_parties_account[0]['debit'] if \
                            movement_related_parties_account[0]['debit'] else 0
                    movement_related_parties_account = movement_related_parties_account_debit - movement_related_parties_account_credit
                    movement_related_partiess = round(((
                                                               movement_related_parties_sum + movement_related_parties_account) * -1),
                                                      2)
                    movement_related_parties_list.append(
                        movement_related_partiess)

                    movement_related_parties_dict = {
                        'id': 'movement_related_parties',
                        'name': 'Movement in due to related parties',
                        'level': 2,
                        'class': 'cash_flow_line_val_tr',
                        'columns': [
                            {
                                'name': '',
                                'class': 'number'}]
                    }
                    movement_related_parties_dict['columns'][0][
                        'name'] = movement_related_parties_list
        else:
            self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                            and journal_item.company_id = %(company_ids)s
                                                            and journal_item.date >= %(from_date)s 
                                                            and journal_item.date <= %(to_date)s
                                                            and {states_args}
                                                            '''.format(
                states_args=states_args),
                                {'from_date': options['date']['date_from'],
                                 'to_date': options['date']['date_to'],
                                 'code_start': '212101', 'code_end': '212169',
                                 'company_ids': self.env.company.id})
            movement_related_parties = self.env.cr.dictfetchall()
            movement_related_parties_credit = movement_related_parties[0][
                'credit'] if movement_related_parties[0]['credit'] else 0
            movement_related_parties_debit = movement_related_parties[0][
                'debit'] if \
                movement_related_parties[0]['debit'] else 0
            movement_related_parties_sum = movement_related_parties_debit - movement_related_parties_credit
            movement_related_parties_account = self._get_movement_related_parties_account(
                query, options, states_args)
            movement_related_partiess = round(((
                                                       movement_related_parties_sum + movement_related_parties_account) * -1),
                                              2)
            movement_related_parties_list.append(
                movement_related_partiess)

            movement_related_parties_dict = {
                'id': 'movement_related_parties',
                'name': 'Movement in due to related parties',
                'level': 2,
                'class': 'cash_flow_line_val_tr',
                'columns': [
                    {
                        'name': '',
                        'class': 'number'}]
            }
            movement_related_parties_dict['columns'][0][
                'name'] = movement_related_parties_list
        return movement_related_parties_dict

    def movement_capital(self, options, states_args, number_period):
        movement_list = []
        query = '''select sum(journal_item.credit) as credit, sum(journal_item.debit) as debit 
                            from account_move_line as journal_item
                            left join account_account as account on journal_item.account_id = account.id
                            '''

        movement_trade_dict = self.get_movement_trade_dict(query, options,
                                                           states_args,
                                                           number_period)

        movement_list.append(movement_trade_dict)

        movement_related_dict = self.get_movement_related_dict(query, options,
                                                               states_args,
                                                               number_period)

        movement_list.append(movement_related_dict)

        movement_trade_payable_dict = self.get_movement_trade_payable_dict(
            query, options, states_args, number_period)
        movement_list.append(movement_trade_payable_dict)
        movement_related_parties_dict = self.get_movement_related_parties_dict(
            query, options, states_args, number_period)
        movement_list.append(movement_related_parties_dict)
        return movement_list

    def _get_movement_related_parties_account(self, query, options,
                                              states_args):
        self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                                and journal_item.company_id = %(company_ids)s
                                                                and journal_item.date >= %(from_date)s 
                                                                and journal_item.date <= %(to_date)s
                                                                and {states_args}
                                                                '''.format(
            states_args=states_args),
                            {'from_date': options['date']['date_from'],
                             'to_date': options['date']['date_to'],
                             'code_start': '212171', 'code_end': '212999',
                             'company_ids': self.env.company.id})
        movement_related_parties_account = self.env.cr.dictfetchall()
        movement_related_parties_account_credit = \
            movement_related_parties_account[0]['credit'] if \
                movement_related_parties_account[0]['credit'] else 0
        movement_related_parties_account_debit = \
            movement_related_parties_account[0]['debit'] if \
                movement_related_parties_account[0]['debit'] else 0
        return movement_related_parties_account_debit - movement_related_parties_account_credit

    def get_purchase_asset_account_sum(self, query, options, states_args):
        self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                        and journal_item.company_id = %(company_ids)s
                                                        and journal_item.date >= %(from_date)s 
                                                        and journal_item.date <= %(to_date)s
                                                        and {states_args}
                                                        '''.format(
            states_args=states_args),
                            {'from_date': options['date']['date_from'],
                             'to_date': options['date']['date_to'],
                             'code_start': '121101', 'code_end': '121199',
                             'company_ids': self.env.company.id})
        purchase_asset_account = self.env.cr.dictfetchall()
        purchase_asset_account_credit = purchase_asset_account[0]['credit'] if \
            purchase_asset_account[0]['credit'] else 0
        purchase_asset_account_debit = purchase_asset_account[0]['debit'] if \
            purchase_asset_account[0]['debit'] else 0
        return purchase_asset_account_debit - purchase_asset_account_credit

    def get_purchase_asset_dict(self, query, options, states_args,
                                number_period):
        purchase_asset_list = []
        if options['comparison']['comparison_type'] == 'previous_period':
            if options['date_filter'] == 'this_month' or options[
                'date_filter'] == 'last_month':
                for i in range(0, number_period + 1):
                    from_date = datetime.strptime(options['date']['date_from'],
                                                  "%Y-%m-%d")
                    from_date = from_date - relativedelta(months=i)
                    to_date = from_date + relativedelta(months=1)
                    to_date = to_date - relativedelta(days=1)
                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                                        and journal_item.company_id = %(company_ids)s
                                                                        and journal_item.date >= %(from_date)s 
                                                                        and journal_item.date <= %(to_date)s
                                                                        and {states_args}
                                                                        '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '121301',
                                         'code_end': '121399',
                                         'company_ids': self.env.company.id})
                    purchase_asset = self.env.cr.dictfetchall()
                    purchase_asset_credit = purchase_asset[0]['credit'] if \
                        purchase_asset[0]['credit'] else 0
                    purchase_asset_debit = purchase_asset[0]['debit'] if \
                        purchase_asset[0][
                            'debit'] else 0
                    purchase_asset_sum = purchase_asset_debit - purchase_asset_credit
                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                                    and journal_item.company_id = %(company_ids)s
                                                                    and journal_item.date >= %(from_date)s 
                                                                    and journal_item.date <= %(to_date)s
                                                                    and {states_args}
                                                                    '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '121101',
                                         'code_end': '121199',
                                         'company_ids': self.env.company.id})
                    purchase_asset_account = self.env.cr.dictfetchall()
                    purchase_asset_account_credit = purchase_asset_account[0][
                        'credit'] if \
                        purchase_asset_account[0]['credit'] else 0
                    purchase_asset_account_debit = purchase_asset_account[0][
                        'debit'] if \
                        purchase_asset_account[0]['debit'] else 0
                    purchase_asset_account_sum = purchase_asset_account_debit - purchase_asset_account_credit
                    purchase_asset_val = round(((
                                                        purchase_asset_sum + purchase_asset_account_sum) * -1),
                                               2)
                    purchase_asset_list.append(purchase_asset_val)

                purchase_asset_dict = {
                    'id': 'purchase_asset',
                    'name': 'Purchase of fixed assets',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {
                            'name': '',
                            'class': 'number'}]
                }
                purchase_asset_dict['columns'][0]['name'] = purchase_asset_list
            elif options['date_filter'] == 'this_quarter' or options['date_filter'] == 'last_quarter':
                for i in range(0, number_period + 1):
                    from_date = datetime.strptime(options['date']['date_from'],
                                                  "%Y-%m-%d")
                    from_date = from_date + relativedelta(months=-3 * i)
                    current_quarter = round((from_date.month - 1) / 3 + 1)
                    from_date = datetime(from_date.year,
                                         3 * current_quarter - 2, 1)
                    to_date = datetime(from_date.year,
                                       3 * current_quarter + 1,
                                       1) + relativedelta(days=-1)
                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                                                            and journal_item.company_id = %(company_ids)s
                                                                                            and journal_item.date >= %(from_date)s 
                                                                                            and journal_item.date <= %(to_date)s
                                                                                            and {states_args}
                                                                                            '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '121301',
                                         'code_end': '121399',
                                         'company_ids': self.env.company.id})
                    purchase_asset = self.env.cr.dictfetchall()
                    purchase_asset_credit = purchase_asset[0]['credit'] if \
                        purchase_asset[0]['credit'] else 0
                    purchase_asset_debit = purchase_asset[0]['debit'] if \
                        purchase_asset[0][
                            'debit'] else 0
                    purchase_asset_sum = purchase_asset_debit - purchase_asset_credit
                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                                                        and journal_item.company_id = %(company_ids)s
                                                                                        and journal_item.date >= %(from_date)s 
                                                                                        and journal_item.date <= %(to_date)s
                                                                                        and {states_args}
                                                                                        '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '121101',
                                         'code_end': '121199',
                                         'company_ids': self.env.company.id})
                    purchase_asset_account = self.env.cr.dictfetchall()
                    purchase_asset_account_credit = purchase_asset_account[0][
                        'credit'] if \
                        purchase_asset_account[0]['credit'] else 0
                    purchase_asset_account_debit = purchase_asset_account[0][
                        'debit'] if \
                        purchase_asset_account[0]['debit'] else 0
                    purchase_asset_account_sum = purchase_asset_account_debit - purchase_asset_account_credit
                    purchase_asset_val = round(((
                                                        purchase_asset_sum + purchase_asset_account_sum) * -1),
                                               2)
                    purchase_asset_list.append(purchase_asset_val)

                purchase_asset_dict = {
                    'id': 'purchase_asset',
                    'name': 'Purchase of fixed assets',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {
                            'name': '',
                            'class': 'number'}]
                }
                purchase_asset_dict['columns'][0]['name'] = purchase_asset_list
            elif options['date_filter'] == 'this_year' or options['date_filter'] == 'last_year':
                for i in range(0, number_period + 1):
                    from_date = datetime.strptime(options['date']['date_from'],
                                                  "%Y-%m-%d")
                    from_date = from_date - relativedelta(years=i)
                    to_date = from_date.replace(month=12, day=31)
                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                                                                and journal_item.company_id = %(company_ids)s
                                                                                                and journal_item.date >= %(from_date)s 
                                                                                                and journal_item.date <= %(to_date)s
                                                                                                and {states_args}
                                                                                                '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '121301',
                                         'code_end': '121399',
                                         'company_ids': self.env.company.id})
                    purchase_asset = self.env.cr.dictfetchall()
                    purchase_asset_credit = purchase_asset[0]['credit'] if \
                        purchase_asset[0]['credit'] else 0
                    purchase_asset_debit = purchase_asset[0]['debit'] if \
                        purchase_asset[0][
                            'debit'] else 0
                    purchase_asset_sum = purchase_asset_debit - purchase_asset_credit
                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                                                            and journal_item.company_id = %(company_ids)s
                                                                                            and journal_item.date >= %(from_date)s 
                                                                                            and journal_item.date <= %(to_date)s
                                                                                            and {states_args}
                                                                                            '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '121101',
                                         'code_end': '121199',
                                         'company_ids': self.env.company.id})
                    purchase_asset_account = self.env.cr.dictfetchall()
                    purchase_asset_account_credit = purchase_asset_account[0][
                        'credit'] if \
                        purchase_asset_account[0]['credit'] else 0
                    purchase_asset_account_debit = purchase_asset_account[0][
                        'debit'] if \
                        purchase_asset_account[0]['debit'] else 0
                    purchase_asset_account_sum = purchase_asset_account_debit - purchase_asset_account_credit
                    purchase_asset_val = round(((
                                                        purchase_asset_sum + purchase_asset_account_sum) * -1),
                                               2)
                    purchase_asset_list.append(purchase_asset_val)

                purchase_asset_dict = {
                    'id': 'purchase_asset',
                    'name': 'Purchase of fixed assets',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {
                            'name': '',
                            'class': 'number'}]
                }
                purchase_asset_dict['columns'][0]['name'] = purchase_asset_list

        elif options['comparison'][
            'comparison_type'] == 'same_period_last_year':
            if options['date_filter'] == 'this_month' or options[
                'date_filter'] == 'last_month':
                for j in range(0, number_period + 1):
                    from_date = datetime.strptime(options['date']['date_from'],
                                                  "%Y-%m-%d")
                    from_date = from_date - relativedelta(years=j)
                    to_date = from_date + relativedelta(months=1)
                    to_date = to_date - relativedelta(days=1)
                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                                                            and journal_item.company_id = %(company_ids)s
                                                                                            and journal_item.date >= %(from_date)s 
                                                                                            and journal_item.date <= %(to_date)s
                                                                                            and {states_args}
                                                                                            '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '121301',
                                         'code_end': '121399',
                                         'company_ids': self.env.company.id})
                    purchase_asset = self.env.cr.dictfetchall()
                    purchase_asset_credit = purchase_asset[0]['credit'] if \
                        purchase_asset[0]['credit'] else 0
                    purchase_asset_debit = purchase_asset[0]['debit'] if \
                        purchase_asset[0][
                            'debit'] else 0
                    purchase_asset_sum = purchase_asset_debit - purchase_asset_credit
                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                                            and journal_item.company_id = %(company_ids)s
                                                                            and journal_item.date >= %(from_date)s 
                                                                            and journal_item.date <= %(to_date)s
                                                                            and {states_args}
                                                                            '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '121101',
                                         'code_end': '121199',
                                         'company_ids': self.env.company.id})
                    purchase_asset_account = self.env.cr.dictfetchall()
                    purchase_asset_account_credit = purchase_asset_account[0][
                        'credit'] if \
                        purchase_asset_account[0]['credit'] else 0
                    purchase_asset_account_debit = purchase_asset_account[0][
                        'debit'] if \
                        purchase_asset_account[0]['debit'] else 0
                    purchase_asset_account_sum = purchase_asset_account_debit - purchase_asset_account_credit
                    purchase_asset_val = round(((
                                                        purchase_asset_sum + purchase_asset_account_sum) * -1),
                                               2)
                    purchase_asset_list.append(purchase_asset_val)

                purchase_asset_dict = {
                    'id': 'purchase_asset',
                    'name': 'Purchase of fixed assets',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {
                            'name': '',
                            'class': 'number'}]
                }
                purchase_asset_dict['columns'][0]['name'] = purchase_asset_list
            elif options['date_filter'] == 'this_quarter' or options['date_filter'] == 'last_quarter':
                for i in range(0, number_period + 1):
                    from_date = datetime.strptime(options['date']['date_from'],
                                                  "%Y-%m-%d")
                    from_date = from_date + relativedelta(years=-i)
                    current_quarter = round((from_date.month - 1) / 3 + 1)
                    from_date = datetime(from_date.year,
                                         3 * current_quarter - 2, 1)
                    to_date = datetime(from_date.year,
                                       3 * current_quarter + 1,
                                       1) + relativedelta(days=-1)
                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                                                                                and journal_item.company_id = %(company_ids)s
                                                                                                                and journal_item.date >= %(from_date)s 
                                                                                                                and journal_item.date <= %(to_date)s
                                                                                                                and {states_args}
                                                                                                                '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '121301',
                                         'code_end': '121399',
                                         'company_ids': self.env.company.id})
                    purchase_asset = self.env.cr.dictfetchall()
                    purchase_asset_credit = purchase_asset[0]['credit'] if \
                        purchase_asset[0]['credit'] else 0
                    purchase_asset_debit = purchase_asset[0]['debit'] if \
                        purchase_asset[0][
                            'debit'] else 0
                    purchase_asset_sum = purchase_asset_debit - purchase_asset_credit
                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                                                                and journal_item.company_id = %(company_ids)s
                                                                                                and journal_item.date >= %(from_date)s 
                                                                                                and journal_item.date <= %(to_date)s
                                                                                                and {states_args}
                                                                                                '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '121101',
                                         'code_end': '121199',
                                         'company_ids': self.env.company.id})
                    purchase_asset_account = self.env.cr.dictfetchall()
                    purchase_asset_account_credit = purchase_asset_account[0][
                        'credit'] if \
                        purchase_asset_account[0]['credit'] else 0
                    purchase_asset_account_debit = purchase_asset_account[0][
                        'debit'] if \
                        purchase_asset_account[0]['debit'] else 0
                    purchase_asset_account_sum = purchase_asset_account_debit - purchase_asset_account_credit

                    purchase_asset_val = round(((
                                                        purchase_asset_sum + purchase_asset_account_sum) * -1),
                                               2)
                    purchase_asset_list.append(purchase_asset_val)

                purchase_asset_dict = {
                    'id': 'purchase_asset',
                    'name': 'Purchase of fixed assets',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {
                            'name': '',
                            'class': 'number'}]
                }
                purchase_asset_dict['columns'][0]['name'] = purchase_asset_list
            elif options['date_filter'] == 'this_year' or options['date_filter'] == 'last_year':
                for i in range(0, number_period + 1):
                    from_date = datetime.strptime(options['date']['date_from'],
                                                  "%Y-%m-%d")
                    from_date = from_date - relativedelta(years=i)
                    to_date = from_date.replace(month=12, day=31)
                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                                                                                    and journal_item.company_id = %(company_ids)s
                                                                                                                    and journal_item.date >= %(from_date)s 
                                                                                                                    and journal_item.date <= %(to_date)s
                                                                                                                    and {states_args}
                                                                                                                    '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '121301',
                                         'code_end': '121399',
                                         'company_ids': self.env.company.id})
                    purchase_asset = self.env.cr.dictfetchall()
                    purchase_asset_credit = purchase_asset[0]['credit'] if \
                        purchase_asset[0]['credit'] else 0
                    purchase_asset_debit = purchase_asset[0]['debit'] if \
                        purchase_asset[0][
                            'debit'] else 0
                    purchase_asset_sum = purchase_asset_debit - purchase_asset_credit
                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                                                                    and journal_item.company_id = %(company_ids)s
                                                                                                    and journal_item.date >= %(from_date)s 
                                                                                                    and journal_item.date <= %(to_date)s
                                                                                                    and {states_args}
                                                                                                    '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '121101',
                                         'code_end': '121199',
                                         'company_ids': self.env.company.id})
                    purchase_asset_account = self.env.cr.dictfetchall()
                    purchase_asset_account_credit = purchase_asset_account[0][
                        'credit'] if \
                        purchase_asset_account[0]['credit'] else 0
                    purchase_asset_account_debit = purchase_asset_account[0][
                        'debit'] if \
                        purchase_asset_account[0]['debit'] else 0
                    purchase_asset_account_sum = purchase_asset_account_debit - purchase_asset_account_credit

                    purchase_asset_val = round(((
                                                        purchase_asset_sum + purchase_asset_account_sum) * -1),
                                               2)
                    purchase_asset_list.append(purchase_asset_val)

                purchase_asset_dict = {
                    'id': 'purchase_asset',
                    'name': 'Purchase of fixed assets',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {
                            'name': '',
                            'class': 'number'}]
                }
                purchase_asset_dict['columns'][0]['name'] = purchase_asset_list

        else:

            self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                    and journal_item.company_id = %(company_ids)s
                                                    and journal_item.date >= %(from_date)s 
                                                    and journal_item.date <= %(to_date)s
                                                    and {states_args}
                                                    '''.format(
                states_args=states_args),
                                {'from_date': options['date']['date_from'],
                                 'to_date': options['date']['date_to'],
                                 'code_start': '121301', 'code_end': '121399',
                                 'company_ids': self.env.company.id})
            purchase_asset = self.env.cr.dictfetchall()
            purchase_asset_credit = purchase_asset[0]['credit'] if \
                purchase_asset[0]['credit'] else 0
            purchase_asset_debit = purchase_asset[0]['debit'] if \
                purchase_asset[0][
                    'debit'] else 0
            purchase_asset_sum = purchase_asset_debit - purchase_asset_credit
            purchase_asset_account_sum = self.get_purchase_asset_account_sum(
                query,
                options,
                states_args)
            purchase_asset_val = round(((
                                                purchase_asset_sum + purchase_asset_account_sum) * -1),
                                       2)
            purchase_asset_list.append(purchase_asset_val)
            purchase_asset_dict = {
                'id': 'purchase_asset',
                'name': 'Purchase of fixed assets',
                'level': 2,
                'class': 'cash_flow_line_val_tr',
                'columns': [
                    {
                        'name': '',
                        'class': 'number'}]
            }
            purchase_asset_dict['columns'][0]['name'] = purchase_asset_list
        return purchase_asset_dict

    def investing_activities(self, options, states_args, number_period):
        investing_activities_list = []
        query = '''select sum(journal_item.credit) as credit, sum(journal_item.debit) as debit 
                                    from account_move_line as journal_item
                                    left join account_account as account on journal_item.account_id = account.id
                                    '''

        purchase_asset_dict = self.get_purchase_asset_dict(query, options,
                                                           states_args,
                                                           number_period)

        investing_activities_list.append(purchase_asset_dict)
        subsidiary_list = []
        if options['comparison']['comparison_type'] == 'previous_period':
            if options['date_filter'] == 'this_month' or options[
                'date_filter'] == 'last_month':
                for i in range(0, number_period + 1):
                    from_date = datetime.strptime(options['date']['date_from'],
                                                  "%Y-%m-%d")
                    from_date = from_date - relativedelta(months=i)
                    to_date = from_date + relativedelta(months=1)
                    to_date = to_date - relativedelta(days=1)
                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                                and journal_item.company_id = %(company_ids)s
                                                                and journal_item.date >= %(from_date)s 
                                                                and journal_item.date <= %(to_date)s
                                                                and {states_args}
                                                                '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '123101',
                                         'code_end': '123999',
                                         'company_ids': self.env.company.id})
                    subsidiaries = self.env.cr.dictfetchall()
                    subsidiaries_credit = subsidiaries[0]['credit'] if \
                        subsidiaries[0][
                            'credit'] else 0
                    subsidiaries_debit = subsidiaries[0]['debit'] if \
                        subsidiaries[0][
                            'debit'] else 0
                    subsidiary_val = round(
                        ((
                                 subsidiaries_debit - subsidiaries_credit) * -1),
                        2)
                    subsidiary_list.append(subsidiary_val)
                subsidiaries_dict = {
                    'id': 'subsidiaries',
                    'name': 'Investment in subsidiaries',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {
                            'name': '',
                            'class': 'number'}]
                }
                subsidiaries_dict['columns'][0]['name'] = subsidiary_list
                investing_activities_list.append(subsidiaries_dict)
            elif options['date_filter'] == 'this_quarter' or options['date_filter'] == 'last_quarter':
                for i in range(0, number_period + 1):
                    from_date = datetime.strptime(options['date']['date_from'],
                                                  "%Y-%m-%d")
                    from_date = from_date + relativedelta(months=-3 * i)
                    current_quarter = round((from_date.month - 1) / 3 + 1)
                    from_date = datetime(from_date.year,
                                         3 * current_quarter - 2, 1)
                    to_date = datetime(from_date.year,
                                       3 * current_quarter + 1,
                                       1) + relativedelta(days=-1)
                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                                                    and journal_item.company_id = %(company_ids)s
                                                                                    and journal_item.date >= %(from_date)s 
                                                                                    and journal_item.date <= %(to_date)s
                                                                                    and {states_args}
                                                                                    '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '123101',
                                         'code_end': '123999',
                                         'company_ids': self.env.company.id})
                    subsidiaries = self.env.cr.dictfetchall()
                    subsidiaries_credit = subsidiaries[0]['credit'] if \
                        subsidiaries[0][
                            'credit'] else 0
                    subsidiaries_debit = subsidiaries[0]['debit'] if \
                        subsidiaries[0][
                            'debit'] else 0
                    subsidiary_val = round(
                        ((
                                 subsidiaries_debit - subsidiaries_credit) * -1),
                        2)
                    subsidiary_list.append(subsidiary_val)
                subsidiaries_dict = {
                    'id': 'subsidiaries',
                    'name': 'Investment in subsidiaries',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {
                            'name': '',
                            'class': 'number'}]
                }
                subsidiaries_dict['columns'][0]['name'] = subsidiary_list
                investing_activities_list.append(subsidiaries_dict)
            elif options['date_filter'] == 'this_year' or options['date_filter'] == 'last_year':
                for i in range(0, number_period + 1):
                    from_date = datetime.strptime(options['date']['date_from'],
                                                  "%Y-%m-%d")
                    from_date = from_date - relativedelta(years=i)
                    to_date = from_date.replace(month=12, day=31)
                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                                                        and journal_item.company_id = %(company_ids)s
                                                                                        and journal_item.date >= %(from_date)s 
                                                                                        and journal_item.date <= %(to_date)s
                                                                                        and {states_args}
                                                                                        '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '123101',
                                         'code_end': '123999',
                                         'company_ids': self.env.company.id})
                    subsidiaries = self.env.cr.dictfetchall()
                    subsidiaries_credit = subsidiaries[0]['credit'] if \
                        subsidiaries[0][
                            'credit'] else 0
                    subsidiaries_debit = subsidiaries[0]['debit'] if \
                        subsidiaries[0][
                            'debit'] else 0
                    subsidiary_val = round(
                        ((
                                 subsidiaries_debit - subsidiaries_credit) * -1),
                        2)
                    subsidiary_list.append(subsidiary_val)
                subsidiaries_dict = {
                    'id': 'subsidiaries',
                    'name': 'Investment in subsidiaries',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {
                            'name': '',
                            'class': 'number'}]
                }
                subsidiaries_dict['columns'][0]['name'] = subsidiary_list
                investing_activities_list.append(subsidiaries_dict)


        elif options['comparison'][
            'comparison_type'] == 'same_period_last_year':
            if options['date_filter'] == 'this_month' or options[
                'date_filter'] == 'last_month':
                for j in range(0, number_period + 1):
                    from_date = datetime.strptime(options['date']['date_from'],
                                                  "%Y-%m-%d")
                    from_date = from_date - relativedelta(years=j)
                    to_date = from_date + relativedelta(months=1)
                    to_date = to_date - relativedelta(days=1)
                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                                                    and journal_item.company_id = %(company_ids)s
                                                                                    and journal_item.date >= %(from_date)s 
                                                                                    and journal_item.date <= %(to_date)s
                                                                                    and {states_args}
                                                                                    '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '123101',
                                         'code_end': '123999',
                                         'company_ids': self.env.company.id})
                    subsidiaries = self.env.cr.dictfetchall()
                    subsidiaries_credit = subsidiaries[0]['credit'] if \
                        subsidiaries[0][
                            'credit'] else 0
                    subsidiaries_debit = subsidiaries[0]['debit'] if \
                        subsidiaries[0][
                            'debit'] else 0
                    subsidiary_val = round(
                        ((
                                 subsidiaries_debit - subsidiaries_credit) * -1),
                        2)
                    subsidiary_list.append(subsidiary_val)
                subsidiaries_dict = {
                    'id': 'subsidiaries',
                    'name': 'Investment in subsidiaries',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {
                            'name': '',
                            'class': 'number'}]
                }
                subsidiaries_dict['columns'][0]['name'] = subsidiary_list
                investing_activities_list.append(subsidiaries_dict)
            elif options['date_filter'] == 'this_quarter' or options['date_filter'] == 'last_quarter':
                for i in range(0, number_period + 1):
                    from_date = datetime.strptime(options['date']['date_from'],
                                                  "%Y-%m-%d")
                    from_date = from_date + relativedelta(years=-i)
                    current_quarter = round((from_date.month - 1) / 3 + 1)
                    from_date = datetime(from_date.year,
                                         3 * current_quarter - 2, 1)
                    to_date = datetime(from_date.year,
                                       3 * current_quarter + 1,
                                       1) + relativedelta(days=-1)
                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                                                                        and journal_item.company_id = %(company_ids)s
                                                                                                        and journal_item.date >= %(from_date)s 
                                                                                                        and journal_item.date <= %(to_date)s
                                                                                                        and {states_args}
                                                                                                        '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '123101',
                                         'code_end': '123999',
                                         'company_ids': self.env.company.id})
                    subsidiaries = self.env.cr.dictfetchall()
                    subsidiaries_credit = subsidiaries[0]['credit'] if \
                        subsidiaries[0][
                            'credit'] else 0
                    subsidiaries_debit = subsidiaries[0]['debit'] if \
                        subsidiaries[0][
                            'debit'] else 0
                    subsidiary_val = round(
                        ((
                                 subsidiaries_debit - subsidiaries_credit) * -1),
                        2)
                    subsidiary_list.append(subsidiary_val)
                subsidiaries_dict = {
                    'id': 'subsidiaries',
                    'name': 'Investment in subsidiaries',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {
                            'name': '',
                            'class': 'number'}]
                }
                subsidiaries_dict['columns'][0]['name'] = subsidiary_list
                investing_activities_list.append(subsidiaries_dict)

            elif options['date_filter'] == 'this_year' or options['date_filter'] == 'last_year':
                for i in range(0, number_period + 1):
                    from_date = datetime.strptime(options['date']['date_from'],
                                                  "%Y-%m-%d")
                    from_date = from_date - relativedelta(years=i)
                    to_date = from_date.replace(month=12, day=31)
                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                                                                            and journal_item.company_id = %(company_ids)s
                                                                                                            and journal_item.date >= %(from_date)s 
                                                                                                            and journal_item.date <= %(to_date)s
                                                                                                            and {states_args}
                                                                                                            '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '123101',
                                         'code_end': '123999',
                                         'company_ids': self.env.company.id})
                    subsidiaries = self.env.cr.dictfetchall()
                    subsidiaries_credit = subsidiaries[0]['credit'] if \
                        subsidiaries[0][
                            'credit'] else 0
                    subsidiaries_debit = subsidiaries[0]['debit'] if \
                        subsidiaries[0][
                            'debit'] else 0
                    subsidiary_val = round(
                        ((
                                 subsidiaries_debit - subsidiaries_credit) * -1),
                        2)
                    subsidiary_list.append(subsidiary_val)
                subsidiaries_dict = {
                    'id': 'subsidiaries',
                    'name': 'Investment in subsidiaries',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {
                            'name': '',
                            'class': 'number'}]
                }
                subsidiaries_dict['columns'][0]['name'] = subsidiary_list
                investing_activities_list.append(subsidiaries_dict)
        else:
            self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                            and journal_item.company_id = %(company_ids)s
                                            and journal_item.date >= %(from_date)s 
                                            and journal_item.date <= %(to_date)s
                                            and {states_args}
                                            '''.format(states_args=states_args),
                                {'from_date': options['date']['date_from'],
                                 'to_date': options['date']['date_to'],
                                 'code_start': '123101', 'code_end': '123999',
                                 'company_ids': self.env.company.id})
            subsidiaries = self.env.cr.dictfetchall()
            subsidiaries_credit = subsidiaries[0]['credit'] if subsidiaries[0][
                'credit'] else 0
            subsidiaries_debit = subsidiaries[0]['debit'] if subsidiaries[0][
                'debit'] else 0
            subsidiary_val = round(
                ((
                         subsidiaries_debit - subsidiaries_credit) * -1),
                2)
            subsidiary_list.append(subsidiary_val)
            subsidiaries_dict = {
                'id': 'subsidiaries',
                'name': 'Investment in subsidiaries',
                'level': 2,
                'class': 'cash_flow_line_val_tr',
                'columns': [
                    {
                        'name': '',
                        'class': 'number'}]
            }
            subsidiaries_dict['columns'][0]['name'] = subsidiary_list
            investing_activities_list.append(subsidiaries_dict)

        return investing_activities_list

    def zain_loan_account(self, query, states_args, options, number_period):
        zain_loan_account_sum_list = []

        if options['comparison']['comparison_type'] == 'previous_period':
            if options['date_filter'] == 'this_month' or options[
                'date_filter'] == 'last_month':
                for i in range(0, number_period + 1):
                    from_date = datetime.strptime(options['date']['date_from'],
                                                  "%Y-%m-%d")
                    from_date = from_date - relativedelta(months=i)
                    to_date = from_date + relativedelta(months=1)
                    to_date = to_date - relativedelta(days=1)
                    self.env.cr.execute(query + '''where account.code = %(account_code)s
                                                                        and journal_item.company_id = %(company_ids)s
                                                                        and journal_item.date >= %(from_date)s 
                                                                        and journal_item.date <= %(to_date)s
                                                                        and {states_args}
                                                                        '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'account_code': '212170',
                                         'company_ids': self.env.company.id})
                    zain_loan_account_fetch = self.env.cr.dictfetchall()
                    zain_loan_account_sum = zain_loan_account_fetch[0][
                        'debit'] if \
                        zain_loan_account_fetch[0][
                            'debit'] else 0 - zain_loan_account_fetch[0][
                        'credit'] if \
                        zain_loan_account_fetch[0][
                            'credit'] else 0
                    zain_loan_account_sum_list.append(zain_loan_account_sum)
            elif options['date_filter'] == 'this_quarter' or options['date_filter'] == 'last_quarter':
                for i in range(0, number_period + 1):
                    from_date = datetime.strptime(options['date']['date_from'],
                                                  "%Y-%m-%d")
                    from_date = from_date + relativedelta(months=-3 * i)
                    current_quarter = round((from_date.month - 1) / 3 + 1)
                    from_date = datetime(from_date.year,
                                         3 * current_quarter - 2, 1)
                    to_date = datetime(from_date.year,
                                       3 * current_quarter + 1,
                                       1) + relativedelta(days=-1)
                    self.env.cr.execute(query + '''where account.code = %(account_code)s
                                                                                            and journal_item.company_id = %(company_ids)s
                                                                                            and journal_item.date >= %(from_date)s 
                                                                                            and journal_item.date <= %(to_date)s
                                                                                            and {states_args}
                                                                                            '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'account_code': '212170',
                                         'company_ids': self.env.company.id})
                    zain_loan_account_fetch = self.env.cr.dictfetchall()
                    zain_loan_account_sum = zain_loan_account_fetch[0][
                        'debit'] if \
                        zain_loan_account_fetch[0][
                            'debit'] else 0 - zain_loan_account_fetch[0][
                        'credit'] if \
                        zain_loan_account_fetch[0][
                            'credit'] else 0
                    zain_loan_account_sum_list.append(zain_loan_account_sum)
            elif options['date_filter'] == 'this_year' or options['date_filter'] == 'last_year':
                for i in range(0, number_period + 1):
                    from_date = datetime.strptime(options['date']['date_from'],
                                                  "%Y-%m-%d")
                    from_date = from_date - relativedelta(years=i)
                    to_date = from_date.replace(month=12, day=31)
                    self.env.cr.execute(query + '''where account.code = %(account_code)s
                                                                                            and journal_item.company_id = %(company_ids)s
                                                                                            and journal_item.date >= %(from_date)s 
                                                                                            and journal_item.date <= %(to_date)s
                                                                                            and {states_args}
                                                                                            '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'account_code': '212170',
                                         'company_ids': self.env.company.id})
                    zain_loan_account_fetch = self.env.cr.dictfetchall()
                    zain_loan_account_sum = zain_loan_account_fetch[0][
                        'debit'] if \
                        zain_loan_account_fetch[0][
                            'debit'] else 0 - zain_loan_account_fetch[0][
                        'credit'] if \
                        zain_loan_account_fetch[0][
                            'credit'] else 0
                    zain_loan_account_sum_list.append(zain_loan_account_sum)
        elif options['comparison'][
            'comparison_type'] == 'same_period_last_year':
            if options['date_filter'] == 'this_month' or options[
                'date_filter'] == 'last_month':
                for j in range(0, number_period + 1):
                    from_date = datetime.strptime(options['date']['date_from'],
                                                  "%Y-%m-%d")
                    from_date = from_date - relativedelta(years=j)
                    to_date = from_date + relativedelta(months=1)
                    to_date = to_date - relativedelta(days=1)
                    self.env.cr.execute(query + '''where account.code = %(account_code)s
                                                                                            and journal_item.company_id = %(company_ids)s
                                                                                            and journal_item.date >= %(from_date)s 
                                                                                            and journal_item.date <= %(to_date)s
                                                                                            and {states_args}
                                                                                            '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'account_code': '212170',
                                         'company_ids': self.env.company.id})
                    zain_loan_account_fetch = self.env.cr.dictfetchall()
                    zain_loan_account_sum = zain_loan_account_fetch[0][
                        'debit'] if \
                        zain_loan_account_fetch[0][
                            'debit'] else 0 - zain_loan_account_fetch[0][
                        'credit'] if \
                        zain_loan_account_fetch[0][
                            'credit'] else 0
                    zain_loan_account_sum_list.append(zain_loan_account_sum)
            elif options['date_filter'] == 'this_quarter' or options['date_filter'] == 'last_quarter':
                for i in range(0, number_period + 1):
                    from_date = datetime.strptime(options['date']['date_from'],
                                                  "%Y-%m-%d")
                    from_date = from_date + relativedelta(years=-i)
                    current_quarter = round((from_date.month - 1) / 3 + 1)
                    from_date = datetime(from_date.year,
                                         3 * current_quarter - 2, 1)
                    to_date = datetime(from_date.year,
                                       3 * current_quarter + 1,
                                       1) + relativedelta(days=-1)
                    self.env.cr.execute(query + '''where account.code = %(account_code)s
                                                                                            and journal_item.company_id = %(company_ids)s
                                                                                            and journal_item.date >= %(from_date)s 
                                                                                            and journal_item.date <= %(to_date)s
                                                                                            and {states_args}
                                                                                            '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'account_code': '212170',
                                         'company_ids': self.env.company.id})
                    zain_loan_account_fetch = self.env.cr.dictfetchall()
                    zain_loan_account_sum = zain_loan_account_fetch[0][
                        'debit'] if \
                        zain_loan_account_fetch[0][
                            'debit'] else 0 - zain_loan_account_fetch[0][
                        'credit'] if \
                        zain_loan_account_fetch[0][
                            'credit'] else 0
                    zain_loan_account_sum_list.append(zain_loan_account_sum)
            elif options['date_filter'] == 'this_year' or options['date_filter'] == 'last_year':
                for i in range(0, number_period + 1):
                    from_date = datetime.strptime(options['date']['date_from'],
                                                  "%Y-%m-%d")
                    from_date = from_date - relativedelta(years=i)
                    to_date = from_date.replace(month=12, day=31)
                    self.env.cr.execute(query + '''where account.code = %(account_code)s
                                                                                            and journal_item.company_id = %(company_ids)s
                                                                                            and journal_item.date >= %(from_date)s 
                                                                                            and journal_item.date <= %(to_date)s
                                                                                            and {states_args}
                                                                                            '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'account_code': '212170',
                                         'company_ids': self.env.company.id})
                    zain_loan_account_fetch = self.env.cr.dictfetchall()
                    zain_loan_account_sum = zain_loan_account_fetch[0][
                        'debit'] if \
                        zain_loan_account_fetch[0][
                            'debit'] else 0 - zain_loan_account_fetch[0][
                        'credit'] if \
                        zain_loan_account_fetch[0][
                            'credit'] else 0
                    zain_loan_account_sum_list.append(zain_loan_account_sum)
        else:
            self.env.cr.execute(query + '''where account.code = %(account_code)s
                                                    and journal_item.company_id = %(company_ids)s
                                                    and journal_item.date >= %(from_date)s 
                                                    and journal_item.date <= %(to_date)s
                                                    and {states_args}
                                                    '''.format(
                states_args=states_args),
                                {'from_date': options['date']['date_from'],
                                 'to_date': options['date']['date_to'],
                                 'account_code': '212170',
                                 'company_ids': self.env.company.id})
            zain_loan_account_fetch = self.env.cr.dictfetchall()
            zain_loan_account_sum = zain_loan_account_fetch[0]['debit'] if \
                zain_loan_account_fetch[0][
                    'debit'] else 0 - zain_loan_account_fetch[0]['credit'] if \
                zain_loan_account_fetch[0][
                    'credit'] else 0
            zain_loan_account_sum_list.append(zain_loan_account_sum)
        return zain_loan_account_sum_list

    def get_cash_flow_financial(self, options, states_args, number_period):
        cash_flow_financial_list = []

        ordinary_shares_list = []
        premium_shares_list = []
        payment_zain_list = []
        zain_loan_list = []
        payment_lease_list = []
        if options['comparison']['comparison_type'] == 'previous_period':
            if options['date_filter'] == 'this_month' or options[
                'date_filter'] == 'last_month':
                for i in range(0, number_period + 1):
                    from_date = datetime.strptime(options['date']['date_from'],
                                                  "%Y-%m-%d")
                    from_date = from_date - relativedelta(months=i)
                    to_date = from_date + relativedelta(months=1)
                    to_date = to_date - relativedelta(days=1)
                    query = '''select sum(journal_item.credit) as credit, sum(journal_item.debit) as debit 
                                                from account_move_line as journal_item
                                                left join account_account as account on journal_item.account_id = account.id
                                                '''

                    self.env.cr.execute(query + '''where account.code = %(account_code)s
                                                    and journal_item.company_id = %(company_ids)s
                                                    and journal_item.date >= %(from_date)s 
                                                    and journal_item.date <= %(to_date)s
                                                    and {states_args}
                                                    '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'account_code': '311101',
                                         'company_ids': self.env.company.id})
                    ordinary_shares = self.env.cr.dictfetchall()
                    ordinary_shares_credit = ordinary_shares[0]['credit'] if \
                        ordinary_shares[0]['credit'] else 0
                    ordinary_shares_debit = ordinary_shares[0]['debit'] if \
                        ordinary_shares[0]['debit'] else 0

                    ordinary_shares_amt = round(
                        ((
                                 ordinary_shares_debit - ordinary_shares_credit) * -1),
                        2)
                    ordinary_shares_list.append(ordinary_shares_amt)
                    self.env.cr.execute(query + '''where account.code = %(account_code)s
                                                    and journal_item.company_id = %(company_ids)s
                                                    and journal_item.date >= %(from_date)s 
                                                    and journal_item.date <= %(to_date)s
                                                    and {states_args}
                                                    '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'account_code': '321101',
                                         'company_ids': self.env.company.id})
                    premium_shares = self.env.cr.dictfetchall()
                    premium_shares_credit = premium_shares[0]['credit'] if \
                        premium_shares[0]['credit'] else 0
                    premium_shares_debit = premium_shares[0]['debit'] if \
                    premium_shares[0][
                        'debit'] else 0
                    premium_shares_amt = round(
                        ((premium_shares_debit - premium_shares_credit) * -1),
                        2)
                    premium_shares_list.append(premium_shares_amt)
                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                    and journal_item.company_id = %(company_ids)s
                                                    and journal_item.date >= %(from_date)s 
                                                    and journal_item.date <= %(to_date)s
                                                    and {states_args}
                                                    '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '213401',
                                         'code_end': '213499',
                                         'company_ids': self.env.company.id})
                    payment_zain = self.env.cr.dictfetchall()
                    payment_zain_debit = payment_zain[0]['debit'] if \
                    payment_zain[0][
                        'debit'] else 0
                    payment_zain_amt = round(((payment_zain_debit) * -1), 2)
                    payment_zain_list.append(payment_zain_amt)
                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                    and journal_item.company_id = %(company_ids)s
                                                    and journal_item.date >= %(from_date)s 
                                                    and journal_item.date <= %(to_date)s
                                                    and {states_args}
                                                    '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '221101',
                                         'code_end': '223999',
                                         'company_ids': self.env.company.id})
                    zain_loan = self.env.cr.dictfetchall()
                    zain_loan_credit = zain_loan[0]['credit'] if zain_loan[0][
                        'credit'] else 0
                    zain_loan_account_list = self.zain_loan_account(query,
                                                                    states_args,
                                                                    options,
                                                                    number_period)
                    zain_loan_account = zain_loan_account_list[i]
                    zain_loan_amt = round(
                        ((zain_loan_credit + zain_loan_account) * -1),
                        2)
                    zain_loan_list.append(zain_loan_amt)

                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                    and journal_item.company_id = %(company_ids)s
                                                    and journal_item.date >= %(from_date)s 
                                                    and journal_item.date <= %(to_date)s
                                                    and {states_args}
                                                    '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '214101',
                                         'code_end': '214999',
                                         'company_ids': self.env.company.id})
                    payment_lease = self.env.cr.dictfetchall()
                    payment_lease_credit = payment_lease[0]['credit'] if \
                    payment_lease[0][
                        'credit'] else 0
                    payment_lease_debit = payment_lease[0]['debit'] if \
                    payment_lease[0][
                        'debit'] else 0
                    payment_lease_amt = round(
                        ((payment_lease_debit - payment_lease_credit) * -1), 2)
                    payment_lease_list.append(payment_lease_amt)

                ordinary_shares_dict = {
                    'id': 'ordinary_shares',
                    'name': 'Ordinary shares issued @ par value $ 0.01',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {
                            'name': '',
                            'class': 'number'}]
                }
                ordinary_shares_dict['columns'][0][
                    'name'] = ordinary_shares_list
                cash_flow_financial_list.append(ordinary_shares_dict)
                premium_shares_dict = {
                    'id': 'premium_shares',
                    'name': 'Share premium on shares issued to acquire subs',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {
                            'name': '',
                            'class': 'number'}]
                }
                premium_shares_dict['columns'][0]['name'] = premium_shares_list
                cash_flow_financial_list.append(premium_shares_dict)

                payment_zain_dict = {
                    'id': 'payment_zain',
                    'name': 'Payment of interest on Zain loan',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {
                            'name': round(((payment_zain_debit) * -1), 2),
                            'class': 'number'}]
                }
                payment_zain_dict['columns'][0]['name'] = payment_zain_list
                cash_flow_financial_list.append(payment_zain_dict)
                zain_loan_dict = {
                    'id': 'zain_loan',
                    'name': 'Loan from Zain',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {
                            'name': '',
                            'class': 'number'}]
                }
                zain_loan_dict['columns'][0]['name'] = zain_loan_list
                cash_flow_financial_list.append(zain_loan_dict)
                payment_lease_dict = {
                    'id': 'payment_lease',
                    'name': 'Payment of lease liability',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {
                            'name': '',
                            'class': 'number'}]
                }
                payment_lease_dict['columns'][0]['name'] = payment_lease_list
                cash_flow_financial_list.append(payment_lease_dict)
            elif options['date_filter'] == 'this_quarter' or options['date_filter'] == 'last_quarter':
                for i in range(0, number_period + 1):
                    from_date = datetime.strptime(options['date']['date_from'],
                                                  "%Y-%m-%d")
                    from_date = from_date + relativedelta(months=-3 * i)
                    current_quarter = round((from_date.month - 1) / 3 + 1)
                    from_date = datetime(from_date.year,
                                         3 * current_quarter - 2, 1)

                    to_date = datetime(from_date.year,
                                       3 * current_quarter + 1,
                                       1) + relativedelta(days=-1)

                    query = '''select sum(journal_item.credit) as credit, sum(journal_item.debit) as debit 
                                                    from account_move_line as journal_item
                                                    left join account_account as account on journal_item.account_id = account.id
                                                    '''

                    self.env.cr.execute(query + '''where account.code = %(account_code)s
                                                        and journal_item.company_id = %(company_ids)s
                                                        and journal_item.date >= %(from_date)s 
                                                        and journal_item.date <= %(to_date)s
                                                        and {states_args}
                                                        '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'account_code': '311101',
                                         'company_ids': self.env.company.id})
                    ordinary_shares = self.env.cr.dictfetchall()
                    ordinary_shares_credit = ordinary_shares[0]['credit'] if \
                        ordinary_shares[0]['credit'] else 0
                    ordinary_shares_debit = ordinary_shares[0]['debit'] if \
                        ordinary_shares[0]['debit'] else 0

                    ordinary_shares_amt = round(
                        ((
                                 ordinary_shares_debit - ordinary_shares_credit) * -1),
                        2)
                    ordinary_shares_list.append(ordinary_shares_amt)
                    self.env.cr.execute(query + '''where account.code = %(account_code)s
                                                        and journal_item.company_id = %(company_ids)s
                                                        and journal_item.date >= %(from_date)s 
                                                        and journal_item.date <= %(to_date)s
                                                        and {states_args}
                                                        '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'account_code': '321101',
                                         'company_ids': self.env.company.id})
                    premium_shares = self.env.cr.dictfetchall()
                    premium_shares_credit = premium_shares[0]['credit'] if \
                        premium_shares[0]['credit'] else 0
                    premium_shares_debit = premium_shares[0]['debit'] if \
                        premium_shares[0][
                            'debit'] else 0
                    premium_shares_amt = round(
                        ((premium_shares_debit - premium_shares_credit) * -1),
                        2)
                    premium_shares_list.append(premium_shares_amt)
                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                        and journal_item.company_id = %(company_ids)s
                                                        and journal_item.date >= %(from_date)s 
                                                        and journal_item.date <= %(to_date)s
                                                        and {states_args}
                                                        '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '213401',
                                         'code_end': '213499',
                                         'company_ids': self.env.company.id})
                    payment_zain = self.env.cr.dictfetchall()
                    payment_zain_debit = payment_zain[0]['debit'] if \
                        payment_zain[0][
                            'debit'] else 0
                    payment_zain_amt = round(((payment_zain_debit) * -1), 2)
                    payment_zain_list.append(payment_zain_amt)
                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                        and journal_item.company_id = %(company_ids)s
                                                        and journal_item.date >= %(from_date)s 
                                                        and journal_item.date <= %(to_date)s
                                                        and {states_args}
                                                        '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '221101',
                                         'code_end': '223999',
                                         'company_ids': self.env.company.id})
                    zain_loan = self.env.cr.dictfetchall()
                    zain_loan_credit = zain_loan[0]['credit'] if zain_loan[0][
                        'credit'] else 0
                    zain_loan_account_list = self.zain_loan_account(query,
                                                                    states_args,
                                                                    options,
                                                                    number_period)
                    zain_loan_account = zain_loan_account_list[i]
                    zain_loan_amt = round(
                        ((zain_loan_credit + zain_loan_account) * -1),
                        2)
                    zain_loan_list.append(zain_loan_amt)

                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                        and journal_item.company_id = %(company_ids)s
                                                        and journal_item.date >= %(from_date)s 
                                                        and journal_item.date <= %(to_date)s
                                                        and {states_args}
                                                        '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '214101',
                                         'code_end': '214999',
                                         'company_ids': self.env.company.id})
                    payment_lease = self.env.cr.dictfetchall()
                    payment_lease_credit = payment_lease[0]['credit'] if \
                        payment_lease[0][
                            'credit'] else 0
                    payment_lease_debit = payment_lease[0]['debit'] if \
                        payment_lease[0][
                            'debit'] else 0
                    payment_lease_amt = round(
                        ((payment_lease_debit - payment_lease_credit) * -1), 2)
                    payment_lease_list.append(payment_lease_amt)

                ordinary_shares_dict = {
                    'id': 'ordinary_shares',
                    'name': 'Ordinary shares issued @ par value $ 0.01',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {
                            'name': '',
                            'class': 'number'}]
                }
                ordinary_shares_dict['columns'][0][
                    'name'] = ordinary_shares_list
                cash_flow_financial_list.append(ordinary_shares_dict)
                premium_shares_dict = {
                    'id': 'premium_shares',
                    'name': 'Share premium on shares issued to acquire subs',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {
                            'name': '',
                            'class': 'number'}]
                }
                premium_shares_dict['columns'][0]['name'] = premium_shares_list
                cash_flow_financial_list.append(premium_shares_dict)

                payment_zain_dict = {
                    'id': 'payment_zain',
                    'name': 'Payment of interest on Zain loan',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {
                            'name': round(((payment_zain_debit) * -1), 2),
                            'class': 'number'}]
                }
                payment_zain_dict['columns'][0]['name'] = payment_zain_list
                cash_flow_financial_list.append(payment_zain_dict)
                zain_loan_dict = {
                    'id': 'zain_loan',
                    'name': 'Loan from Zain',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {
                            'name': '',
                            'class': 'number'}]
                }
                zain_loan_dict['columns'][0]['name'] = zain_loan_list
                cash_flow_financial_list.append(zain_loan_dict)
                payment_lease_dict = {
                    'id': 'payment_lease',
                    'name': 'Payment of lease liability',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {
                            'name': '',
                            'class': 'number'}]
                }
                payment_lease_dict['columns'][0]['name'] = payment_lease_list
                cash_flow_financial_list.append(payment_lease_dict)
            elif options['date_filter'] == 'this_year' or options['date_filter'] == 'last_year':
                for i in range(0, number_period + 1):
                    from_date = datetime.strptime(options['date']['date_from'],
                                                  "%Y-%m-%d")
                    from_date = from_date - relativedelta(years=i)
                    to_date = from_date.replace(month=12, day=31)
                    query = '''select sum(journal_item.credit) as credit, sum(journal_item.debit) as debit 
                                                        from account_move_line as journal_item
                                                        left join account_account as account on journal_item.account_id = account.id
                                                        '''

                    self.env.cr.execute(query + '''where account.code = %(account_code)s
                                                            and journal_item.company_id = %(company_ids)s
                                                            and journal_item.date >= %(from_date)s 
                                                            and journal_item.date <= %(to_date)s
                                                            and {states_args}
                                                            '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'account_code': '311101',
                                         'company_ids': self.env.company.id})
                    ordinary_shares = self.env.cr.dictfetchall()
                    ordinary_shares_credit = ordinary_shares[0]['credit'] if \
                        ordinary_shares[0]['credit'] else 0
                    ordinary_shares_debit = ordinary_shares[0]['debit'] if \
                        ordinary_shares[0]['debit'] else 0

                    ordinary_shares_amt = round(
                        ((
                                 ordinary_shares_debit - ordinary_shares_credit) * -1),
                        2)
                    ordinary_shares_list.append(ordinary_shares_amt)
                    self.env.cr.execute(query + '''where account.code = %(account_code)s
                                                            and journal_item.company_id = %(company_ids)s
                                                            and journal_item.date >= %(from_date)s 
                                                            and journal_item.date <= %(to_date)s
                                                            and {states_args}
                                                            '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'account_code': '321101',
                                         'company_ids': self.env.company.id})
                    premium_shares = self.env.cr.dictfetchall()
                    premium_shares_credit = premium_shares[0]['credit'] if \
                        premium_shares[0]['credit'] else 0
                    premium_shares_debit = premium_shares[0]['debit'] if \
                        premium_shares[0][
                            'debit'] else 0
                    premium_shares_amt = round(
                        ((premium_shares_debit - premium_shares_credit) * -1),
                        2)
                    premium_shares_list.append(premium_shares_amt)

                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                            and journal_item.company_id = %(company_ids)s
                                                            and journal_item.date >= %(from_date)s 
                                                            and journal_item.date <= %(to_date)s
                                                            and {states_args}
                                                            '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '213401',
                                         'code_end': '213499',
                                         'company_ids': self.env.company.id})
                    payment_zain = self.env.cr.dictfetchall()
                    payment_zain_debit = payment_zain[0]['debit'] if \
                        payment_zain[0][
                            'debit'] else 0
                    payment_zain_amt = round(((payment_zain_debit) * -1), 2)
                    payment_zain_list.append(payment_zain_amt)

                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                            and journal_item.company_id = %(company_ids)s
                                                            and journal_item.date >= %(from_date)s 
                                                            and journal_item.date <= %(to_date)s
                                                            and {states_args}
                                                            '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '221101',
                                         'code_end': '223999',
                                         'company_ids': self.env.company.id})
                    zain_loan = self.env.cr.dictfetchall()
                    zain_loan_credit = zain_loan[0]['credit'] if zain_loan[0][
                        'credit'] else 0
                    zain_loan_account_list = self.zain_loan_account(query,
                                                                    states_args,
                                                                    options,
                                                                    number_period)
                    zain_loan_account = zain_loan_account_list[i]
                    zain_loan_amt = round(
                        ((zain_loan_credit + zain_loan_account) * -1),
                        2)
                    zain_loan_list.append(zain_loan_amt)

                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                            and journal_item.company_id = %(company_ids)s
                                                            and journal_item.date >= %(from_date)s 
                                                            and journal_item.date <= %(to_date)s
                                                            and {states_args}
                                                            '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '214101',
                                         'code_end': '214999',
                                         'company_ids': self.env.company.id})
                    payment_lease = self.env.cr.dictfetchall()
                    payment_lease_credit = payment_lease[0]['credit'] if \
                        payment_lease[0][
                            'credit'] else 0
                    payment_lease_debit = payment_lease[0]['debit'] if \
                        payment_lease[0][
                            'debit'] else 0
                    payment_lease_amt = round(
                        ((payment_lease_debit - payment_lease_credit) * -1), 2)
                    payment_lease_list.append(payment_lease_amt)

                ordinary_shares_dict = {
                    'id': 'ordinary_shares',
                    'name': 'Ordinary shares issued @ par value $ 0.01',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {
                            'name': '',
                            'class': 'number'}]
                }
                ordinary_shares_dict['columns'][0][
                    'name'] = ordinary_shares_list
                cash_flow_financial_list.append(ordinary_shares_dict)
                premium_shares_dict = {
                    'id': 'premium_shares',
                    'name': 'Share premium on shares issued to acquire subs',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {
                            'name': '',
                            'class': 'number'}]
                }
                premium_shares_dict['columns'][0]['name'] = premium_shares_list
                cash_flow_financial_list.append(premium_shares_dict)

                payment_zain_dict = {
                    'id': 'payment_zain',
                    'name': 'Payment of interest on Zain loan',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {
                            'name': round(((payment_zain_debit) * -1), 2),
                            'class': 'number'}]
                }
                payment_zain_dict['columns'][0]['name'] = payment_zain_list
                cash_flow_financial_list.append(payment_zain_dict)
                zain_loan_dict = {
                    'id': 'zain_loan',
                    'name': 'Loan from Zain',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {
                            'name': '',
                            'class': 'number'}]
                }
                zain_loan_dict['columns'][0]['name'] = zain_loan_list
                cash_flow_financial_list.append(zain_loan_dict)
                payment_lease_dict = {
                    'id': 'payment_lease',
                    'name': 'Payment of lease liability',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {
                            'name': '',
                            'class': 'number'}]
                }
                payment_lease_dict['columns'][0]['name'] = payment_lease_list
                cash_flow_financial_list.append(payment_lease_dict)

        elif options['comparison'][
            'comparison_type'] == 'same_period_last_year':
            if options['date_filter'] == 'this_month' or options[
                'date_filter'] == 'last_month':
                for j in range(0, number_period + 1):
                    from_date = datetime.strptime(options['date']['date_from'],
                                                  "%Y-%m-%d")
                    from_date = from_date - relativedelta(years=j)
                    to_date = from_date + relativedelta(months=1)
                    to_date = to_date - relativedelta(days=1)

                    query = '''select sum(journal_item.credit) as credit, sum(journal_item.debit) as debit 
                                                    from account_move_line as journal_item
                                                    left join account_account as account on journal_item.account_id = account.id
                                                    '''

                    self.env.cr.execute(query + '''where account.code = %(account_code)s
                                                        and journal_item.company_id = %(company_ids)s
                                                        and journal_item.date >= %(from_date)s 
                                                        and journal_item.date <= %(to_date)s
                                                        and {states_args}
                                                        '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'account_code': '311101',
                                         'company_ids': self.env.company.id})
                    ordinary_shares = self.env.cr.dictfetchall()
                    ordinary_shares_credit = ordinary_shares[0]['credit'] if \
                        ordinary_shares[0]['credit'] else 0
                    ordinary_shares_debit = ordinary_shares[0]['debit'] if \
                        ordinary_shares[0]['debit'] else 0

                    ordinary_shares_amt = round(
                        ((
                                 ordinary_shares_debit - ordinary_shares_credit) * -1),
                        2)
                    ordinary_shares_list.append(ordinary_shares_amt)

                    self.env.cr.execute(query + '''where account.code = %(account_code)s
                                                        and journal_item.company_id = %(company_ids)s
                                                        and journal_item.date >= %(from_date)s 
                                                        and journal_item.date <= %(to_date)s
                                                        and {states_args}
                                                        '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'account_code': '321101',
                                         'company_ids': self.env.company.id})
                    premium_shares = self.env.cr.dictfetchall()
                    premium_shares_credit = premium_shares[0]['credit'] if \
                        premium_shares[0]['credit'] else 0
                    premium_shares_debit = premium_shares[0]['debit'] if \
                        premium_shares[0][
                            'debit'] else 0
                    premium_shares_amt = round(
                        ((premium_shares_debit - premium_shares_credit) * -1),
                        2)
                    premium_shares_list.append(premium_shares_amt)

                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                        and journal_item.company_id = %(company_ids)s
                                                        and journal_item.date >= %(from_date)s 
                                                        and journal_item.date <= %(to_date)s
                                                        and {states_args}
                                                        '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '213401',
                                         'code_end': '213499',
                                         'company_ids': self.env.company.id})
                    payment_zain = self.env.cr.dictfetchall()
                    payment_zain_debit = payment_zain[0]['debit'] if \
                        payment_zain[0][
                            'debit'] else 0
                    payment_zain_amt = round(((payment_zain_debit) * -1), 2)
                    payment_zain_list.append(payment_zain_amt)

                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                        and journal_item.company_id = %(company_ids)s
                                                        and journal_item.date >= %(from_date)s 
                                                        and journal_item.date <= %(to_date)s
                                                        and {states_args}
                                                        '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '221101',
                                         'code_end': '223999',
                                         'company_ids': self.env.company.id})
                    zain_loan = self.env.cr.dictfetchall()
                    zain_loan_credit = zain_loan[0]['credit'] if zain_loan[0][
                        'credit'] else 0
                    zain_loan_account_list = self.zain_loan_account(query,
                                                                    states_args,
                                                                    options,
                                                                    number_period)
                    zain_loan_account = zain_loan_account_list[j]
                    zain_loan_amt = round(
                        ((zain_loan_credit + zain_loan_account) * -1),
                        2)
                    zain_loan_list.append(zain_loan_amt)

                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                        and journal_item.company_id = %(company_ids)s
                                                        and journal_item.date >= %(from_date)s 
                                                        and journal_item.date <= %(to_date)s
                                                        and {states_args}
                                                        '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '214101',
                                         'code_end': '214999',
                                         'company_ids': self.env.company.id})
                    payment_lease = self.env.cr.dictfetchall()
                    payment_lease_credit = payment_lease[0]['credit'] if \
                        payment_lease[0][
                            'credit'] else 0
                    payment_lease_debit = payment_lease[0]['debit'] if \
                        payment_lease[0][
                            'debit'] else 0
                    payment_lease_amt = round(
                        ((payment_lease_debit - payment_lease_credit) * -1), 2)
                    payment_lease_list.append(payment_lease_amt)

                ordinary_shares_dict = {
                    'id': 'ordinary_shares',
                    'name': 'Ordinary shares issued @ par value $ 0.01',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {
                            'name': '',
                            'class': 'number'}]
                }
                ordinary_shares_dict['columns'][0][
                    'name'] = ordinary_shares_list
                cash_flow_financial_list.append(ordinary_shares_dict)
                premium_shares_dict = {
                    'id': 'premium_shares',
                    'name': 'Share premium on shares issued to acquire subs',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {
                            'name': '',
                            'class': 'number'}]
                }
                premium_shares_dict['columns'][0]['name'] = premium_shares_list
                cash_flow_financial_list.append(premium_shares_dict)

                payment_zain_dict = {
                    'id': 'payment_zain',
                    'name': 'Payment of interest on Zain loan',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {
                            'name': round(((payment_zain_debit) * -1), 2),
                            'class': 'number'}]
                }
                payment_zain_dict['columns'][0]['name'] = payment_zain_list
                cash_flow_financial_list.append(payment_zain_dict)
                zain_loan_dict = {
                    'id': 'zain_loan',
                    'name': 'Loan from Zain',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {
                            'name': '',
                            'class': 'number'}]
                }
                zain_loan_dict['columns'][0]['name'] = zain_loan_list
                cash_flow_financial_list.append(zain_loan_dict)
                payment_lease_dict = {
                    'id': 'payment_lease',
                    'name': 'Payment of lease liability',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {
                            'name': '',
                            'class': 'number'}]
                }
                payment_lease_dict['columns'][0]['name'] = payment_lease_list
                cash_flow_financial_list.append(payment_lease_dict)
            elif options['date_filter'] == 'this_quarter' or options['date_filter'] == 'last_quarter':
                for i in range(0, number_period + 1):
                    from_date = datetime.strptime(options['date']['date_from'],
                                                  "%Y-%m-%d")
                    from_date = from_date + relativedelta(years=-i)
                    current_quarter = round((from_date.month - 1) / 3 + 1)
                    from_date = datetime(from_date.year,
                                         3 * current_quarter - 2, 1)

                    to_date = datetime(from_date.year,
                                       3 * current_quarter + 1,
                                       1) + relativedelta(days=-1)
                    query = '''select sum(journal_item.credit) as credit, sum(journal_item.debit) as debit 
                                                        from account_move_line as journal_item
                                                        left join account_account as account on journal_item.account_id = account.id
                                                        '''

                    self.env.cr.execute(query + '''where account.code = %(account_code)s
                                                            and journal_item.company_id = %(company_ids)s
                                                            and journal_item.date >= %(from_date)s 
                                                            and journal_item.date <= %(to_date)s
                                                            and {states_args}
                                                            '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'account_code': '311101',
                                         'company_ids': self.env.company.id})
                    ordinary_shares = self.env.cr.dictfetchall()
                    ordinary_shares_credit = ordinary_shares[0]['credit'] if \
                        ordinary_shares[0]['credit'] else 0
                    ordinary_shares_debit = ordinary_shares[0]['debit'] if \
                        ordinary_shares[0]['debit'] else 0

                    ordinary_shares_amt = round(
                        ((
                                 ordinary_shares_debit - ordinary_shares_credit) * -1),
                        2)
                    ordinary_shares_list.append(ordinary_shares_amt)

                    self.env.cr.execute(query + '''where account.code = %(account_code)s
                                                            and journal_item.company_id = %(company_ids)s
                                                            and journal_item.date >= %(from_date)s 
                                                            and journal_item.date <= %(to_date)s
                                                            and {states_args}
                                                            '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'account_code': '321101',
                                         'company_ids': self.env.company.id})
                    premium_shares = self.env.cr.dictfetchall()
                    premium_shares_credit = premium_shares[0]['credit'] if \
                        premium_shares[0]['credit'] else 0
                    premium_shares_debit = premium_shares[0]['debit'] if \
                        premium_shares[0][
                            'debit'] else 0
                    premium_shares_amt = round(
                        ((premium_shares_debit - premium_shares_credit) * -1),
                        2)
                    premium_shares_list.append(premium_shares_amt)

                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                            and journal_item.company_id = %(company_ids)s
                                                            and journal_item.date >= %(from_date)s 
                                                            and journal_item.date <= %(to_date)s
                                                            and {states_args}
                                                            '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '213401',
                                         'code_end': '213499',
                                         'company_ids': self.env.company.id})
                    payment_zain = self.env.cr.dictfetchall()
                    payment_zain_debit = payment_zain[0]['debit'] if \
                        payment_zain[0][
                            'debit'] else 0
                    payment_zain_amt = round(((payment_zain_debit) * -1), 2)
                    payment_zain_list.append(payment_zain_amt)

                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                            and journal_item.company_id = %(company_ids)s
                                                            and journal_item.date >= %(from_date)s 
                                                            and journal_item.date <= %(to_date)s
                                                            and {states_args}
                                                            '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '221101',
                                         'code_end': '223999',
                                         'company_ids': self.env.company.id})
                    zain_loan = self.env.cr.dictfetchall()
                    zain_loan_credit = zain_loan[0]['credit'] if zain_loan[0][
                        'credit'] else 0
                    zain_loan_account_list = self.zain_loan_account(query,
                                                                    states_args,
                                                                    options,
                                                                    number_period)
                    zain_loan_account = zain_loan_account_list[i]
                    zain_loan_amt = round(
                        ((zain_loan_credit + zain_loan_account) * -1),
                        2)
                    zain_loan_list.append(zain_loan_amt)

                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                            and journal_item.company_id = %(company_ids)s
                                                            and journal_item.date >= %(from_date)s 
                                                            and journal_item.date <= %(to_date)s
                                                            and {states_args}
                                                            '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '214101',
                                         'code_end': '214999',
                                         'company_ids': self.env.company.id})
                    payment_lease = self.env.cr.dictfetchall()
                    payment_lease_credit = payment_lease[0]['credit'] if \
                        payment_lease[0][
                            'credit'] else 0
                    payment_lease_debit = payment_lease[0]['debit'] if \
                        payment_lease[0][
                            'debit'] else 0
                    payment_lease_amt = round(
                        ((payment_lease_debit - payment_lease_credit) * -1), 2)
                    payment_lease_list.append(payment_lease_amt)

                ordinary_shares_dict = {
                    'id': 'ordinary_shares',
                    'name': 'Ordinary shares issued @ par value $ 0.01',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {
                            'name': '',
                            'class': 'number'}]
                }
                ordinary_shares_dict['columns'][0][
                    'name'] = ordinary_shares_list
                cash_flow_financial_list.append(ordinary_shares_dict)
                premium_shares_dict = {
                    'id': 'premium_shares',
                    'name': 'Share premium on shares issued to acquire subs',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {
                            'name': '',
                            'class': 'number'}]
                }
                premium_shares_dict['columns'][0]['name'] = premium_shares_list
                cash_flow_financial_list.append(premium_shares_dict)

                payment_zain_dict = {
                    'id': 'payment_zain',
                    'name': 'Payment of interest on Zain loan',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {
                            'name': round(((payment_zain_debit) * -1), 2),
                            'class': 'number'}]
                }
                payment_zain_dict['columns'][0]['name'] = payment_zain_list
                cash_flow_financial_list.append(payment_zain_dict)
                zain_loan_dict = {
                    'id': 'zain_loan',
                    'name': 'Loan from Zain',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {
                            'name': '',
                            'class': 'number'}]
                }
                zain_loan_dict['columns'][0]['name'] = zain_loan_list
                cash_flow_financial_list.append(zain_loan_dict)
                payment_lease_dict = {
                    'id': 'payment_lease',
                    'name': 'Payment of lease liability',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {
                            'name': '',
                            'class': 'number'}]
                }
                payment_lease_dict['columns'][0]['name'] = payment_lease_list
                cash_flow_financial_list.append(payment_lease_dict)
            elif options['date_filter'] == 'this_year' or options['date_filter'] == 'last_year':
                for i in range(0, number_period + 1):
                    from_date = datetime.strptime(options['date']['date_from'],
                                                  "%Y-%m-%d")
                    from_date = from_date - relativedelta(years=i)
                    to_date = from_date.replace(month=12, day=31)
                    query = '''select sum(journal_item.credit) as credit, sum(journal_item.debit) as debit 
                                                            from account_move_line as journal_item
                                                            left join account_account as account on journal_item.account_id = account.id
                                                            '''

                    self.env.cr.execute(query + '''where account.code = %(account_code)s
                                                                and journal_item.company_id = %(company_ids)s
                                                                and journal_item.date >= %(from_date)s 
                                                                and journal_item.date <= %(to_date)s
                                                                and {states_args}
                                                                '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'account_code': '311101',
                                         'company_ids': self.env.company.id})
                    ordinary_shares = self.env.cr.dictfetchall()
                    ordinary_shares_credit = ordinary_shares[0]['credit'] if \
                        ordinary_shares[0]['credit'] else 0
                    ordinary_shares_debit = ordinary_shares[0]['debit'] if \
                        ordinary_shares[0]['debit'] else 0

                    ordinary_shares_amt = round(
                        ((
                                 ordinary_shares_debit - ordinary_shares_credit) * -1),
                        2)
                    ordinary_shares_list.append(ordinary_shares_amt)

                    # ordinary_shares_dict = {
                    #     'id': 'ordinary_shares',
                    #     'name': 'Ordinary shares issued @ par value $ 0.01',
                    #     'level': 2,
                    #     'class': 'cash_flow_line_val_tr',
                    #     'columns': [
                    #         {
                    #             'name': round(
                    #                 ((ordinary_shares_debit - ordinary_shares_credit) * -1),
                    #                 2),
                    #             'class': 'number'}]
                    # }
                    # cash_flow_financial_list.append(ordinary_shares_dict)

                    self.env.cr.execute(query + '''where account.code = %(account_code)s
                                                                and journal_item.company_id = %(company_ids)s
                                                                and journal_item.date >= %(from_date)s 
                                                                and journal_item.date <= %(to_date)s
                                                                and {states_args}
                                                                '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'account_code': '321101',
                                         'company_ids': self.env.company.id})
                    premium_shares = self.env.cr.dictfetchall()
                    premium_shares_credit = premium_shares[0]['credit'] if \
                        premium_shares[0]['credit'] else 0
                    premium_shares_debit = premium_shares[0]['debit'] if \
                        premium_shares[0][
                            'debit'] else 0
                    premium_shares_amt = round(
                        ((premium_shares_debit - premium_shares_credit) * -1),
                        2)
                    premium_shares_list.append(premium_shares_amt)
                    # premium_shares_dict = {
                    #     'id': 'premium_shares',
                    #     'name': 'Share premium on shares issued to acquire subs',
                    #     'level': 2,
                    #     'class': 'cash_flow_line_val_tr',
                    #     'columns': [
                    #         {
                    #             'name': '',
                    #             'class': 'number'}]
                    # }
                    # cash_flow_financial_list.append(premium_shares_dict)

                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                                and journal_item.company_id = %(company_ids)s
                                                                and journal_item.date >= %(from_date)s 
                                                                and journal_item.date <= %(to_date)s
                                                                and {states_args}
                                                                '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '213401',
                                         'code_end': '213499',
                                         'company_ids': self.env.company.id})
                    payment_zain = self.env.cr.dictfetchall()
                    payment_zain_debit = payment_zain[0]['debit'] if \
                        payment_zain[0][
                            'debit'] else 0
                    payment_zain_amt = round(((payment_zain_debit) * -1), 2)
                    payment_zain_list.append(payment_zain_amt)
                    # payment_zain_dict = {
                    #     'id': 'payment_zain',
                    #     'name': 'Payment of interest on Zain loan',
                    #     'level': 2,
                    #     'class': 'cash_flow_line_val_tr',
                    #     'columns': [
                    #         {
                    #             'name': round(((payment_zain_debit) * -1), 2),
                    #             'class': 'number'}]
                    # }
                    # cash_flow_financial_list.append(payment_zain_dict)

                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                                and journal_item.company_id = %(company_ids)s
                                                                and journal_item.date >= %(from_date)s 
                                                                and journal_item.date <= %(to_date)s
                                                                and {states_args}
                                                                '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '221101',
                                         'code_end': '223999',
                                         'company_ids': self.env.company.id})
                    zain_loan = self.env.cr.dictfetchall()
                    zain_loan_credit = zain_loan[0]['credit'] if zain_loan[0][
                        'credit'] else 0
                    zain_loan_account_list = self.zain_loan_account(query,
                                                                    states_args,
                                                                    options,
                                                                    number_period)
                    zain_loan_account = zain_loan_account_list[i]
                    zain_loan_amt = round(
                        ((zain_loan_credit + zain_loan_account) * -1),
                        2)
                    zain_loan_list.append(zain_loan_amt)

                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                                and journal_item.company_id = %(company_ids)s
                                                                and journal_item.date >= %(from_date)s 
                                                                and journal_item.date <= %(to_date)s
                                                                and {states_args}
                                                                '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'to_date': to_date,
                                         'code_start': '214101',
                                         'code_end': '214999',
                                         'company_ids': self.env.company.id})
                    payment_lease = self.env.cr.dictfetchall()
                    payment_lease_credit = payment_lease[0]['credit'] if \
                        payment_lease[0][
                            'credit'] else 0
                    payment_lease_debit = payment_lease[0]['debit'] if \
                        payment_lease[0][
                            'debit'] else 0
                    payment_lease_amt = round(
                        ((payment_lease_debit - payment_lease_credit) * -1), 2)
                    payment_lease_list.append(payment_lease_amt)

                ordinary_shares_dict = {
                    'id': 'ordinary_shares',
                    'name': 'Ordinary shares issued @ par value $ 0.01',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {
                            'name': '',
                            'class': 'number'}]
                }
                ordinary_shares_dict['columns'][0][
                    'name'] = ordinary_shares_list
                cash_flow_financial_list.append(ordinary_shares_dict)
                premium_shares_dict = {
                    'id': 'premium_shares',
                    'name': 'Share premium on shares issued to acquire subs',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {
                            'name': '',
                            'class': 'number'}]
                }
                premium_shares_dict['columns'][0]['name'] = premium_shares_list
                cash_flow_financial_list.append(premium_shares_dict)

                payment_zain_dict = {
                    'id': 'payment_zain',
                    'name': 'Payment of interest on Zain loan',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {
                            'name': round(((payment_zain_debit) * -1), 2),
                            'class': 'number'}]
                }
                payment_zain_dict['columns'][0]['name'] = payment_zain_list
                cash_flow_financial_list.append(payment_zain_dict)
                zain_loan_dict = {
                    'id': 'zain_loan',
                    'name': 'Loan from Zain',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {
                            'name': '',
                            'class': 'number'}]
                }
                zain_loan_dict['columns'][0]['name'] = zain_loan_list
                cash_flow_financial_list.append(zain_loan_dict)
                payment_lease_dict = {
                    'id': 'payment_lease',
                    'name': 'Payment of lease liability',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {
                            'name': '',
                            'class': 'number'}]
                }
                payment_lease_dict['columns'][0]['name'] = payment_lease_list
                cash_flow_financial_list.append(payment_lease_dict)

        else:
            query = '''select sum(journal_item.credit) as credit, sum(journal_item.debit) as debit 
                                                            from account_move_line as journal_item
                                                            left join account_account as account on journal_item.account_id = account.id
                                                            '''

            self.env.cr.execute(query + '''where account.code = %(account_code)s
                                                                and journal_item.company_id = %(company_ids)s
                                                                and journal_item.date >= %(from_date)s 
                                                                and journal_item.date <= %(to_date)s
                                                                and {states_args}
                                                                '''.format(
                states_args=states_args),
                                {'from_date': options['date']['date_from'],
                                 'to_date': options['date']['date_to'],
                                 'account_code': '311101',
                                 'company_ids': self.env.company.id})
            ordinary_shares = self.env.cr.dictfetchall()
            ordinary_shares_credit = ordinary_shares[0]['credit'] if \
                ordinary_shares[0]['credit'] else 0
            ordinary_shares_debit = ordinary_shares[0]['debit'] if \
                ordinary_shares[0]['debit'] else 0

            ordinary_shares_amt = round(
                ((
                         ordinary_shares_debit - ordinary_shares_credit) * -1),
                2)
            ordinary_shares_list.append(ordinary_shares_amt)

            ordinary_shares_dict = {
                'id': 'ordinary_shares',
                'name': 'Ordinary shares issued @ par value $ 0.01',
                'level': 2,
                'class': 'cash_flow_line_val_tr',
                'columns': [
                    {
                        'name': ordinary_shares_list,
                        'class': 'number'}]
            }
            cash_flow_financial_list.append(ordinary_shares_dict)

            self.env.cr.execute(query + '''where account.code = %(account_code)s
                                                                and journal_item.company_id = %(company_ids)s
                                                                and journal_item.date >= %(from_date)s 
                                                                and journal_item.date <= %(to_date)s
                                                                and {states_args}
                                                                '''.format(
                states_args=states_args),
                                {'from_date': options['date']['date_from'],
                                 'to_date': options['date']['date_to'],
                                 'account_code': '321101',
                                 'company_ids': self.env.company.id})
            premium_shares = self.env.cr.dictfetchall()
            premium_shares_credit = premium_shares[0]['credit'] if \
                premium_shares[0]['credit'] else 0
            premium_shares_debit = premium_shares[0]['debit'] if \
                premium_shares[0][
                    'debit'] else 0
            premium_shares_amt = round(
                ((premium_shares_debit - premium_shares_credit) * -1),
                2)
            premium_shares_list.append(premium_shares_amt)

            premium_shares_dict = {
                'id': 'premium_shares',
                'name': 'Share premium on shares issued to acquire subs',
                'level': 2,
                'class': 'cash_flow_line_val_tr',
                'columns': [
                    {
                        'name': premium_shares_list,
                        'class': 'number'}]
            }
            cash_flow_financial_list.append(premium_shares_dict)

            self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                                and journal_item.company_id = %(company_ids)s
                                                                and journal_item.date >= %(from_date)s 
                                                                and journal_item.date <= %(to_date)s
                                                                and {states_args}
                                                                '''.format(
                states_args=states_args),
                                {'from_date': options['date']['date_from'],
                                 'to_date': options['date']['date_to'],
                                 'code_start': '213401', 'code_end': '213499',
                                 'company_ids': self.env.company.id})
            payment_zain = self.env.cr.dictfetchall()
            payment_zain_debit = payment_zain[0]['debit'] if payment_zain[0][
                'debit'] else 0
            payment_zain_amt = round(((payment_zain_debit) * -1), 2)
            payment_zain_list.append(payment_zain_amt)
            payment_zain_dict = {
                'id': 'payment_zain',
                'name': 'Payment of interest on Zain loan',
                'level': 2,
                'class': 'cash_flow_line_val_tr',
                'columns': [
                    {
                        'name': payment_zain_list,
                        'class': 'number'}]
            }
            cash_flow_financial_list.append(payment_zain_dict)

            self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                                and journal_item.company_id = %(company_ids)s
                                                                and journal_item.date >= %(from_date)s 
                                                                and journal_item.date <= %(to_date)s
                                                                and {states_args}
                                                                '''.format(
                states_args=states_args),
                                {'from_date': options['date']['date_from'],
                                 'to_date': options['date']['date_to'],
                                 'code_start': '221101', 'code_end': '223999',
                                 'company_ids': self.env.company.id})
            zain_loan = self.env.cr.dictfetchall()
            zain_loan_credit = zain_loan[0]['credit'] if zain_loan[0][
                'credit'] else 0
            # zain_loan_account_list = self.zain_loan_account(query, states_args,
            #                                            options,number_period)
            # zain_loan_account = zain_loan_account_list[0]
            zain_loan_account_list = self.zain_loan_account(query, states_args,
                                                            options,
                                                            number_period)
            zain_loan_account = zain_loan_account_list[0]
            zain_loan_amt = round(((zain_loan_credit + zain_loan_account) * -1),
                                  2)
            zain_loan_list.append(zain_loan_amt)
            zain_loan_dict = {
                'id': 'zain_loan',
                'name': 'Loan from Zain',
                'level': 2,
                'class': 'cash_flow_line_val_tr',
                'columns': [
                    {
                        'name': zain_loan_list,
                        'class': 'number'}]
            }
            cash_flow_financial_list.append(zain_loan_dict)

            self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                                and journal_item.company_id = %(company_ids)s
                                                                and journal_item.date >= %(from_date)s 
                                                                and journal_item.date <= %(to_date)s
                                                                and {states_args}
                                                                '''.format(
                states_args=states_args),
                                {'from_date': options['date']['date_from'],
                                 'to_date': options['date']['date_to'],
                                 'code_start': '214101', 'code_end': '214999',
                                 'company_ids': self.env.company.id})
            payment_lease = self.env.cr.dictfetchall()
            payment_lease_credit = payment_lease[0]['credit'] if \
                payment_lease[0][
                    'credit'] else 0
            payment_lease_debit = payment_lease[0]['debit'] if payment_lease[0][
                'debit'] else 0
            payment_lease_amt = round(
                ((payment_lease_debit - payment_lease_credit) * -1), 2)
            payment_lease_list.append(payment_lease_amt)
            payment_lease_dict = {
                'id': 'payment_lease',
                'name': 'Payment of lease liability',
                'level': 2,
                'class': 'cash_flow_line_val_tr',
                'columns': [
                    {
                        'name': payment_lease_list,
                        'class': 'number'}]
            }
            cash_flow_financial_list.append(payment_lease_dict)
        return cash_flow_financial_list

    def get_equivalent_cash_account_sum(self, query, options, states_args,
                                        number_period):
        equivalent_cash_account_sum_list = []
        if options['comparison']['comparison_type'] == 'previous_period':
            if options['date_filter'] == 'this_month' or options[
                'date_filter'] == 'last_month':
                for i in range(0, number_period + 1):
                    from_date = datetime.strptime(options['date'][
                                                      'previous_date'],
                                                  "%Y-%m-%d")
                    from_date = from_date - relativedelta(months=i)
                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                                    and journal_item.company_id = %(company_ids)s
                                                                    and journal_item.date <= %(from_date)s 
                                                                    and {states_args}
                                                                    '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'code_start': '111111',
                                         'code_end': '111299',
                                         'company_ids': self.env.company.id})
                    equivalent_cash_account = self.env.cr.dictfetchall()
                    equivalent_cash_account_credit = equivalent_cash_account[0][
                        'credit'] if \
                        equivalent_cash_account[0]['credit'] else 0
                    equivalent_cash_account_debit = equivalent_cash_account[0][
                        'debit'] if \
                        equivalent_cash_account[0]['debit'] else 0
                    equivalent_cash_account_sum = equivalent_cash_account_debit - equivalent_cash_account_credit
                    equivalent_cash_account_sum_list.append(
                        equivalent_cash_account_sum)
            elif options['date_filter'] == 'this_quarter' or options['date_filter'] == 'last_quarter':
                for i in range(0, number_period + 1):
                    from_date = datetime.strptime(options['date']['previous_date'],
                                                  "%Y-%m-%d")
                    from_date = from_date + relativedelta(months=-3 * i)
                    current_quarter = round((from_date.month - 1) / 3 + 1)
                    from_date = datetime(from_date.year,
                                         3 * current_quarter - 2, 1)
                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                                                        and journal_item.company_id = %(company_ids)s
                                                                                        and journal_item.date <= %(from_date)s 
                                                                                        and {states_args}
                                                                                        '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'code_start': '111111',
                                         'code_end': '111299',
                                         'company_ids': self.env.company.id})
                    equivalent_cash_account = self.env.cr.dictfetchall()
                    equivalent_cash_account_credit = equivalent_cash_account[0][
                        'credit'] if \
                        equivalent_cash_account[0]['credit'] else 0
                    equivalent_cash_account_debit = equivalent_cash_account[0][
                        'debit'] if \
                        equivalent_cash_account[0]['debit'] else 0
                    equivalent_cash_account_sum = equivalent_cash_account_debit - equivalent_cash_account_credit
                    equivalent_cash_account_sum_list.append(
                        equivalent_cash_account_sum)
            elif options['date_filter'] == 'this_year' or options['date_filter'] == 'last_year':
                for i in range(0, number_period + 1):
                    from_date = datetime.strptime(options['date']['previous_date'],
                                                  "%Y-%m-%d")
                    from_date = from_date - relativedelta(years=i)
                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                                                        and journal_item.company_id = %(company_ids)s
                                                                                        and journal_item.date <= %(from_date)s 
                                                                                        and {states_args}
                                                                                        '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'code_start': '111111',
                                         'code_end': '111299',
                                         'company_ids': self.env.company.id})
                    equivalent_cash_account = self.env.cr.dictfetchall()
                    equivalent_cash_account_credit = equivalent_cash_account[0][
                        'credit'] if \
                        equivalent_cash_account[0]['credit'] else 0
                    equivalent_cash_account_debit = equivalent_cash_account[0][
                        'debit'] if \
                        equivalent_cash_account[0]['debit'] else 0
                    equivalent_cash_account_sum = equivalent_cash_account_debit - equivalent_cash_account_credit
                    equivalent_cash_account_sum_list.append(
                        equivalent_cash_account_sum)

        elif options['comparison'][
            'comparison_type'] == 'same_period_last_year':
            if options['date_filter'] == 'this_month' or options[
                'date_filter'] == 'last_month':
                for j in range(0, number_period + 1):
                    from_date = datetime.strptime(
                        options['date']['previous_date'],
                        "%Y-%m-%d")
                    from_date = from_date - relativedelta(years=j)

                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                                    and journal_item.company_id = %(company_ids)s
                                                                    and journal_item.date <= %(from_date)s 
                                                                    and {states_args}
                                                                    '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'code_start': '111111',
                                         'code_end': '111299',
                                         'company_ids': self.env.company.id})
                    equivalent_cash_account = self.env.cr.dictfetchall()
                    equivalent_cash_account_credit = equivalent_cash_account[0][
                        'credit'] if \
                        equivalent_cash_account[0]['credit'] else 0
                    equivalent_cash_account_debit = equivalent_cash_account[0][
                        'debit'] if \
                        equivalent_cash_account[0]['debit'] else 0
                    equivalent_cash_account_sum = equivalent_cash_account_debit - equivalent_cash_account_credit
                    equivalent_cash_account_sum_list.append(
                        equivalent_cash_account_sum)
            elif options['date_filter'] == 'this_quarter' or options['date_filter'] == 'last_quarter':
                for i in range(0, number_period + 1):
                    from_date = datetime.strptime(options['date']['previous_date'],
                                                  "%Y-%m-%d")
                    from_date = from_date + relativedelta(years=-i)
                    current_quarter = round((from_date.month - 1) / 3 + 1)
                    from_date = datetime(from_date.year,
                                         3 * current_quarter - 2, 1)
                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                                                        and journal_item.company_id = %(company_ids)s
                                                                                        and journal_item.date <= %(from_date)s 
                                                                                        and {states_args}
                                                                                        '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'code_start': '111111',
                                         'code_end': '111299',
                                         'company_ids': self.env.company.id})
                    equivalent_cash_account = self.env.cr.dictfetchall()
                    equivalent_cash_account_credit = equivalent_cash_account[0][
                        'credit'] if \
                        equivalent_cash_account[0]['credit'] else 0
                    equivalent_cash_account_debit = equivalent_cash_account[0][
                        'debit'] if \
                        equivalent_cash_account[0]['debit'] else 0
                    equivalent_cash_account_sum = equivalent_cash_account_debit - equivalent_cash_account_credit
                    equivalent_cash_account_sum_list.append(
                        equivalent_cash_account_sum)
            elif options['date_filter'] == 'this_year' or options['date_filter'] == 'last_year':
                for i in range(0, number_period + 1):
                    from_date = datetime.strptime(options['date']['previous_date'],
                                                  "%Y-%m-%d")
                    from_date = from_date - relativedelta(years=i)
                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                                                        and journal_item.company_id = %(company_ids)s
                                                                                        and journal_item.date <= %(from_date)s 
                                                                                        and {states_args}
                                                                                        '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'code_start': '111111',
                                         'code_end': '111299',
                                         'company_ids': self.env.company.id})
                    equivalent_cash_account = self.env.cr.dictfetchall()
                    equivalent_cash_account_credit = equivalent_cash_account[0][
                        'credit'] if \
                        equivalent_cash_account[0]['credit'] else 0
                    equivalent_cash_account_debit = equivalent_cash_account[0][
                        'debit'] if \
                        equivalent_cash_account[0]['debit'] else 0
                    equivalent_cash_account_sum = equivalent_cash_account_debit - equivalent_cash_account_credit
                    equivalent_cash_account_sum_list.append(
                        equivalent_cash_account_sum)

        else:

            self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                    and journal_item.company_id = %(company_ids)s
                                                    and journal_item.date <= %(from_date)s 
                                                    and {states_args}
                                                    '''.format(
                states_args=states_args),
                                {'from_date': options['date']['previous_date'],
                                 'code_start': '111111', 'code_end': '111299',
                                 'company_ids': self.env.company.id})
            equivalent_cash_account = self.env.cr.dictfetchall()
            equivalent_cash_account_credit = equivalent_cash_account[0][
                'credit'] if \
                equivalent_cash_account[0]['credit'] else 0
            equivalent_cash_account_debit = equivalent_cash_account[0][
                'debit'] if \
                equivalent_cash_account[0]['debit'] else 0
            equivalent_cash_account_sum = equivalent_cash_account_debit - equivalent_cash_account_credit
            equivalent_cash_account_sum_list.append(equivalent_cash_account_sum)
        return equivalent_cash_account_sum_list

    def get_net_cash_generated_financial(self, options, states_args,
                                         number_period):
        equivalent_cash_amt_list = []
        net_cash_generated_list = []

        if options['comparison']['comparison_type'] == 'previous_period':
            if options['date_filter'] == 'this_month' or options[
                'date_filter'] == 'last_month':
                for i in range(0, number_period + 1):
                    from_date = datetime.strptime(options['date'][
                                                      'previous_date'],
                                                  "%Y-%m-%d")
                    from_date = from_date - relativedelta(months=i)

                    query = '''select sum(journal_item.credit) as credit, sum(journal_item.debit) as debit 
                                            from account_move_line as journal_item
                                            left join account_account as account on journal_item.account_id = account.id
                                            '''

                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                                and journal_item.company_id = %(company_ids)s
                                                                and journal_item.date <= %(from_date)s
                                                                and {states_args}
                                                                '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'code_start': '101001',
                                         'code_end': '111109',
                                         'company_ids': self.env.company.id})
                    equivalent_cash = self.env.cr.dictfetchall()
                    equivalent_cash_credit = equivalent_cash[0]['credit'] if \
                        equivalent_cash[0]['credit'] else 0
                    equivalent_cash_debit = equivalent_cash[0]['debit'] if \
                        equivalent_cash[0]['debit'] else 0
                    equivalent_cash_sum = equivalent_cash_debit - equivalent_cash_credit

                    equivalent_cash_account_sum = self.get_equivalent_cash_account_sum(
                        query, options, states_args, number_period)
                    equivalent_cash_amt = round(
                        (
                                equivalent_cash_sum +
                                equivalent_cash_account_sum[i]),
                        2)
                    equivalent_cash_amt_list.append(equivalent_cash_amt)

                ordinary_shares_dict = {
                    'id': 'equivalent_cash',
                    'name': 'Cash and cash equivalents at the start of the period',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {
                            'name': equivalent_cash_amt_list,
                            'class': 'number'}]
                }
                net_cash_generated_list.append(ordinary_shares_dict)
            elif options['date_filter'] == 'this_quarter' or options['date_filter'] == 'last_quarter':
                for i in range(0, number_period + 1):
                    from_date = datetime.strptime(options['date']['previous_date'],
                                                  "%Y-%m-%d")
                    from_date = from_date + relativedelta(months=-3 * i)
                    current_quarter = round((from_date.month - 1) / 3 + 1)
                    from_date = datetime(from_date.year,
                                         3 * current_quarter - 2, 1)
                    query = '''select sum(journal_item.credit) as credit, sum(journal_item.debit) as debit 
                                                                from account_move_line as journal_item
                                                                left join account_account as account on journal_item.account_id = account.id
                                                                '''

                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                                                    and journal_item.company_id = %(company_ids)s
                                                                                    and journal_item.date <= %(from_date)s
                                                                                    and {states_args}
                                                                                    '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'code_start': '101001',
                                         'code_end': '111109',
                                         'company_ids': self.env.company.id})
                    equivalent_cash = self.env.cr.dictfetchall()
                    equivalent_cash_credit = equivalent_cash[0]['credit'] if \
                        equivalent_cash[0]['credit'] else 0
                    equivalent_cash_debit = equivalent_cash[0]['debit'] if \
                        equivalent_cash[0]['debit'] else 0
                    equivalent_cash_sum = equivalent_cash_debit - equivalent_cash_credit

                    equivalent_cash_account_sum = self.get_equivalent_cash_account_sum(
                        query, options, states_args, number_period)
                    equivalent_cash_amt = round(
                        (
                                equivalent_cash_sum +
                                equivalent_cash_account_sum[i]),
                        2)
                    equivalent_cash_amt_list.append(equivalent_cash_amt)

                ordinary_shares_dict = {
                    'id': 'equivalent_cash',
                    'name': 'Cash and cash equivalents at the start of the period',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {
                            'name': equivalent_cash_amt_list,
                            'class': 'number'}]
                }
                net_cash_generated_list.append(ordinary_shares_dict)
            elif options['date_filter'] == 'this_year' or options['date_filter'] == 'last_year':
                for i in range(0, number_period + 1):
                    from_date = datetime.strptime(options['date']['previous_date'],
                                                  "%Y-%m-%d")
                    from_date = from_date - relativedelta(years=i)
                    to_date = from_date.replace(month=12, day=31)
                    query = '''select sum(journal_item.credit) as credit, sum(journal_item.debit) as debit 
                                                                    from account_move_line as journal_item
                                                                    left join account_account as account on journal_item.account_id = account.id
                                                                    '''

                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                                                        and journal_item.company_id = %(company_ids)s
                                                                                        and journal_item.date <= %(from_date)s
                                                                                        and {states_args}
                                                                                        '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'code_start': '101001',
                                         'code_end': '111109',
                                         'company_ids': self.env.company.id})
                    equivalent_cash = self.env.cr.dictfetchall()
                    equivalent_cash_credit = equivalent_cash[0]['credit'] if \
                        equivalent_cash[0]['credit'] else 0
                    equivalent_cash_debit = equivalent_cash[0]['debit'] if \
                        equivalent_cash[0]['debit'] else 0
                    equivalent_cash_sum = equivalent_cash_debit - equivalent_cash_credit

                    equivalent_cash_account_sum = self.get_equivalent_cash_account_sum(
                        query, options, states_args, number_period)
                    equivalent_cash_amt = round(
                        (
                                equivalent_cash_sum +
                                equivalent_cash_account_sum[i]),
                        2)
                    equivalent_cash_amt_list.append(equivalent_cash_amt)

                ordinary_shares_dict = {
                    'id': 'equivalent_cash',
                    'name': 'Cash and cash equivalents at the start of the period',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {
                            'name': equivalent_cash_amt_list,
                            'class': 'number'}]
                }
                net_cash_generated_list.append(ordinary_shares_dict)

        elif options['comparison'][
            'comparison_type'] == 'same_period_last_year':
            if options['date_filter'] == 'this_month' or options[
                'date_filter'] == 'last_month':
                for j in range(0, number_period + 1):
                    from_date = datetime.strptime(
                        options['date']['previous_date'],
                        "%Y-%m-%d")
                    from_date = from_date - relativedelta(years=j)
                    query = '''select sum(journal_item.credit) as credit, sum(journal_item.debit) as debit 
                                                from account_move_line as journal_item
                                                left join account_account as account on journal_item.account_id = account.id
                                                '''

                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                                    and journal_item.company_id = %(company_ids)s
                                                                    and journal_item.date <= %(from_date)s
                                                                    and {states_args}
                                                                    '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'code_start': '101001',
                                         'code_end': '111109',
                                         'company_ids': self.env.company.id})
                    equivalent_cash = self.env.cr.dictfetchall()
                    equivalent_cash_credit = equivalent_cash[0]['credit'] if \
                        equivalent_cash[0]['credit'] else 0
                    equivalent_cash_debit = equivalent_cash[0]['debit'] if \
                        equivalent_cash[0]['debit'] else 0
                    equivalent_cash_sum = equivalent_cash_debit - equivalent_cash_credit

                    equivalent_cash_account_sum = self.get_equivalent_cash_account_sum(
                        query, options, states_args, number_period)
                    equivalent_cash_amt = round(
                        (
                                equivalent_cash_sum +
                                equivalent_cash_account_sum[j]),
                        2)
                    equivalent_cash_amt_list.append(equivalent_cash_amt)

                ordinary_shares_dict = {
                    'id': 'equivalent_cash',
                    'name': 'Cash and cash equivalents at the start of the period',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {
                            'name': equivalent_cash_amt_list,
                            'class': 'number'}]
                }
                net_cash_generated_list.append(ordinary_shares_dict)
            elif options['date_filter'] == 'this_quarter' or options['date_filter'] == 'last_quarter':
                for i in range(0, number_period + 1):
                    from_date = datetime.strptime(options['date']['previous_date'],
                                                  "%Y-%m-%d")
                    from_date = from_date + relativedelta(years=-i)
                    current_quarter = round((from_date.month - 1) / 3 + 1)
                    from_date = datetime(from_date.year,
                                         3 * current_quarter - 2, 1)
                    query = '''select sum(journal_item.credit) as credit, sum(journal_item.debit) as debit 
                                                                    from account_move_line as journal_item
                                                                    left join account_account as account on journal_item.account_id = account.id
                                                                    '''

                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                                                        and journal_item.company_id = %(company_ids)s
                                                                                        and journal_item.date <= %(from_date)s
                                                                                        and {states_args}
                                                                                        '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'code_start': '101001',
                                         'code_end': '111109',
                                         'company_ids': self.env.company.id})
                    equivalent_cash = self.env.cr.dictfetchall()
                    equivalent_cash_credit = equivalent_cash[0]['credit'] if \
                        equivalent_cash[0]['credit'] else 0
                    equivalent_cash_debit = equivalent_cash[0]['debit'] if \
                        equivalent_cash[0]['debit'] else 0
                    equivalent_cash_sum = equivalent_cash_debit - equivalent_cash_credit

                    equivalent_cash_account_sum = self.get_equivalent_cash_account_sum(
                        query, options, states_args, number_period)
                    equivalent_cash_amt = round(
                        (
                                equivalent_cash_sum +
                                equivalent_cash_account_sum[i]),
                        2)
                    equivalent_cash_amt_list.append(equivalent_cash_amt)

                ordinary_shares_dict = {
                    'id': 'equivalent_cash',
                    'name': 'Cash and cash equivalents at the start of the period',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {
                            'name': equivalent_cash_amt_list,
                            'class': 'number'}]
                }
                net_cash_generated_list.append(ordinary_shares_dict)
            elif options['date_filter'] == 'this_year' or options['date_filter'] == 'last_year':
                for i in range(0, number_period + 1):
                    from_date = datetime.strptime(options['date']['previous_date'],
                                                  "%Y-%m-%d")
                    from_date = from_date - relativedelta(years=i)
                    to_date = from_date.replace(month=12, day=31)
                    query = '''select sum(journal_item.credit) as credit, sum(journal_item.debit) as debit 
                                                                    from account_move_line as journal_item
                                                                    left join account_account as account on journal_item.account_id = account.id
                                                                    '''

                    self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                                                        and journal_item.company_id = %(company_ids)s
                                                                                        and journal_item.date <= %(from_date)s
                                                                                        and {states_args}
                                                                                        '''.format(
                        states_args=states_args),
                                        {'from_date': from_date,
                                         'code_start': '101001',
                                         'code_end': '111109',
                                         'company_ids': self.env.company.id})
                    equivalent_cash = self.env.cr.dictfetchall()
                    equivalent_cash_credit = equivalent_cash[0]['credit'] if \
                        equivalent_cash[0]['credit'] else 0
                    equivalent_cash_debit = equivalent_cash[0]['debit'] if \
                        equivalent_cash[0]['debit'] else 0
                    equivalent_cash_sum = equivalent_cash_debit - equivalent_cash_credit

                    equivalent_cash_account_sum = self.get_equivalent_cash_account_sum(
                        query, options, states_args, number_period)
                    equivalent_cash_amt = round(
                        (
                                equivalent_cash_sum +
                                equivalent_cash_account_sum[i]),
                        2)
                    equivalent_cash_amt_list.append(equivalent_cash_amt)

                ordinary_shares_dict = {
                    'id': 'equivalent_cash',
                    'name': 'Cash and cash equivalents at the start of the period',
                    'level': 2,
                    'class': 'cash_flow_line_val_tr',
                    'columns': [
                        {
                            'name': equivalent_cash_amt_list,
                            'class': 'number'}]
                }
                net_cash_generated_list.append(ordinary_shares_dict)

        else:

            query = '''select sum(journal_item.credit) as credit, sum(journal_item.debit) as debit 
                        from account_move_line as journal_item
                        left join account_account as account on journal_item.account_id = account.id
                        '''

            self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                            and journal_item.company_id = %(company_ids)s
                                            and journal_item.date <= %(from_date)s
                                            and {states_args}
                                            '''.format(states_args=states_args),
                                {'from_date': options['date']['previous_date'],
                                 'code_start': '101001', 'code_end': '111109',
                                 'company_ids': self.env.company.id})
            equivalent_cash = self.env.cr.dictfetchall()
            equivalent_cash_credit = equivalent_cash[0]['credit'] if \
                equivalent_cash[0]['credit'] else 0
            equivalent_cash_debit = equivalent_cash[0]['debit'] if \
                equivalent_cash[0]['debit'] else 0
            equivalent_cash_sum = equivalent_cash_debit - equivalent_cash_credit

            equivalent_cash_account_sum = self.get_equivalent_cash_account_sum(
                query, options, states_args, number_period)
            equivalent_cash_amt = round(
                (
                        equivalent_cash_sum + equivalent_cash_account_sum[0]),
                2)
            equivalent_cash_amt_list.append(equivalent_cash_amt)

            ordinary_shares_dict = {
                'id': 'equivalent_cash',
                'name': 'Cash and cash equivalents at the start of the period',
                'level': 2,
                'class': 'cash_flow_line_val_tr',
                'columns': [
                    {
                        'name': equivalent_cash_amt_list,
                        'class': 'number'}]
            }
            net_cash_generated_list.append(ordinary_shares_dict)
        return net_cash_generated_list

    def get_cash_flow_lines(self, options):
        number_period = options['comparison']['number_period']
        number_period = int(number_period)
        states_args = """ parent_state = 'posted'"""
        if options['entry'] != 'posted':
            states_args = """ parent_state in ('to_approve','posted', 'draft')"""
        cash_flow_lines = [
            {
                'id': 'Cash flows from operating activities',
                'name': 'Cash flows from operating activities',
                'level': 1,
                'class': 'cash_flow_line_main_head',
                'columns': [{'name': '', 'class': 'number'}]
            },
            {
                'id': 'loss_for_the_period_1',
                'name': 'Loss for the period',
                'level': 2,
                'class': 'cash_flow_line_val_tr',
                'columns': [
                    {'name': self.get_loss_for_period(options, states_args,
                                                      number_period),
                     'class': 'number'}]
            },
            {
                'id': 'adjustment_1',
                'name': 'Adjustments for :',
                'level': 3,
                'class': 'cash_flow_line_sub_head',
                'columns': [
                    {'name': '', 'class': 'number'}]
            },
            {
                'id': 'movement_1',
                'name': 'Movement in working capital',
                'level': 3,
                'class': 'cash_flow_line_sub_head',
                'columns': [
                    {'name': '', 'class': 'number'}]
            },
            {
                'id': 'activities',
                'name': 'Net cash used in operating activities',
                'level': 0,
                'class': 'cash_flow_line_sub_head',
                'columns': [
                    {'name': '', 'class': 'number'}]
            },
            {
                'id': 'investing_activities',
                'name': 'Cash flows from investing activities',
                'level': 0,
                'class': 'cash_flow_line_sub_head',
                'columns': [
                    {'name': '', 'class': 'number'}]
            },
            {
                'id': 'net_investing_activities',
                'name': 'Net cash used in investing activities',
                'level': 0,
                'class': 'cash_flow_line_sub_head',
                'columns': [
                    {'name': '', 'class': 'number'}]
            },
            {
                'id': 'cash_flow_financial',
                'name': 'Cash flows from financing activities',
                'level': 0,
                'class': 'cash_flow_line_sub_head',
                'columns': [
                    {'name': '', 'class': 'number'}]
            },

            {
                'id': 'net_cash_generated_financial',
                'name': 'Net cash generated from financing activities',
                'level': 0,
                'class': 'cash_flow_line_sub_head',
                'columns': [
                    {'name': '', 'class': 'number'}]
            },
            {
                'id': 'net_increase',
                'name': 'Net increase / (decrease) in cash and cash equivalents',
                'level': 0,
                'class': 'cash_flow_line_sub_head',
                'columns': [
                    {'name': '', 'class': 'number'}]
            },

            {
                'id': 'cash_equivalent_end',
                'name': 'Cash and cash equivalents at the end of the period',
                'level': 0,
                'class': 'cash_flow_line_sub_head',
                'columns': [
                    {'name': '', 'class': 'number'}]
            },
        ]
        adjustment = self.adjustment_1(options, states_args, number_period)
        adjustment_index = 3
        net_cash_operating_activities_sum = self.get_loss_for_period(options,
                                                                     states_args,
                                                                     number_period)


        for rec in adjustment:
            if len(rec['columns'][0]['name']) == 1:
                net_cash_operating_activities_sum[0] += \
                    rec['columns'][0]['name'][0]
            else:
                for k in range(0, number_period + 1):
                    net_cash_operating_activities_sum[k] += \
                        rec['columns'][0]['name'][k]
            cash_flow_lines.insert(adjustment_index, rec)
            adjustment_index += 1

        movement = self.movement_capital(options, states_args, number_period)
        net_cash_operating_activities_sum = [0] * len(
            movement[0]['columns'][0]['name'])
        # movement =
        movement_index = 9
        for rec in movement:
            if len(rec['columns'][0]['name']) == 1:
                net_cash_operating_activities_sum[0] += \
                    rec['columns'][0]['name'][0]
            else:
                for m in range(0, number_period + 1):
                    net_cash_operating_activities_sum[m] += \
                        rec['columns'][0]['name'][m]
            cash_flow_lines.insert(movement_index, rec)
            movement_index += 1
        cash_flow_lines[13]['columns'][0]['name'] = list()
        for i in range(0, len(net_cash_operating_activities_sum)):
            cash_flow_lines[13]['columns'][0]['name'].append(0)

        if len(cash_flow_lines[13]['columns'][0]['name']) == 1:
            cash_flow_lines[13]['columns'][0]['name'][0] = \
            net_cash_operating_activities_sum[0]
        else:
            cash_flow_lines[13]['columns'][0][
                'name'] = net_cash_operating_activities_sum

        investing_activities = self.investing_activities(options, states_args,
                                                         number_period)
        net_cash_investing_activities_sum = [0] * len(
            investing_activities[0]['columns'][0]['name'])
        investing_activities_index = 15
        for rec in investing_activities:
            if len(rec['columns'][0]['name']) == 1:
                net_cash_investing_activities_sum[0] += \
                    rec['columns'][0]['name'][0]
            else:
                for n in range(0, number_period + 1):
                    net_cash_investing_activities_sum[n] += \
                        rec['columns'][0]['name'][n]
            cash_flow_lines.insert(investing_activities_index, rec)
            investing_activities_index += 1
            cash_flow_lines[17]['columns'][0]['name'] = list()
            for i in range(0, len(net_cash_investing_activities_sum)):
                cash_flow_lines[17]['columns'][0]['name'].append(0)

            if len(cash_flow_lines[17]['columns'][0]['name']) == 1:
                cash_flow_lines[17]['columns'][0]['name'][0] = \
                    net_cash_investing_activities_sum[0]
            else:
                cash_flow_lines[17]['columns'][0][
                    'name'] = net_cash_investing_activities_sum

        cash_flow_financial = self.get_cash_flow_financial(options, states_args,
                                                           number_period)
        cash_flow_financial_index = 19
        net_cash_financial_activities_sum = [0] * len(
            cash_flow_financial[0]['columns'][0]['name'])

        for rec in cash_flow_financial:
            if len(rec['columns'][0]['name']) == 1:
                net_cash_financial_activities_sum[0] += \
                    rec['columns'][0]['name'][0]
            else:
                for r in range(0, number_period + 1):
                    net_cash_financial_activities_sum[r] += \
                        rec['columns'][0]['name'][r]
            cash_flow_lines.insert(cash_flow_financial_index, rec)
            cash_flow_financial_index += 1

        cash_flow_lines[24]['columns'][0]['name'] = list()
        for i in range(0, len(net_cash_financial_activities_sum)):
            cash_flow_lines[24]['columns'][0]['name'].append(0)

        if len(cash_flow_lines[24]['columns'][0]['name']) == 1:
            cash_flow_lines[24]['columns'][0]['name'][0] = \
                net_cash_financial_activities_sum[0]
        else:
            cash_flow_lines[24]['columns'][0][
                'name'] = net_cash_financial_activities_sum

        net_cash_generated_financial = self.get_net_cash_generated_financial(
            options, states_args, number_period)
        cash_flow_financial_index = 26
        for rec in net_cash_generated_financial:
            cash_flow_lines.insert(cash_flow_financial_index, rec)

        net_increase_decrease_list = []
        cash_equivalent_end_sum_list = []

        net_increase_decrease = [0] * len(
            net_cash_generated_financial[0]['columns'][0]['name'])
        cash_equivalent_end_sum = [0] * len(
            net_cash_generated_financial[0]['columns'][0]['name'])
        for x in range(0, len(net_increase_decrease)):
            net_increase_decrease[x] = net_cash_operating_activities_sum[x] + \
                                       net_cash_investing_activities_sum[x] + \
                                       net_cash_financial_activities_sum[x]
            net_increase_decrease_amt = round(net_increase_decrease[x], 2)
            net_increase_decrease_list.append(net_increase_decrease_amt)
            cash_equivalent_end_sum[x] = net_increase_decrease[x] + \
                                         cash_flow_lines[26]['columns'][0][
                                             'name'][x]
            cash_equivalent_end_sum_amt = round(cash_equivalent_end_sum[x], 2)
            cash_equivalent_end_sum_list.append(cash_equivalent_end_sum_amt)

        # net_increase_decrease = net_cash_operating_activities_sum + net_cash_investing_activities_sum + net_cash_financial_activities_sum
        cash_flow_lines[25]['columns'][0]['name'] = net_increase_decrease_list
        # cash_equivalent_end_sum = net_increase_decrease + \
        #                           cash_flow_lines[26]['columns'][0]['name']
        cash_flow_lines[27]['columns'][0]['name'] = cash_equivalent_end_sum_list

        return cash_flow_lines

    def get_cash_flow_header(self, options):
        filter_months = ['month', 'Last month']
        filter_years = ['This financial year', 'Last financial year']
        column_list = []
        if options['date']['period_type'] in filter_months and \
                options['comparison']['comparison_type'] == 'previous_period':
            month = datetime.strptime(options['date']['date_from'],
                                      "%Y-%m-%d")
            for i in range(0, int(options['comparison']['number_period']) + 1):
                column_list.append(
                    month.strftime("%B")
                )
                month = month - relativedelta(months=1)

            return column_list
        elif options['date']['period_type'] in filter_months and \
                options['comparison'][
                    'comparison_type'] == 'same_period_last_year':
            month = datetime.strptime(options['date']['date_from'],
                                      "%Y-%m-%d")
            for i in range(0,
                           int(options['comparison']['number_period']) + 1):
                column_list.append(
                    month.strftime("%B") + "-" + month.strftime("%Y")
                )
                month = month - relativedelta(years=1)
            return column_list
        elif options['date']['period_type'] in filter_months:
            month = datetime.strptime(options['date']['date_from'],
                                      "%Y-%m-%d")
            column_list.append(month.strftime("%B"))
            return column_list
        elif options['date']['period_type'] in filter_years and \
                options['comparison']['comparison_type'] == 'previous_period':
            year = datetime.strptime(options['date']['date_from'],
                                     "%Y-%m-%d").year
            for i in range(0, int(options['comparison']['number_period']) + 1):
                column_list.append(
                    year
                )
                year = year - 1
            return column_list
        elif options['date']['period_type'] in filter_years and options['comparison']['comparison_type'] == 'same_period_last_year':
            year = datetime.strptime(options['date']['date_from'],
                                     "%Y-%m-%d").year
            for i in range(0, int(options['comparison']['number_period']) + 1):
                year = year - i
                column_list.append(
                    year
                )
            return column_list

        elif options['date']['period_type'] in filter_years:
            year = datetime.strptime(options['date']['date_from'],
                                     "%Y-%m-%d").year
            column_list.append(year)
            # return {
            #     'name': year
            # }
            return column_list
        elif options['date']['period_type'] == 'custom' or 'custom' in list(
                options['date'].keys()):
            options['date']['period_type'] = options['date'][
                                                 'date_from'] + ' to ' + \
                                             options['date'][
                                                 'date_to']
            options['date']['custom'] = True
            column_list.append(
                options['date']['date_from'] + ' to ' + options['date'][
                    'date_to'])
            return column_list
        else:
            month = datetime.strptime(options['date']['date_from'],
                                      "%Y-%m-%d")
            if options['comparison']['comparison_type'] == 'previous_period':
                for i in range(0,
                               int(options['comparison']['number_period']) + 1):
                    q = math.ceil(month.month / 3)
                    quarter_name = 'Quarter' + str(q) + "-" + str(month.year)
                    column_list.append(
                        quarter_name
                    )
                    month = month - relativedelta(months=3)
            elif options['comparison']['comparison_type'] == 'same_period_last_year':
                for i in range(0,
                               int(options['comparison']['number_period']) + 1):
                    month = month + relativedelta(years=-i)
                    current_quarter = round((month.month - 1) / 3 + 1)
                    quarter_name = 'Quarter' + str(current_quarter) + "-" + str(month.year)
                    column_list.append(
                        quarter_name
                    )
            return column_list

    def get_button_cashflow(self):
        return [
            {'name': _('Export (XLSX)'), 'sequence': 2,
             'action': 'print_xlsx_cash',
             'file_export_type': _('XLSX')},
        ]

    def get_html_content(self, options):
        templates = self._get_templates()
        template = templates['main_template']
        values = {'model': self}
        header = self.get_cash_flow_header(options)
        lines = self.get_cash_flow_lines(options)
        values['lines'] = {'lines': lines, 'header': header,
                           'currency_symbol': self.env.company.currency_id.symbol}

        html = self.env.ref(template)._render(values)
        return html

    def print_xlsx_cash(self, options, params):
        return {
            'type': 'ir.actions.report',
            'data': {'model': self.env.context.get('model'),
                     'options': json.dumps(options,
                                           default=date_utils.json_default),
                     'output_format': 'xlsx',
                     'financial_id': self.env.context.get('id'),
                     'allowed_company_ids': self.env.context.get(
                         'allowed_company_ids'),
                     'report_name': 'Tasc Cash Flow Report',
                     },
            'report_type': 'xlsx'
        }

    def get_xlsx(self, options, response=None):
        lines = self.get_cash_flow_lines(options)
        header = self.get_cash_flow_header(options)
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})

        sheet = workbook.add_worksheet()
        sheet.set_column(0, 0, 50)
        main_head = workbook.add_format(
            {'font_size': 13, 'align': 'center', 'border': 2})

        level_0_style = workbook.add_format(
            {'font_name': 'Arial', 'bold': True, 'font_size': 13, 'bottom': 6,
             'font_color': '#120e0d'})
        head1 = workbook.add_format(
            {'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666',
             'indent': 2})

        head_col = workbook.add_format(
            {'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666'})

        sheet.write(0, 1, header['name'], main_head)
        level_1_style = workbook.add_format(
            {'font_name': 'Arial', 'bold': True, 'font_size': 13, 'bottom': 1,
             'font_color': '#666666', 'indent': 1})

        level_1_style_col = workbook.add_format(
            {'font_name': 'Arial', 'bold': True, 'font_size': 13, 'bottom': 1,
             'font_color': '#666666'})

        row_num = 1
        col_num = 0
        for line in lines:
            head = head1
            head_col1 = head_col
            if line['level'] == 1:
                head = level_0_style
                head_col1 = level_0_style
            elif line['level'] == 3 or line['level'] == 0:
                head = level_1_style
                head_col1 = level_1_style_col
            abc = col_num
            sheet.write(row_num, abc, line['name'], head)
            if line['columns']:
                sheet.write(row_num, abc + 1, line['columns'][0]['name'],
                            head_col1)
            row_num += 1

        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()
