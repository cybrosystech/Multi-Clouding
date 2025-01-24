# -*- coding: utf-8 -*-
from odoo import models, _, fields
from odoo.tools import float_compare
from odoo.tools.misc import DEFAULT_SERVER_DATE_FORMAT


class TascTrialBalance(models.AbstractModel):
    _name = 'tasc.trial.balance'
    _inherit = 'account.report.custom.handler'
    _description = 'Tasc Trial Balance Custom Handler'

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals, warnings=None):
        def _update_column(line, column_key, new_value, blank_if_zero=False):
            line['columns'][column_key]['name'] = self.env['account.report'].format_value(options, new_value,
                                                                                          figure_type='monetary',
                                                                                          blank_if_zero=blank_if_zero)
            line['columns'][column_key]['no_format'] = new_value

        def _update_balance_columns(line, debit_column_key, credit_column_key, total_diff_values_key):
            debit_value = line['columns'][debit_column_key]['no_format'] if debit_column_key is not None else False
            credit_value = line['columns'][credit_column_key]['no_format'] if credit_column_key is not None else False

            if debit_value and credit_value:
                new_debit_value = 0.0
                new_credit_value = 0.0

                if float_compare(debit_value, credit_value,
                                 precision_digits=self.env.company.currency_id.decimal_places) == 1:
                    new_debit_value = debit_value - credit_value
                    total_diff_values[total_diff_values_key] += credit_value
                else:
                    new_credit_value = (debit_value - credit_value) * -1
                    total_diff_values[total_diff_values_key] += debit_value

                _update_column(line, debit_column_key, new_debit_value)
                _update_column(line, credit_column_key, new_credit_value)

        lines = [line[1] for line in
                 self.env['account.general.ledger.report.handler']._dynamic_lines_generator(report, options,
                                                                                            all_column_groups_expression_totals,
                                                                                            warnings=warnings)]
        total_diff_values = {
            'initial_balance': 0.0,
            'end_balance': 0.0,
        }
        # We need to find the index of debit and credit columns for initial and end balance in case of extra custom columns
        init_balance_debit_index = next(
            (index for index, column in enumerate(options['columns']) if column.get('expression_label') == 'debit'),
            None)
        init_balance_credit_index = next(
            (index for index, column in enumerate(options['columns']) if column.get('expression_label') == 'credit'),
            None)

        end_balance_debit_index = -(next((index for index, column in enumerate(reversed(options['columns'])) if
                                          column.get('expression_label') == 'debit'), -1) + 1) \
                                  or None
        end_balance_credit_index = -(next((index for index, column in enumerate(reversed(options['columns'])) if
                                           column.get('expression_label') == 'credit'), -1) + 1) \
                                   or None

        for line in lines[:-1]:
            # Initial balance
            res_model = report._get_model_info_from_id(line['id'])[0]
            if res_model == 'account.account':
                # Initial balance
                _update_balance_columns(line, init_balance_debit_index, init_balance_credit_index, 'initial_balance')

                # End balance
                _update_balance_columns(line, end_balance_debit_index, end_balance_credit_index, 'end_balance')

            line.pop('expand_function', None)
            line.pop('groupby', None)
            line.update({
                'unfoldable': False,
                'unfolded': False,
            })
        # Total line
        if lines:
            total_line = lines[-1]

            for index, balance_key in zip(
                    (init_balance_debit_index, init_balance_credit_index, end_balance_debit_index,
                     end_balance_credit_index),
                    ('initial_balance', 'initial_balance', 'end_balance', 'end_balance')
            ):
                if index is not None:
                    _update_column(total_line, index,
                                   total_line['columns'][index]['no_format'] - total_diff_values[balance_key],
                                   blank_if_zero=False)
        return [(0, line) for line in lines]

    def _caret_options_initializer(self):
        return {}

    def _custom_options_initializer(self, report, options, previous_options=None):
        """ Modifies the provided options to add a column group for initial balance and end balance, as well as the appropriate columns.
        """
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        default_group_vals = {'horizontal_groupby_element': {}, 'forced_options': {}}

        # Columns between initial and end balance must not include initial balance; we use a special option key for that in general ledger
        for column_group in options['column_groups'].values():
            column_group['forced_options']['general_ledger_strict_range'] = True
        # Initial balance
        initial_balance_options = self.env['account.general.ledger.report.handler']._get_options_initial_balance(
            options)
        initial_forced_options = {
            'date': initial_balance_options['date'],
            'include_current_year_in_unaff_earnings': initial_balance_options['include_current_year_in_unaff_earnings']
        }
        initial_header_element = [{'name': _("Initial Balance"), 'forced_options': initial_forced_options}]
        col_headers_initial = [
            initial_header_element,
            *options['column_headers'][1:],
        ]
        initial_column_group_vals = report._generate_columns_group_vals_recursively(col_headers_initial,
                                                                                    default_group_vals)
        initial_columns, initial_column_groups = report._build_columns_from_column_group_vals(initial_forced_options,
                                                                                              initial_column_group_vals)
        # End balance
        end_date_to = options['date']['date_to']
        end_date_from = options['date']['date_from']
        end_forced_options = {
            'date': {
                'mode': 'range',
                'date_to': fields.Date.from_string(end_date_to).strftime(DEFAULT_SERVER_DATE_FORMAT),
                'date_from': fields.Date.from_string(end_date_from).strftime(DEFAULT_SERVER_DATE_FORMAT)
            }
        }
        end_header_element = [{'name': _("End Balance"), 'forced_options': end_forced_options}]
        col_headers_end = [
            end_header_element,
            *options['column_headers'][1:],
        ]
        end_column_group_vals = report._generate_columns_group_vals_recursively(col_headers_end, default_group_vals)
        end_columns, end_column_groups = report._build_columns_from_column_group_vals(end_forced_options,
                                                                                      end_column_group_vals)
        # Update options
        options['column_headers'][0] = initial_header_element + options['column_headers'][0] + end_header_element
        options['column_groups'].update(initial_column_groups)
        options['column_groups'].update(end_column_groups)
        options['columns'] = initial_columns + options['columns'] + end_columns
        options['ignore_totals_below_sections'] = True  # So that GL does not compute them
        options['display_hierarchy_filter'] = False
        report._init_options_order_column(options, previous_options)

    def _custom_line_postprocessor(self, report, options, lines, warnings=None):
        # If the hierarchy is enabled, ensure to add the o_account_coa_column_contrast class to the hierarchy lines
        if options.get('hierarchy'):
            for line in lines:
                model, dummy = report._get_model_info_from_id(line['id'])
                if model == 'account.group':
                    line_classes = line.get('class', '')
                    line['class'] = line_classes + ' o_account_coa_column_contrast_hierarchy'
        return lines
        
        
