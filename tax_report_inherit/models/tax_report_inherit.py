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
            return self._get_lines_by_grid(options, line_id, data)
        return self._get_lines_by_tax(options, line_id, data)

    def _get_lines_by_grid(self, options, line_id, grids):
        # Fetch the report layout to use
        report = self.env['account.tax.report'].browse(options['tax_report'])
        formulas_dict = dict(report.line_ids.filtered(lambda l: l.code and l.formula).mapped(lambda l: (l.code, l.formula)))

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
                deferred_total_lines.append((len(lines)-1, current_line))
            elif current_line.tag_name:
                # Then it's a tax grid line
                lines.append(self._build_tax_grid_line(grids[current_line.id][0], hierarchy_level))
            else:
                # Then it's a title line
                lines.append(self._build_tax_section_line(current_line, hierarchy_level))

        # # Fill in in the total for each title line and get a mapping linking line codes to balances
        # balances_by_code = self._postprocess_lines(lines, options)
        # for (index, total_line) in deferred_total_lines:
        #     hierarchy_level = self._get_hierarchy_level(total_line)
        #     # number_period option contains 1 if no comparison, or the number of periods to compare with if there is one.
        #     total_period_number = 1 + (options['comparison'].get('periods') and options['comparison']['number_period'] or 0)
        #     lines[index] = self._build_total_line(total_line, balances_by_code, formulas_dict, hierarchy_level, total_period_number, options)

        return lines