from odoo import models, api
import re
from odoo.tools import safe_eval


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

    @api.model
    def _get_lines(self, options, line_id=None):
        options.update({'menu': 'custom', 'report': 'not_custom'})
        if options['group_by'] == 'tax_report_custom':
            options.update(
                {'report': 'custom', 'menu': 'custom', 'group_by': False,
                 'tax_report': int(options['available_tax_reports'][0]['id'])})
        data = self._compute_tax_report_data(options)
        if options.get('tax_report') and not options.get('group_by'):
            return self._get_lines_by_grid(options, line_id, data)
        return self._get_lines_by_tax(options, line_id, data)

    def _get_lines_by_grid(self, options, line_id, grids):
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
            for i in lines:
                if i.get('id') == 'section_1':
                    sales = i.get('columns')[1]
                if i.get('id') == 'total_48':
                    i.get('columns').append({})
                    i.get('columns').append(sales)
                if i.get('id') == 'section_19':
                    purchase = i.get('columns')[1]
                if i.get('id') == 'total_49':
                    i.get('columns').append({})
                    i.get('columns').append(purchase)
                if i.get('id') == 'total_50':
                    i.get('columns').append({})
                    i.get('columns').append(
                        {'name': str(sales['balance'] - purchase['balance']) + ' ' + str(self.env.company.currency_id.name),
                         'style': 'white-space:nowrap;',
                         'balance': sales['balance'] - purchase[
                             'balance'] or 0})
                if i.get('id') == 'total_47':
                    i.get('columns').append({})
                    i.get('columns').append(
                        {'name': str(sales['balance'] - purchase['balance']) + ' ' + str(self.env.company.currency_id.name),
                         'style': 'white-space:nowrap;',
                         'balance': sales['balance'] - purchase[
                             'balance'] or 0})
                if i.get('name') == 'Sub Total':
                    lines.remove(i)
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
            # abc = lines
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
            if not re.search("(Tax)", section.name) or re.search("scope", section.name):
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
