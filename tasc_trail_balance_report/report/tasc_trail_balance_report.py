from dateutil.relativedelta import relativedelta

from odoo import models, api, _, fields
import calendar
from datetime import datetime

from odoo.tools import date_utils
from odoo.tools.safe_eval import json
import io
import xlsxwriter


class TascTrailBalance(models.Model):
    _name = 'tasc.trail.balance'

    report_json = fields.Char()

    def _get_templates(self):
        return {
            'main_template': 'tasc_trail_balance_report.tasc_trail_balance_html_content_view',
            'main_table_header_template': 'account_reports.main_table_header',
            'line_template': 'cash_flow_statement_report.line_template_cash_flow',
            'footnotes_template': 'account_reports.footnotes_template',
            'budget_analysis_search_view': 'tasc_trail_balance_report.tasc_trail_balance_search_view',
        }

    @api.model
    def get_button_trail_balance(self):
        return [
            {'name': _('Export (XLSX)'), 'sequence': 2,
             'action': 'print_xlsx_tasc_trail_balance',
             'file_export_type': _('XLSX')},
        ]

    def get_cash_flow_information(self, filter):
        options = self.env['cash.flow.statement']._get_cashflow_options(filter)
        info = {
            'options': options,
            'main_html': self.get_html_content(options),
            'searchview_html': self.env['ir.ui.view']._render_template(
                self._get_templates().get('budget_analysis_search_view', ),
                values={'options': options}),
            'buttons': self.get_button_trail_balance()
        }
        return info

    def total_lines_align(self, lines):
        for line in lines:
            difference = line['initial']['debit'] - line['initial']['credit']
            if difference >= 0:
                line['initial'].update({
                    'debit': difference,
                    'credit': 0
                })
            else:
                line['initial'].update({
                    'debit': 0,
                    'credit': -1 * difference
                })

            line.update({'total': {
                'debit': line['initial']['debit'] + line['monthly']['debit'],
                'credit': line['initial']['credit'] + line['monthly']['credit']
            }})
        return lines

    def get_html_content(self, options):
        to_currency = self.env['res.currency'].search([('name', '=', 'USD')])
        templates = self._get_templates()
        template = templates['main_template']
        values = {'model': self}
        lines = self.get_trail_balance_line(options, to_currency)
        lines = self.total_lines_align(lines)
        tasc_trail_obj = self.sudo().search([])
        if not tasc_trail_obj:
            self.env['tasc.trail.balance'].sudo().create({
                'report_json': json.dumps(lines)
            })
        else:
            tasc_trail_obj.report_json = json.dumps(lines)
        header = self.get_trail_balance_header(options)
        values['lines'] = {'lines': lines, 'header': header}
        html = self.env.ref(template)._render(values)
        return html

    def get_trail_balance_header(self, options):
        return ['Account', 'Debit', 'Credit']

    def get_trail_balance_line(self, options, to_currency):
        company_conversion_id = self.env['res.company'].search([
            ('id', '=', self.env.company.id)])
        accounts = self.get_chart_accounts(options)
        currencies = self.get_currency_dict(options)
        lines = []
        lines_demo = []
        states_args = """ parent_state = 'posted'"""
        if options['entry'] != 'posted':
            states_args = """ parent_state in ('to_approve','posted', 'draft')"""
        demo_date = datetime.strptime(options['date']['date_from'], "%Y-%m-%d")
        for account in accounts:
            test_move_dict = {
                'account': str(account['code']) + ' ' + account['name'],
                'debit': 0,
                'credit': 0}
            test_move_dict_demo = {'initial': {
                'account': str(account['code']) + ' ' + account['name'],
                'debit': 0,
                'credit': 0}, 'monthly': {
                'account': str(account['code']) + ' ' + account['name'],
                'debit': 0,
                'credit': 0}}
            for currency in currencies:
                from_currency = self.env['res.currency'].browse(currency['id'])
                if options['date_filter'] == 'this_month':
                    query = '''select coalesce(sum(move_line.credit), 0)as credit, coalesce(sum(move_line.debit), 0) as debit
                     from account_move_line as move_line
                    where move_line.account_id = %(account)s and 
                    move_line.currency_id = %(currency)s and move_line.date between %(date_from)s and %(date_to)s
                    and move_line.company_id = %(company)s and {states_args}'''.format(
                        states_args=states_args)
                    self.env.cr.execute(query, {'account': account['id'],
                                                'currency': currency['id'],
                                                'date_from': options['date'][
                                                    'date_from'],
                                                'date_to': options['date'][
                                                    'date_to'],
                                                'company': self.env.company.id})
                    move_line_dict = self.env.cr.dictfetchall()
                    def_rate = self.env[
                        'res.currency']._get_conversion_rate(
                        self.env.company.currency_id, from_currency,
                        self.env.company,
                        fields.date.today())
                    if move_line_dict[0]['debit'] != 0 or move_line_dict[0][
                        'credit'] != 0:
                        total_debit = move_line_dict[0]['debit'] * def_rate
                        total_credit = move_line_dict[0]['credit'] * def_rate
                        rate = self.env['res.currency']._get_conversion_rate(
                            from_currency, to_currency, company_conversion_id,
                            fields.date.today())
                        test_move_dict.update({'debit': test_move_dict[
                                                            'debit'] + (
                                                                total_debit * rate),
                                               'credit': test_move_dict[
                                                             'credit'] + (
                                                                 total_credit * rate)})
                        test_move_dict_demo['monthly'].update(
                            {'debit': test_move_dict_demo['monthly'][
                                          'debit'] + (
                                              total_debit * rate),
                             'credit': test_move_dict_demo['monthly'][
                                           'credit'] + (
                                               total_credit * rate)})
                    previous_date = demo_date - relativedelta(days=1)
                    def_rate_initial = self.env[
                        'res.currency']._get_conversion_rate(
                        self.env.company.currency_id, from_currency,
                        self.env.company,
                        previous_date)
                    query2 = '''select coalesce(sum(move_line.credit), 0)as credit, coalesce(sum(move_line.debit), 0) as debit
                                         from account_move_line as move_line
                                        where move_line.account_id = %(account)s and 
                                        move_line.currency_id = %(currency)s and move_line.date <= %(date_from)s
                                        and move_line.company_id = %(company)s and {states_args}'''.format(
                        states_args=states_args)
                    self.env.cr.execute(query2, {'account': account['id'],
                                                 'currency': currency['id'],
                                                 'date_from': previous_date,
                                                 'company': self.env.company.id})
                    move_line_dict_initial = self.env.cr.dictfetchall()
                    if move_line_dict_initial[0]['debit'] != 0 or \
                            move_line_dict_initial[0][
                                'credit'] != 0:
                        total_debit_initial = move_line_dict_initial[0][
                                                  'debit'] * def_rate_initial
                        total_credit_initial = move_line_dict_initial[0][
                                                   'credit'] * def_rate_initial
                        rate = self.env[
                            'res.currency']._get_conversion_rate(
                            from_currency, to_currency,
                            company_conversion_id,
                            previous_date)
                        test_move_dict_demo['initial'].update(
                            {'debit': test_move_dict_demo['initial'][
                                          'debit'] + (
                                              total_debit_initial * rate),
                             'credit': test_move_dict_demo['initial'][
                                           'credit'] + (
                                               total_credit_initial * rate)})

                elif options['date_filter'] in ['this_year', 'last_year']:
                    previous_date = demo_date - relativedelta(days=1)
                    for i in range(1, 13):
                        month_range = calendar.monthrange(demo_date.year, i)
                        start_date = datetime(demo_date.year, i, 1)
                        end_date = datetime(demo_date.year, i, month_range[1])
                        query = '''select coalesce(sum(move_line.credit), 0)as credit, coalesce(sum(move_line.debit), 0) as debit
                                             from account_move_line as move_line
                                            where move_line.account_id = %(account)s and 
                                            move_line.currency_id = %(currency)s and move_line.date between %(date_from)s and %(date_to)s
                                            and move_line.company_id = %(company)s and {states_args}'''.format(
                            states_args=states_args)
                        self.env.cr.execute(query, {'account': account['id'],
                                                    'currency': currency['id'],
                                                    'date_from': str(
                                                        start_date),
                                                    'date_to': str(end_date),
                                                    'company': self.env.company.id})
                        move_line_dict = self.env.cr.dictfetchall()
                        def_rate = self.env[
                            'res.currency']._get_conversion_rate(
                            self.env.company.currency_id, from_currency,
                            self.env.company,
                            end_date)
                        if move_line_dict[0]['debit'] != 0 or move_line_dict[0][
                            'credit'] != 0:
                            total_debit = move_line_dict[0]['debit'] * def_rate
                            total_credit = move_line_dict[0]['credit'] * def_rate
                            rate = self.env[
                                'res.currency']._get_conversion_rate(
                                from_currency, to_currency,
                                company_conversion_id,
                                end_date)
                            test_move_dict_demo['monthly'].update(
                                {'debit': test_move_dict_demo['monthly'][
                                              'debit'] + (
                                                  total_debit * rate),
                                 'credit': test_move_dict_demo['monthly'][
                                               'credit'] + (
                                                   total_credit * rate)})
                    def_rate_initial = self.env[
                        'res.currency']._get_conversion_rate(
                        self.env.company.currency_id, from_currency,
                        self.env.company,
                        previous_date)
                    query2 = '''select coalesce(sum(move_line.credit), 0)as credit, coalesce(sum(move_line.debit), 0) as debit
                                                             from account_move_line as move_line
                                                            where move_line.account_id = %(account)s and 
                                                            move_line.currency_id = %(currency)s and move_line.date <= %(date_from)s
                                                            and move_line.company_id = %(company)s and {states_args}'''.format(
                        states_args=states_args)
                    self.env.cr.execute(query2, {'account': account['id'],
                                                 'currency': currency['id'],
                                                 'date_from': previous_date,
                                                 'company': self.env.company.id})
                    move_line_dict_initial = self.env.cr.dictfetchall()
                    if move_line_dict_initial[0]['debit'] != 0 or \
                            move_line_dict_initial[0][
                                'credit'] != 0:
                        total_debit_initial = move_line_dict_initial[0][
                                                  'debit'] * def_rate_initial
                        total_credit_initial = move_line_dict_initial[0][
                                                   'credit'] * def_rate_initial
                        rate = self.env[
                            'res.currency']._get_conversion_rate(
                            from_currency, to_currency,
                            company_conversion_id,
                            previous_date)
                        test_move_dict_demo['initial'].update(
                            {'debit': test_move_dict_demo['initial'][
                                          'debit'] + (
                                              total_debit_initial * rate),
                             'credit': test_move_dict_demo['initial'][
                                           'credit'] + (
                                               total_credit_initial * rate)})

            lines.append(test_move_dict)
            lines_demo.append(test_move_dict_demo)
        return lines_demo

    def get_chart_accounts(self, options):
        query = '''select chart_accounts.id, chart_accounts.name, chart_accounts.code
        from account_account as chart_accounts where chart_accounts.company_id = %(company)s order by chart_accounts.code ASC'''
        self.env.cr.execute(query, {'company': self.env.company.id})
        account_dict = self.env.cr.dictfetchall()
        return account_dict

    def get_currency_dict(self, options):
        query = '''select currency.id, currency.name, currency.active 
        from res_currency as currency where currency.active = True'''
        self.env.cr.execute(query)
        currency_dict = self.env.cr.dictfetchall()
        return currency_dict

    def print_xlsx_tasc_trail_balance(self, options, params):
        return {
            'type': 'ir.actions.report',
            'data': {'model': self.env.context.get('model'),
                     'options': json.dumps(options,
                                           default=date_utils.json_default),
                     'output_format': 'xlsx',
                     'financial_id': self.env.context.get('id'),
                     'allowed_company_ids': self.env.context.get(
                         'allowed_company_ids'),
                     'report_name': 'Tasc Budget analysis Report',
                     },
            'report_type': 'xlsx'
        }

    @api.model
    def get_xlsx(self, options, response=None):
        # date_filter_name = self.env['cash.flow.statement'].get_cash_flow_header(
        #     options)
        to_currency = self.env['res.currency'].search([('name', '=', 'USD')])
        # lines = self.get_trail_balance_line(options, to_currency)
        # lines = self.total_lines_align(lines)
        tasc_trail_obj = self.sudo().search([])
        lines = json.loads(tasc_trail_obj.report_json)
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet()
        sheet.set_row(4, 20)
        main_head = workbook.add_format(
            {'font_size': 13, 'align': 'center', 'border': 1,
             'bg_color': '#fcd15b'})
        sub_head = workbook.add_format(
            {'font_size': 12, 'align': 'center', 'border': 1,
             'bg_color': '#5db5fc'})
        line_style = workbook.add_format(
            {'font_size': 12, 'bold': True})
        sub_line_style = workbook.add_format(
            {'font_size': 12, 'align': 'right'})
        row_head = 6
        col_head = 1
        sheet.merge_range('B5:D5', 'Account', main_head)
        sheet.merge_range('E5:H5', 'Initial', main_head)
        sheet.merge_range('I5:L5', 'Current', main_head)
        sheet.merge_range('M5:P5', 'Current', main_head)
        sheet.merge_range('E6:F6', 'Debit', sub_head)
        sheet.merge_range('G6:H6', 'Credit', sub_head)
        sheet.merge_range('I6:J6', 'Debit', sub_head)
        sheet.merge_range('K6:L6', 'Credit', sub_head)
        sheet.merge_range('M6:N6', 'Debit', sub_head)
        sheet.merge_range('O6:P6', 'Debit', sub_head)
        for line in lines:
            if line['initial']['debit'] != 0 or line['initial']['credit'] != 0 or line['monthly']['debit'] != 0 or line['monthly']['credit'] != 0:
                sheet.merge_range(row_head, col_head, row_head, col_head + 2,
                                  line['initial']['account'], line_style)
                sheet.merge_range(row_head, col_head + 3, row_head,
                                  col_head + 4,
                                  to_currency.symbol + str(round(line['initial']['debit'], 2)),
                                  sub_line_style)
                sheet.merge_range(row_head, col_head + 5, row_head,
                                  col_head + 6,
                                  to_currency.symbol + str(round(line['initial']['credit'], 2)),
                                  sub_line_style)
                sheet.merge_range(row_head, col_head + 7, row_head,
                                  col_head + 8,
                                  to_currency.symbol + str(round(line['monthly']['debit'], 2)),
                                  sub_line_style)
                sheet.merge_range(row_head, col_head + 9, row_head,
                                  col_head + 10,
                                  to_currency.symbol + str(round(line['monthly']['credit'], 2)),
                                  sub_line_style)
                sheet.merge_range(row_head, col_head + 11, row_head,
                                  col_head + 12,
                                  to_currency.symbol + str(round(line['total']['debit'], 2)),
                                  sub_line_style)
                sheet.merge_range(row_head, col_head + 13, row_head,
                                  col_head + 14,
                                  to_currency.symbol + str(round(line['total']['credit'], 2)),
                                  sub_line_style)
                row_head += 1
        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()
