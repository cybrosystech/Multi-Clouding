from odoo import models, api, fields
import re
from odoo.tools import safe_eval
from odoo.tools.translate import _


class generic_tax_report_inherit(models.AbstractModel):
    _inherit = 'account.generic.tax.report'

    def _init_filter_tax_report(self, options, previous_options=None):
        options['available_tax_reports'] = []
        available_reports = self.env.company.get_available_tax_reports()
        for report in available_reports:
            options['available_tax_reports'].append({
                'id': report.id,
                'name': report.name,
            })
        # The computation of lines groupped by account require calling `compute_all` with the
        # param handle_price_include set to False. This is not compatible with taxes of type group
        # because the base amount can affect the computation of other taxes; hence we disable the
        # option if there are taxes with that configuration.
        options['by_account_available'] = not self.env['account.tax'].search([
            ('amount_type', '=', 'group'),
        ], limit=1)

        options['tax_report'] = (previous_options or {}).get('tax_report')

        generic_reports_with_groupby = {'account_tax', 'tax_account',
                                        'tax_report_custom'}

        if options['tax_report'] not in {0, *generic_reports_with_groupby} and \
                options['tax_report'] not in available_reports.ids:
            # Replace the report in options by the default report if it is not the generic report
            # (always available for all companies) and the report in options is not available for this company
            options['tax_report'] = available_reports and available_reports[
                0].id or 0

        if options['tax_report'] in generic_reports_with_groupby:
            options['group_by'] = options['tax_report']
        else:
            options['group_by'] = False

    def _get_columns_name(self, options):
        columns_header = [{}]

        if options.get('tax_report') and not options.get('group_by'):
            columns_header += [
                {'name': '%s \n %s' % (_('Balance'), self.format_date(options)),
                 'class': 'number', 'style': 'white-space: pre;'}]
            if options.get('comparison') and options['comparison'].get(
                    'periods'):
                for p in options['comparison']['periods']:
                    columns_header += [
                        {'name': '%s \n %s' % (_('Balance'), p.get('string')),
                         'class': 'number', 'style': 'white-space: pre;'}]
        else:
            if options[
                'tax_report'] == 'tax_report_custom' and self.env.company.currency_id.name == 'USD':
                columns_header += [
                    {'name': '%s \n %s' % (_('NET'), self.format_date(options)),
                     'class': 'number'}, {'name': _('TAX'), 'class': 'number'},
                    {'name': '%s \n %s' % (_('NET'), self.format_date(options)),
                     'class': 'number'}, {'name': _('TAX'), 'class': 'number'}]
            elif options.get('comparison') and options['comparison'].get(
                    'periods'):
                for p in options['comparison']['periods']:
                    columns_header += [
                        {'name': '%s \n %s' % (_('NET'), p.get('string')),
                         'class': 'number'},
                        {'name': _('TAX'), 'class': 'number'}]
            else:
                columns_header += [
                    {'name': '%s \n %s' % (_('NET'), self.format_date(options)),
                     'class': 'number'}, {'name': _('TAX'), 'class': 'number'}]
        return columns_header

    @api.model
    def _get_lines(self, options, line_id=None):
        options.update({'menu': 'custom', 'report': 'not_custom'})
        if options['group_by'] == 'tax_report_custom':
            options.update(
                {'report': 'custom', 'menu': 'custom', 'group_by': False,
                 'tax_report': int(options['available_tax_reports'][0]['id'])})
        data = self._compute_tax_report_data(options)
        abcd = 1
        if options.get('tax_report') and not options.get('group_by'):
            if options['report'] == 'custom':
                lines = self._get_lines_by_grid(options, line_id, data)
                for i in lines[0].get('columns'):
                    lines[16].get('columns').append(i)
                for i in lines[17].get('columns'):
                    lines[21].get('columns').append(i)
                for line in lines:
                    if not line.get('columns'):
                        lines.remove(line)
                for abc in lines:
                    if re.match("[0-9]", abc.get('name')):
                        ggg = abc.get('name')[0:3]
                        bbb = abc.get('name').strip('%s' % ggg)
                        abc.update({
                            'name': str(abcd) + '. ' + bbb
                        })
                        abcd += 1
                return lines
            else:
                return self._get_lines_by_grid(options, line_id, data)
        return self._get_lines_by_tax(options, line_id, data)

    def _get_lines_by_grid(self, options, line_id, grids):
        rate = 0
        to_currency = self.env['res.currency'].search(
            [('name', '=', 'AED')])
        if to_currency:
            rate = self.env['res.currency']._get_conversion_rate(
                self.env.company.currency_id, to_currency, self.env.company,
                fields.date.today())
        report = self.env['account.tax.report'].browse(options['tax_report'])
        formulas_dict = dict(
            report.line_ids.filtered(lambda l: l.code and l.formula).mapped(
                lambda l: (l.code, l.formula)))

        # Build the report, line by line
        lines = []
        deferred_total_lines = []  # list of tuples (index where to add the total in lines, tax report line object)
        for current_line in report.get_lines_in_hierarchy():
            hierarchy_level = self._get_hierarchy_level(current_line)
            if current_line.formula:
                # Then it's a total line
                # We defer the adding of total lines, since their balance depends
                # on the rest of the report. We use a special dictionnary for that,
                # keeping track of hierarchy level
                lines.append({'id': 'deferred_total', 'level': hierarchy_level})
                deferred_total_lines.append((len(lines) - 1, current_line))
            elif current_line.tag_name:
                # Then it's a tax grid line
                if options['report'] == 'custom':
                    lines = self._build_tax_grid_line(grids[current_line.id][0],
                                                      hierarchy_level, options,
                                                      lines)
                else:
                    lines.append(
                        self._build_tax_grid_line(grids[current_line.id][0],
                                                  hierarchy_level, options,
                                                  lines))
            else:
                # Then it's a title line
                if options['report'] == 'custom':
                    abc = self._build_tax_section_line(current_line,
                                                       hierarchy_level, options)
                    if abc:
                        lines.append(abc)
                else:
                    lines.append(
                        self._build_tax_section_line(current_line,
                                                     hierarchy_level,
                                                     options))
        if options['report'] == 'custom':
            lines[11].get('columns').clear()
            for rec in lines[19].get('columns'):
                lines[11].get('columns').append(rec)
        # Fill in in the total for each title line and get a mapping linking line codes to balances
        balances_by_code = self._postprocess_lines(lines, options)
        for (index, total_line) in deferred_total_lines:
            hierarchy_level = self._get_hierarchy_level(total_line)
            # number_period option contains 1 if no comparison, or the number of periods to compare with if there is one.
            total_period_number = 1 + (options['comparison'].get('periods') and
                                       options['comparison'][
                                           'number_period'] or 0)
            lines[index] = self._build_total_line(total_line, balances_by_code,
                                                  formulas_dict,
                                                  hierarchy_level,
                                                  total_period_number, options)
        if options['report'] == 'custom':
            lines[15].get('columns').append(lines[22].get('columns')[0])
            lines.remove(lines[22])
            lines.remove(lines[21])
            for i in lines:
                if i.get('name') == 'VAT on Sales and all other Outputs ':
                    sales = i.get('columns')[1]
                if i.get('name') == '14. Total value of due tax for the period':
                    i.get('columns').append({})
                    i.get('columns').append(sales)
                if i.get('name') == 'VAT on Expenses and all other Inputs ':
                    purchase = i.get('columns')[1]
                if i.get(
                        'name') == '15. Total value of recoverable tax for the period':
                    i.get('columns').append({})
                    i.get('columns').append(purchase)
                if i.get(
                        'name') == '16. Net VAT due (or reclaimed) for the period':
                    i.get('columns').append({})
                    i.get('columns').append(
                        {'name': str(
                            self.env.company.currency_id.symbol) + ' ' +
                                 str('{:20,.2f}'.format(round(
                                     sales['balance'] - purchase[
                                         'balance'], 2))),
                         'style': 'white-space:nowrap;',
                         'balance': round(sales['balance'] - purchase[
                             'balance'], 2) or 0})
                if i.get('name') == 'Net VAT Due':
                    i.get('columns').append({})
                    i.get('columns').append(
                        {'name': str(
                            self.env.company.currency_id.symbol) + ' ' + str(
                            '{:20,.2f}'.format(round(
                                sales['balance'] - purchase[
                                    'balance'], 2))),
                         'style': 'white-space:nowrap;',
                         'balance': round(sales['balance'] - purchase[
                             'balance'], 2) or 0})
                if self.env.company.currency_id.name == 'USD':
                    append_line = self.columns_add(i.get('columns'), rate,
                                                   to_currency)
                    for append in append_line:
                        i.get('columns').append(append)
            options.update(
                {'report': 'custom', 'menu': 'custom',
                 'group_by': 'tax_report_custom',
                 'tax_report': 'tax_report_custom'})
        return lines

    def _build_tax_grid_line(self, grid_data, hierarchy_level, options, lines):
        """Return the report line dictionary corresponding to a given tax grid.

        Used when grouping the report by tax grid.
        """
        columns = []
        if options['report'] == 'custom':
            for period in grid_data['periods']:
                columns += [{'name': self.format_value(period['balance']),
                             'style': 'white-space:nowrap;',
                             'balance': period['balance']}]

            for i in lines:
                if i.get('name') == grid_data['obj'].name:
                    i.get('columns').append(columns[0])
                    return lines

            rslt = {
                'id': grid_data['obj'].id,
                'name': grid_data['obj'].name,
                'unfoldable': False,
                'columns': columns,
                'level': hierarchy_level,
                'line_code': grid_data['obj'].code,
            }

            if grid_data['obj'].report_action_id:
                rslt['action_id'] = grid_data['obj'].report_action_id.id
            else:
                rslt['caret_options'] = 'account.tax.report.line'
            lines.append(rslt)
            return lines
        else:
            for period in grid_data['periods']:
                columns += [{'name': self.format_value(period['balance']),
                             'style': 'white-space:nowrap;',
                             'balance': period['balance']}]

            rslt = {
                'id': grid_data['obj'].id,
                'name': grid_data['obj'].name,
                'unfoldable': False,
                'columns': columns,
                'level': hierarchy_level,
                'line_code': grid_data['obj'].code,
            }

            if grid_data['obj'].report_action_id:
                rslt['action_id'] = grid_data['obj'].report_action_id.id
            else:
                rslt['caret_options'] = 'account.tax.report.line'
            return rslt

    def _build_tax_section_line(self, section, hierarchy_level, options):
        """Return the report line dictionary corresponding to a given section.

        Used when grouping the report by tax grid.
        """
        if options['report'] == 'custom':
            if not re.search("scope", section.name):
                if not re.search("(Tax)", section.name):
                    return {
                        'id': 'section_' + str(section.id),
                        'name': section.name.replace('(Base)', ''),
                        'unfoldable': False,
                        'columns': [],
                        'level': hierarchy_level,
                        'line_code': section.code,
                    }
                else:
                    return None
        else:
            return {
                'id': 'section_' + str(section.id),
                'name': section.name,
                'unfoldable': False,
                'columns': [],
                'level': hierarchy_level,
                'line_code': section.code,
            }

    def _build_total_line(self, report_line, balances_by_code, formulas_dict,
                          hierarchy_level, number_periods, options):
        """Return the report line dictionary corresponding to a given total line.

        Compute if from its formula.
        """

        def expand_formula(formula):
            for word in re.split(r'\W+', formula):
                if formulas_dict.get(word):
                    formula = re.sub(r'\b%s\b' % word, '(%s)' % expand_formula(
                        formulas_dict.get(word)), formula)
            return formula

        columns = []
        for period_index in range(0, number_periods):
            period_balances_by_code = {code: balances[period_index] for
                                       code, balances in
                                       balances_by_code.items()}
            period_date_from = (period_index == 0) and options['date'][
                'date_from'] or options['comparison']['periods'][
                                   period_index - 1]['date_from']
            period_date_to = (period_index == 0) and options['date'][
                'date_to'] or \
                             options['comparison']['periods'][period_index - 1][
                                 'date_to']
            if not options['report'] == 'custom':
                eval_dict = self._get_total_line_eval_dict(
                    period_balances_by_code,
                    period_date_from,
                    period_date_to, options)
                period_total = safe_eval.safe_eval(
                    expand_formula(report_line.formula), eval_dict)
                columns.append({
                    'name': '' if period_total is None else self.format_value(
                        period_total),
                    'style': 'white-space:nowrap;',
                    'balance': period_total or 0.0})

        return {
            'id': 'total_' + str(report_line.id),
            'name': report_line.name,
            'unfoldable': False,
            'columns': columns,
            'level': hierarchy_level,
            'line_code': report_line.code
        }

    def columns_add(self, lines, rate, to_currency):
        abc = []
        for line in lines:
            if line:
                rates = rate if rate > 1 else 3.6725
                aed_amount = int(line['balance']) * rates
                amount = to_currency.name + ' ' + str(
                    '{:20,.2f}'.format(round(aed_amount, 2)))
                abc.append({
                    'name': amount,
                    'style': 'white-space:nowrap;',
                    'balance': amount
                })
            else:
                abc.append({})
        return abc
