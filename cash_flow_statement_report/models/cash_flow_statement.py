import json
import io

import xlsxwriter

from odoo import models, fields, _
from odoo.tools import date_utils, datetime


class CashFlowStatement(models.Model):
    _name = 'cash.flow.statement'

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
        if options:
            if options['date_filter'] == 'this_month':
                date_from, date_to = date_utils.get_month(
                    fields.Date.context_today(self))
                period_type = 'month'
            elif options['date_filter'] == 'this_quarter':
                date_from, date_to = date_utils.get_quarter(
                    fields.Date.context_today(self))
                period_type = 'quarter'
            elif options['date_filter'] == 'this_year':
                company_fiscalyear_dates = self.env.company.compute_fiscalyear_dates(
                    fields.Date.context_today(self))
                date_from = company_fiscalyear_dates['date_from']
                date_to = company_fiscalyear_dates['date_to']
                period_type = 'year'
        else:
            date_from, date_to = date_utils.get_month(
                fields.Date.context_today(self))
            period_type = 'month'
            options['entry'] = ''
            options['date_filter'] = 'this_month'
        options['date'] = {
            'date_from': fields.Date.to_string(date_from),
            'date_to': fields.Date.to_string(date_to),
            'period_type': period_type
        }

    def get_posted_filter(self, options):
        if not options['entry']:
            options['entry'] = 'posted'

    def _get_cashflow_options(self, options):
        if not options:
            options = {}
        self._get_date_filter(options)
        self.get_posted_filter(options)
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

    def get_loss_for_period(self, options, states_args):
        query = '''select sum(journal_item.credit) as credit, sum(journal_item.debit) as debit 
                    from account_move_line as journal_item
                    left join account_account as account on journal_item.account_id = account.id
                    '''
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
        return round(((loss_for_period_debit - loss_for_period_credit) * -1), 2)

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
        self.env.cr.execute(query + '''where account.code = %(account_code)s
                                                    and journal_item.company_id = %(company_ids)s
                                                    and journal_item.date >= %(from_date)s 
                                                    and journal_item.date <= %(to_date)s
                                                    and {states_args}
                                                    '''.format(
            states_args=states_args),
                            {'from_date': options['date']['date_from'],
                             'to_date': options['date']['date_to'],
                             'account_code': '111110',
                             'company_ids': self.env.company.id})
        movement_trade_account = self.env.cr.dictfetchall()
        movement_trade_account_credit = movement_trade_account[0]['credit'] if \
            movement_trade_account[0]['credit'] else 0
        movement_trade_account_debit = movement_trade_account[0]['debit'] if \
            movement_trade_account[0]['debit'] else 0
        return movement_trade_account_debit - movement_trade_account_credit

    def get_movement_trade_dict(self, query, options, states_args):
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
        movement_trade_debit = movement_trade[0]['debit'] if movement_trade[0][
            'debit'] else 0
        movement_trade_sum = movement_trade_debit - movement_trade_credit

        movement_trade_account_sum = self.get_movement_trade_account_sum(query,
                                                                         options,
                                                                         states_args)

        movement_trade_dict = {
            'id': 'movement_trade',
            'name': 'Movement in trade and other receivables',
            'level': 2,
            'class': 'cash_flow_line_val_tr',
            'columns': [
                {
                    'name': round(((
                                           movement_trade_sum + movement_trade_account_sum) * -1),
                                  2),
                    'class': 'number'}]
        }
        return movement_trade_dict

    def get_movement_related_dict(self, query, options, states_args):
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
        movement_related_dict = {
            'id': 'movement_related',
            'name': 'Movement in due from related parties',
            'level': 2,
            'class': 'cash_flow_line_val_tr',
            'columns': [
                {
                    'name': round(((
                                           movement_related_debit - movement_related_credit) * -1),
                                  2),
                    'class': 'number'}]
        }
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
                             'code_start': '213501', 'code_end': '213999',
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

    def get_movement_trade_payable_dict(self, query, options, states_args):
        self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                            and journal_item.company_id = %(company_ids)s
                                            and journal_item.date >= %(from_date)s 
                                            and journal_item.date <= %(to_date)s
                                            and {states_args}
                                            '''.format(states_args=states_args),
                            {'from_date': options['date']['date_from'],
                             'to_date': options['date']['date_to'],
                             'code_start': '211101', 'code_end': '211999',
                             'company_ids': self.env.company.id})
        movement_trade_payable = self.env.cr.dictfetchall()
        movement_trade_payable_credit = movement_trade_payable[0]['credit'] if \
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

        movement_trade_payable_dict = {
            'id': 'movement_trade_payable',
            'name': 'Movement trade and other payables',
            'level': 2,
            'class': 'cash_flow_line_val_tr',
            'columns': [
                {
                    'name': round(((
                                           movement_trade_payable_account_sum + movement_trade_payable_sum + movement_trade_payable_account1_sum + movement_trade_payable_account2_sum) * -1),
                                  2),
                    'class': 'number'}]
        }
        return movement_trade_payable_dict

    def adjustment_1(self, options, states_args):
        adjustment_list = []
        query = '''select sum(journal_item.credit) as credit, sum(journal_item.debit) as debit 
                    from account_move_line as journal_item
                    left join account_account as account on journal_item.account_id = account.id
                    '''
        self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                    and journal_item.company_id = %(company_ids)s
                    and journal_item.date >= %(from_date)s 
                    and journal_item.date <= %(to_date)s
                    and {states_args}
                    '''.format(states_args=states_args),
                            {'from_date': options['date']['date_from'],
                             'to_date': options['date']['date_to'],
                             'code_start': '553101', 'code_end': '553299',
                             'company_ids': self.env.company.id})
        depreciation = self.env.cr.dictfetchall()
        depreciation_credit = depreciation[0]['credit'] if depreciation[0][
            'credit'] else 0
        depreciation_debit = depreciation[0]['debit'] if depreciation[0][
            'debit'] else 0
        depreciation_of_ppe_dict = {
            'id': 'depreciation_of_ppe',
            'name': 'Depreciation of PPE',
            'level': 2,
            'class': 'cash_flow_line_val_tr',
            'columns': [
                {'name': round((depreciation_debit - depreciation_credit), 2),
                 'class': 'number'}]
        }
        adjustment_list.append(depreciation_of_ppe_dict)
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
        amortisation_dict = {
            'id': 'amortisation_id',
            'name': 'Amortisation of intangible assets',
            'level': 2,
            'class': 'cash_flow_line_val_tr',
            'columns': [
                {'name': round((amortisation_debit - amortisation_credit), 2),
                 'class': 'number'}]
        }
        adjustment_list.append(amortisation_dict)

        amortisation_right_dict = self.get_amortisation_right_dict(query,
                                                                   options,
                                                                   states_args)
        adjustment_list.append(amortisation_right_dict)

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
        interest_lease_liability_debit = interest_lease_liability[0]['debit'] if \
            interest_lease_liability[0]['debit'] else 0
        interest_lease_liability_dict = {
            'id': 'interest_lease_liability',
            'name': 'Interest on lease liability',
            'level': 2,
            'class': 'cash_flow_line_val_tr',
            'columns': [
                {
                    'name': round(((
                                           interest_lease_liability_debit - interest_lease_liability_credit) * -1),
                                  2),
                    'class': 'number'}]
        }
        adjustment_list.append(interest_lease_liability_dict)

        self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                            and journal_item.company_id = %(company_ids)s
                                            and journal_item.date >= %(from_date)s 
                                            and journal_item.date <= %(to_date)s
                                            and {states_args}
                                            '''.format(states_args=states_args),
                            {'from_date': options['date']['date_from'],
                             'to_date': options['date']['date_to'],
                             'code_start': '213401', 'code_end': '213499',
                             'company_ids': self.env.company.id})
        finance_zain = self.env.cr.dictfetchall()
        finance_zain_credit = finance_zain[0]['credit'] if finance_zain[0][
            'credit'] else 0
        finance_zain_debit = finance_zain[0]['debit'] if finance_zain[0][
            'debit'] else 0
        finance_zain_dict = {
            'id': 'finance_zain_id',
            'name': 'Finance costs on Zain`s loan',
            'level': 2,
            'class': 'cash_flow_line_val_tr',
            'columns': [
                {
                    'name': round(
                        ((finance_zain_credit) * -1), 2),
                    'class': 'number'}]
        }
        adjustment_list.append(finance_zain_dict)
        return adjustment_list

    def get_movement_related_parties_dict(self, query, options, states_args):
        self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                        and journal_item.company_id = %(company_ids)s
                                                        and journal_item.date >= %(from_date)s 
                                                        and journal_item.date <= %(to_date)s
                                                        and {states_args}
                                                        '''.format(
            states_args=states_args),
                            {'from_date': options['date']['date_from'],
                             'to_date': options['date']['date_to'],
                             'code_start': '212101', 'code_end': '212999',
                             'company_ids': self.env.company.id})
        movement_related_parties = self.env.cr.dictfetchall()
        movement_related_parties_credit = movement_related_parties[0][
            'credit'] if movement_related_parties[0]['credit'] else 0
        movement_related_parties_debit = movement_related_parties[0]['debit'] if \
            movement_related_parties[0]['debit'] else 0
        movement_related_parties_dict = {
            'id': 'movement_related_parties',
            'name': 'Movement in due to related parties',
            'level': 2,
            'class': 'cash_flow_line_val_tr',
            'columns': [
                {
                    'name': round(((
                                           movement_related_parties_debit - movement_related_parties_credit) * -1),
                                  2),
                    'class': 'number'}]
        }
        return movement_related_parties_dict

    def movement_capital(self, options, states_args):
        movement_list = []
        query = '''select sum(journal_item.credit) as credit, sum(journal_item.debit) as debit 
                            from account_move_line as journal_item
                            left join account_account as account on journal_item.account_id = account.id
                            '''
        movement_trade_dict = self.get_movement_trade_dict(query, options,
                                                           states_args)

        movement_list.append(movement_trade_dict)

        movement_related_dict = self.get_movement_related_dict(query, options,
                                                               states_args)

        movement_list.append(movement_related_dict)

        movement_trade_payable_dict = self.get_movement_trade_payable_dict(
            query, options, states_args)
        movement_list.append(movement_trade_payable_dict)

        movement_related_parties_dict = self.get_movement_related_parties_dict(
            query, options, states_args)
        movement_list.append(movement_related_parties_dict)

        return movement_list

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

    def get_purchase_asset_dict(self, query, options, states_args):
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
        purchase_asset_debit = purchase_asset[0]['debit'] if purchase_asset[0][
            'debit'] else 0
        purchase_asset_sum = purchase_asset_debit - purchase_asset_credit
        purchase_asset_account_sum = self.get_purchase_asset_account_sum(query,
                                                                         options,
                                                                         states_args)
        purchase_asset_dict = {
            'id': 'purchase_asset',
            'name': 'Purchase of fixed assets',
            'level': 2,
            'class': 'cash_flow_line_val_tr',
            'columns': [
                {
                    'name': round(((
                                           purchase_asset_sum + purchase_asset_account_sum) * -1),
                                  2),
                    'class': 'number'}]
        }
        return purchase_asset_dict

    def investing_activities(self, options, states_args):
        investing_activities_list = []
        query = '''select sum(journal_item.credit) as credit, sum(journal_item.debit) as debit 
                                    from account_move_line as journal_item
                                    left join account_account as account on journal_item.account_id = account.id
                                    '''

        purchase_asset_dict = self.get_purchase_asset_dict(query, options,
                                                           states_args)

        investing_activities_list.append(purchase_asset_dict)

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
        subsidiaries_dict = {
            'id': 'subsidiaries',
            'name': 'Investment in subsidiaries',
            'level': 2,
            'class': 'cash_flow_line_val_tr',
            'columns': [
                {
                    'name': round(
                        ((subsidiaries_debit - subsidiaries_credit) * -1), 2),
                    'class': 'number'}]
        }
        investing_activities_list.append(subsidiaries_dict)

        return investing_activities_list

    def get_cash_flow_financial(self, options, states_args):
        cash_flow_financial_list = []

        query = '''select sum(journal_item.credit) as credit, sum(journal_item.debit) as debit 
                                    from account_move_line as journal_item
                                    left join account_account as account on journal_item.account_id = account.id
                                    '''

        self.env.cr.execute(query + '''where account.code = %(account_code)s
                                        and journal_item.company_id = %(company_ids)s
                                        and journal_item.date >= %(from_date)s 
                                        and journal_item.date <= %(to_date)s
                                        and {states_args}
                                        '''.format(states_args=states_args),
                            {'from_date': options['date']['date_from'],
                             'to_date': options['date']['date_to'],
                             'account_code': '311101',
                             'company_ids': self.env.company.id})
        ordinary_shares = self.env.cr.dictfetchall()
        ordinary_shares_credit = ordinary_shares[0]['credit'] if \
            ordinary_shares[0]['credit'] else 0
        ordinary_shares_debit = ordinary_shares[0]['debit'] if \
            ordinary_shares[0]['debit'] else 0

        ordinary_shares_dict = {
            'id': 'ordinary_shares',
            'name': 'Ordinary shares issued @ par value $ 0.01',
            'level': 2,
            'class': 'cash_flow_line_val_tr',
            'columns': [
                {
                    'name': round(
                        ((ordinary_shares_debit - ordinary_shares_credit) * -1),
                        2),
                    'class': 'number'}]
        }
        cash_flow_financial_list.append(ordinary_shares_dict)

        self.env.cr.execute(query + '''where account.code = %(account_code)s
                                        and journal_item.company_id = %(company_ids)s
                                        and journal_item.date >= %(from_date)s 
                                        and journal_item.date <= %(to_date)s
                                        and {states_args}
                                        '''.format(states_args=states_args),
                            {'from_date': options['date']['date_from'],
                             'to_date': options['date']['date_to'],
                             'account_code': '321101',
                             'company_ids': self.env.company.id})
        premium_shares = self.env.cr.dictfetchall()
        premium_shares_credit = premium_shares[0]['credit'] if \
            premium_shares[0]['credit'] else 0
        premium_shares_debit = premium_shares[0]['debit'] if premium_shares[0][
            'debit'] else 0

        premium_shares_dict = {
            'id': 'premium_shares',
            'name': 'Share premium on shares issued to acquire subs',
            'level': 2,
            'class': 'cash_flow_line_val_tr',
            'columns': [
                {
                    'name': round(
                        ((premium_shares_debit - premium_shares_credit) * -1),
                        2),
                    'class': 'number'}]
        }
        cash_flow_financial_list.append(premium_shares_dict)

        self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                        and journal_item.company_id = %(company_ids)s
                                        and journal_item.date >= %(from_date)s 
                                        and journal_item.date <= %(to_date)s
                                        and {states_args}
                                        '''.format(states_args=states_args),
                            {'from_date': options['date']['date_from'],
                             'to_date': options['date']['date_to'],
                             'code_start': '213401', 'code_end': '213499',
                             'company_ids': self.env.company.id})
        payment_zain = self.env.cr.dictfetchall()
        payment_zain_debit = payment_zain[0]['debit'] if payment_zain[0][
            'debit'] else 0
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
        cash_flow_financial_list.append(payment_zain_dict)

        self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                        and journal_item.company_id = %(company_ids)s
                                        and journal_item.date >= %(from_date)s 
                                        and journal_item.date <= %(to_date)s
                                        and {states_args}
                                        '''.format(states_args=states_args),
                            {'from_date': options['date']['date_from'],
                             'to_date': options['date']['date_to'],
                             'code_start': '221101', 'code_end': '223999',
                             'company_ids': self.env.company.id})
        zain_loan = self.env.cr.dictfetchall()
        zain_loan_credit = zain_loan[0]['credit'] if zain_loan[0][
            'credit'] else 0
        zain_loan_dict = {
            'id': 'zain_loan',
            'name': 'Loan from Zain',
            'level': 2,
            'class': 'cash_flow_line_val_tr',
            'columns': [
                {
                    'name': round(((zain_loan_credit) * -1), 2),
                    'class': 'number'}]
        }
        cash_flow_financial_list.append(zain_loan_dict)

        self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                        and journal_item.company_id = %(company_ids)s
                                        and journal_item.date >= %(from_date)s 
                                        and journal_item.date <= %(to_date)s
                                        and {states_args}
                                        '''.format(states_args=states_args),
                            {'from_date': options['date']['date_from'],
                             'to_date': options['date']['date_to'],
                             'code_start': '214101', 'code_end': '214999',
                             'company_ids': self.env.company.id})
        payment_lease = self.env.cr.dictfetchall()
        payment_lease_credit = payment_lease[0]['credit'] if payment_lease[0][
            'credit'] else 0
        payment_lease_debit = payment_lease[0]['debit'] if payment_lease[0][
            'debit'] else 0
        payment_lease_dict = {
            'id': 'payment_lease',
            'name': 'Payment of lease liability',
            'level': 2,
            'class': 'cash_flow_line_val_tr',
            'columns': [
                {
                    'name': round(
                        ((payment_lease_debit - payment_lease_credit) * -1), 2),
                    'class': 'number'}]
        }
        cash_flow_financial_list.append(payment_lease_dict)

        return cash_flow_financial_list

    def get_equivalent_cash_account_sum(self, query, options, states_args):
        self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                                and journal_item.company_id = %(company_ids)s
                                                and journal_item.date <= %(from_date)s 
                                                and {states_args}
                                                '''.format(
            states_args=states_args),
                            {'from_date': options['date']['date_from'],
                             'code_start': '111111', 'code_end': '111299',
                             'company_ids': self.env.company.id})
        equivalent_cash_account = self.env.cr.dictfetchall()
        equivalent_cash_account_credit = equivalent_cash_account[0]['credit'] if \
            equivalent_cash_account[0]['credit'] else 0
        equivalent_cash_account_debit = equivalent_cash_account[0]['debit'] if \
            equivalent_cash_account[0]['debit'] else 0
        equivalent_cash_account_sum = equivalent_cash_account_debit - equivalent_cash_account_credit
        return equivalent_cash_account_sum

    def get_net_cash_generated_financial(self, options, states_args):
        net_cash_generated_list = []

        query = '''select sum(journal_item.credit) as credit, sum(journal_item.debit) as debit 
                    from account_move_line as journal_item
                    left join account_account as account on journal_item.account_id = account.id
                    '''

        self.env.cr.execute(query + '''where account.code between %(code_start)s and %(code_end)s
                                        and journal_item.company_id = %(company_ids)s
                                        and journal_item.date <= %(from_date)s
                                        and {states_args}
                                        '''.format(states_args=states_args),
                            {'from_date': options['date']['date_from'],
                             'code_start': '101003', 'code_end': '111109',
                             'company_ids': self.env.company.id})
        equivalent_cash = self.env.cr.dictfetchall()
        equivalent_cash_credit = equivalent_cash[0]['credit'] if \
            equivalent_cash[0]['credit'] else 0
        equivalent_cash_debit = equivalent_cash[0]['debit'] if \
            equivalent_cash[0]['debit'] else 0
        equivalent_cash_sum = equivalent_cash_debit - equivalent_cash_credit

        equivalent_cash_account_sum = self.get_equivalent_cash_account_sum(
            query, options, states_args)

        ordinary_shares_dict = {
            'id': 'equivalent_cash',
            'name': 'Cash and cash equivalents at the start of the period',
            'level': 2,
            'class': 'cash_flow_line_val_tr',
            'columns': [
                {
                    'name': round(
                        (equivalent_cash_sum + equivalent_cash_account_sum), 2),
                    'class': 'number'}]
        }
        net_cash_generated_list.append(ordinary_shares_dict)
        return net_cash_generated_list

    def get_cash_flow_lines(self, options):
        states_args = """ parent_state = 'posted'"""
        if options['entry'] != 'posted':
            states_args = """ parent_state in ('posted', 'draft')"""
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
                    {'name': self.get_loss_for_period(options, states_args),
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
        adjustment = self.adjustment_1(options, states_args)
        adjustment_index = 3
        net_cash_operating_activities_sum = self.get_loss_for_period(options,
                                                                     states_args)
        for rec in adjustment:
            net_cash_operating_activities_sum += rec['columns'][0]['name']
            cash_flow_lines.insert(adjustment_index, rec)
            adjustment_index += 1
        movement = self.movement_capital(options, states_args)
        movement_index = 9
        for rec in movement:
            net_cash_operating_activities_sum += rec['columns'][0]['name']
            cash_flow_lines.insert(movement_index, rec)
            movement_index += 1

        cash_flow_lines[13]['columns'][0]['name'] = round(
            net_cash_operating_activities_sum, 2)

        investing_activities = self.investing_activities(options, states_args)
        net_cash_investing_activities_sum = 0
        investing_activities_index = 15
        for rec in investing_activities:
            net_cash_investing_activities_sum += rec['columns'][0]['name']
            cash_flow_lines.insert(investing_activities_index, rec)
            investing_activities_index += 1

        cash_flow_lines[17]['columns'][0]['name'] = round(
            net_cash_investing_activities_sum, 2)

        cash_flow_financial = self.get_cash_flow_financial(options, states_args)
        cash_flow_financial_index = 19
        net_cash_financial_activities_sum = 0
        for rec in cash_flow_financial:
            net_cash_financial_activities_sum += rec['columns'][0]['name']
            cash_flow_lines.insert(cash_flow_financial_index, rec)
            cash_flow_financial_index += 1

        cash_flow_lines[24]['columns'][0]['name'] = round(
            net_cash_financial_activities_sum, 2)

        net_cash_generated_financial = self.get_net_cash_generated_financial(
            options, states_args)
        cash_flow_financial_index = 26
        for rec in net_cash_generated_financial:
            cash_flow_lines.insert(cash_flow_financial_index, rec)

        net_increase_decrease = net_cash_operating_activities_sum + net_cash_investing_activities_sum + net_cash_financial_activities_sum
        cash_flow_lines[25]['columns'][0]['name'] = round(net_increase_decrease,
                                                          2)
        cash_equivalent_end_sum = net_increase_decrease + \
                                  cash_flow_lines[26]['columns'][0]['name']
        cash_flow_lines[27]['columns'][0]['name'] = round(
            cash_equivalent_end_sum, 2)

        return cash_flow_lines

    def get_cash_flow_header(self, options):
        if options['date']['period_type'] == 'month':
            month = datetime.strptime(options['date']['date_from'],
                                      "%Y-%m-%d")
            return {
                'name': month.strftime("%B")
            }
        elif options['date']['period_type'] == 'quarter':
            month = datetime.strptime(options['date']['date_from'],
                                      "%Y-%m-%d")
            return {
                'name': 'Quarter'
            }
        elif options['date']['period_type'] == 'year':
            year = datetime.strptime(options['date']['date_from'],
                                     "%Y-%m-%d").year
            return {
                'name': year
            }

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
        lines = self.get_cash_flow_lines(options)
        header = self.get_cash_flow_header(options)
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
            {'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666', 'indent': 2})

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
                sheet.write(row_num, abc + 1, line['columns'][0]['name'], head_col1)
            row_num += 1

        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()