class AccountReport(models.Model):
    _inherit = 'account.report'


    def _inject_report_into_xlsx_sheet(self, options, workbook, sheet):
        if options["available_variants"][0][
            "name"] == 'TASC Trial Balance':
            def write_with_colspan(sheet, x, y, value, colspan, style):
                if colspan == 1:
                    sheet.write(y, x, value, style)
                else:
                    sheet.merge_range(y, x, y, x + colspan - 1, value, style)

            date_default_col1_style = workbook.add_format(
                {'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666',
                 'indent': 2, 'num_format': 'yyyy-mm-dd'})
            date_default_style = workbook.add_format(
                {'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666',
                 'num_format': 'yyyy-mm-dd'})
            default_col1_style = workbook.add_format(
                {'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666',
                 'indent': 2})
            default_col2_style = workbook.add_format(
                {'font_name': 'Arial', 'font_size': 12,
                 'font_color': '#666666'})
            default_style = workbook.add_format(
                {'font_name': 'Arial', 'font_size': 12,
                 'font_color': '#666666'})
            title_style = workbook.add_format(
                {'font_name': 'Arial', 'bold': True, 'bottom': 2})
            level_0_style = workbook.add_format(
                {'font_name': 'Arial', 'bold': True, 'font_size': 13,
                 'bottom': 6, 'font_color': '#666666'})
            level_1_col1_style = workbook.add_format(
                {'font_name': 'Arial', 'bold': True, 'font_size': 13,
                 'bottom': 1, 'font_color': '#666666', 'indent': 1})
            level_1_col1_total_style = workbook.add_format(
                {'font_name': 'Arial', 'bold': True, 'font_size': 13,
                 'bottom': 1, 'font_color': '#666666'})
            level_1_col2_style = workbook.add_format(
                {'font_name': 'Arial', 'bold': True, 'font_size': 13,
                 'bottom': 1, 'font_color': '#666666'})
            level_1_style = workbook.add_format(
                {'font_name': 'Arial', 'bold': True, 'font_size': 13,
                 'bottom': 1, 'font_color': '#666666'})
            level_2_col1_style = workbook.add_format(
                {'font_name': 'Arial', 'bold': True, 'font_size': 12,
                 'font_color': '#666666', 'indent': 2})
            level_2_col1_total_style = workbook.add_format(
                {'font_name': 'Arial', 'bold': True, 'font_size': 12,
                 'font_color': '#666666', 'indent': 1})
            level_2_col2_style = workbook.add_format(
                {'font_name': 'Arial', 'bold': True, 'font_size': 12,
                 'font_color': '#666666'})
            level_2_style = workbook.add_format(
                {'font_name': 'Arial', 'bold': True, 'font_size': 12,
                 'font_color': '#666666'})
            col1_styles = {}

            print_mode_self = self.with_context(no_format=True)
            lines = self._filter_out_folded_children(
                print_mode_self._get_lines(options))

            # For reports with lines generated for accounts, the account name and codes are shown in a single column.
            # To help user post-process the report if they need, we should in such a case split the account name and code in two columns.
            account_lines_split_names = {}
            for line in lines:
                line_model = self._get_model_info_from_id(line['id'])[0]
                if line_model == 'account.account':
                    # Reuse the _split_code_name to split the name and code in two values.
                    # account_lines_split_names[line['id']] = self.env['account.account']._split_code_name(line['name'])
                    account_lines_split_names[line['id']] = self.env[
                        'account.account']._split_code_name(line['name'])

            # Set the first column width to 50.
            # If we have account lines and split the name and code in two columns, we will also set the second column.
            sheet.set_column(0, 0, 50)
            if len(account_lines_split_names) > 0:
                sheet.set_column(1, 1, 13)

            original_x_offset = 1 if len(account_lines_split_names) > 0 else 0

            y_offset = 0
            # 1 and not 0 to leave space for the line name. original_x_offset allows making place for the code column if needed.
            x_offset = original_x_offset + 1

            # Add headers.
            # For this, iterate in the same way as done in main_table_header template
            column_headers_render_data = self._get_column_headers_render_data(
                options)
            for header_level_index, header_level in enumerate(
                    options['column_headers']):
                for header_to_render in header_level * \
                                        column_headers_render_data[
                                            'level_repetitions'][
                                            header_level_index]:
                    colspan = header_to_render.get('colspan',
                                                   column_headers_render_data[
                                                       'level_colspan'][
                                                       header_level_index])
                    write_with_colspan(sheet, x_offset, y_offset,
                                       header_to_render.get('name', ''),
                                       colspan, title_style)
                    x_offset += colspan
                if options['show_growth_comparison']:
                    write_with_colspan(sheet, x_offset, y_offset, '%', 1,
                                       title_style)
                y_offset += 1
                x_offset = original_x_offset + 1

            if account_lines_split_names:
                # If we have a separate account code column, add a title for it
                sheet.write(y_offset+1, x_offset - 2, _("Account Code"),
                            title_style)
                sheet.write(y_offset + 1, x_offset - 1, _("Account Name"),
                            title_style)

            for subheader in column_headers_render_data['custom_subheaders']:
                colspan = subheader.get('colspan', 1)
                write_with_colspan(sheet, x_offset - 1, y_offset,
                                   subheader.get('name', ''), colspan,
                                   title_style)
                x_offset += colspan
            y_offset += 1
            x_offset = original_x_offset + 1

            for column in options['columns']:
                colspan = column.get('colspan', 1)
                write_with_colspan(sheet, x_offset, y_offset,
                                   column.get('name', ''), colspan, title_style)
                x_offset += colspan
            y_offset += 1

            if options.get('order_column'):
                lines = self.sort_lines(lines, options)

            # Add lines.
            for y in range(0, len(lines)):
                level = lines[y].get('level')
                is_total_line = 'total' in lines[y].get('class', '').split(' ')
                if level == 0:
                    y_offset += 1
                    style = level_0_style
                    col1_style = style
                    col2_style = style
                elif level == 1:
                    style = level_1_style
                    col1_style = level_1_col1_total_style if is_total_line else level_1_col1_style
                    col2_style = level_1_col2_style
                elif level == 2:
                    style = level_2_style
                    col1_style = level_2_col1_total_style if is_total_line else level_2_col1_style
                    col2_style = level_2_col2_style
                elif level and level >= 3:
                    style = default_style
                    col2_style = style
                    level_col1_styles = col1_styles.get(level)
                    if not level_col1_styles:
                        level_col1_styles = col1_styles[level] = {
                            'default': workbook.add_format(
                                {'font_name': 'Arial', 'font_size': 12,
                                 'font_color': '#666666', 'indent': level}
                            ),
                            'total': workbook.add_format(
                                {
                                    'font_name': 'Arial',
                                    'bold': True,
                                    'font_size': 12,
                                    'font_color': '#666666',
                                    'indent': level - 1,
                                }
                            ),
                        }
                    col1_style = level_col1_styles[
                        'total'] if is_total_line else level_col1_styles[
                        'default']
                else:
                    style = default_style
                    col1_style = default_col1_style
                    col2_style = default_col2_style

                # write the first column, with a specific style to manage the indentation
                x_offset = original_x_offset + 1
                if lines[y]['id'] in account_lines_split_names:
                    code, name = account_lines_split_names[lines[y]['id']]
                    sheet.write(y + y_offset, 1, name, col1_style)
                    sheet.write(y + y_offset, 0, code, col2_style)
                else:
                    cell_type, cell_value = self._get_cell_type_value(lines[y])
                    if cell_type == 'date':
                        sheet.write_datetime(y + y_offset, 0, cell_value,
                                             date_default_col1_style)
                    else:
                        sheet.write(y + y_offset, 0, cell_value, col1_style)

                    if lines[y].get('parent_id') and lines[y][
                        'parent_id'] in account_lines_split_names:
                        sheet.write(y + y_offset, 1, account_lines_split_names[
                            lines[y]['parent_id']][0], col2_style)
                    elif account_lines_split_names:
                        sheet.write(y + y_offset, 1, "", col2_style)

                # write all the remaining cells
                columns = lines[y]['columns']
                if options[
                    'show_growth_comparison'] and 'growth_comparison_data' in \
                        lines[y]:
                    columns += [lines[y].get('growth_comparison_data')]
                for x, column in enumerate(columns, start=x_offset):
                    cell_type, cell_value = self._get_cell_type_value(column)
                    if cell_type == 'date':
                        sheet.write_datetime(y + y_offset,
                                             x + lines[y].get('colspan', 1) - 1,
                                             cell_value, date_default_style)
                    else:
                        sheet.write(y + y_offset,
                                    x + lines[y].get('colspan', 1) - 1,
                                    cell_value, style)
        else:
            super()._inject_report_into_xlsx_sheet(options, workbook, sheet)

        
        
        
        
        
        
