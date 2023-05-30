from odoo import models, api, _, fields
import json
from odoo.tools import date_utils
import io
import xlsxwriter


class TascBudgetAnalysis(models.Model):
    _name = 'tasc.budget.analysis'

    budget_line_json = fields.Char()

    def _get_templates(self):
        return {
            'main_template': 'tasc_budget_analysis_report.tasc_budget_analysis_html_content_view',
            'main_table_header_template': 'account_reports.main_table_header',
            'line_template': 'cash_flow_statement_report.line_template_cash_flow',
            'footnotes_template': 'account_reports.footnotes_template',
            'budget_analysis_search_view': 'tasc_budget_analysis_report.tasc_budget_analysis_search_view',
        }

    @api.model
    def get_budgets(self, filter, options):
        if filter:
            options.update({
                'budget_filter': filter['budget_filter'],
                'budget_name': filter['budget_name'],
            })
        else:
            options.update({
                'budget_filter': '',
                'budget_name': '',
            })
        self.env.cr.execute('''select
        budget.id, budget.name
        from crossovered_budget as budget where budget.company_id = %(company_id)s''',
                            {'company_id': self.env.company.id})
        return self.env.cr.dictfetchall()

    @api.model
    def get_button_budget_analysis(self):
        return [
            {'name': _('Export (XLSX)'), 'sequence': 2,
             'action': 'print_xlsx_budget_analysis',
             'file_export_type': _('XLSX')},
        ]

    def get_cash_flow_information(self, filter):
        options = self.env['cash.flow.statement']._get_cashflow_options(filter)
        budgets = self.get_budgets(filter, options)
        info = {
            'options': options,
            'main_html': self.get_html_content(options),
            'searchview_html': self.env['ir.ui.view']._render_template(
                self._get_templates().get('budget_analysis_search_view', ),
                values={'options': options, 'budgets': budgets}),
            'buttons': self.get_button_budget_analysis()
        }
        return info

    @api.model
    def get_budget_header(self):
        return ['Account (Budget Position)', 'Budget', 'Cost Center', 'Project',
                'Start Date', 'End Date', 'Planned Amount',
                'Consumed', 'Remaining Amount', 'Consumed Percentage']

    def get_html_content(self, options):
        templates = self._get_templates()
        template = templates['main_template']
        values = {'model': self}
        lines = self.get_budget_lines(options)
        header = self.get_budget_header()
        budget_analysis_obj = self.sudo().search([])
        if not budget_analysis_obj:
            self.env['tasc.budget.analysis'].sudo().create({
                'budget_line_json': json.dumps(lines, default=str)
            })
        else:
            budget_analysis_obj.budget_line_json = json.dumps(lines, default=str)
        values['lines'] = {'lines': lines, 'header': header,
                           'currency_symbol': self.env.company.currency_id.symbol}
        html = self.env.ref(template)._render(values)
        return html

    @api.model
    def get_cross_overed_budget_lines(self, options):
        query = '''select budget_lines.id, budget_lines.general_budget_id, 
                 analytic_account.name as analytic, project_site.name as project_site, 
                 budget_lines.date_from, budget_lines.date_to,
                 budget_lines.planned_amount, 
                 budget_lines.practical_demo as practical_demo, 
                 budget_id1.name as budget
                 from crossovered_budget_lines as budget_lines
                 left join account_analytic_account as analytic_account on 
                 budget_lines.analytic_account_id = analytic_account.id
                 left join account_analytic_account as project_site on 
                 budget_lines.project_site_id = project_site.id
                 left join res_company as company on 
                 budget_lines.company_id = company.id
                 left join crossovered_budget as budget_id1 on budget_lines.crossovered_budget_id = budget_id1.id
                 where budget_lines.date_from >= %(from_date)s 
                 and budget_lines.date_to <= %(date_to)s and budget_lines.company_id = %(company_id)s'''
        if options['budget_filter'] != '':
            self.env.cr.execute(
                query + '''and budget_lines.crossovered_budget_id = %(budget_id)s''',
                {'from_date': options['date']['date_from'],
                 'date_to': options['date']['date_to'],
                 'budget_id': options['budget_filter'],
                 'company_id': self.env.company.id})
        else:
            self.env.cr.execute(query,
                                {'from_date': options['date']['date_from'],
                                 'date_to': options['date']['date_to'],
                                 'company_id': self.env.company.id})
        cross_overed_budget_lines = self.env.cr.dictfetchall()
        for lines in cross_overed_budget_lines:
            percent = 0
            obj = self.env['crossovered.budget.lines'].browse(int(lines['id']))
            if obj.practical_amount != 0 and lines['planned_amount'] != 0:
                percent = round(-1 * ((obj.practical_amount / lines[
                    'planned_amount']) * 100))
            lines.update({
                'practical_amount': obj.practical_amount,
                'remaining_amount': obj.remaining_amount,
                'percentage':  percent,
            })
        return cross_overed_budget_lines

    @api.model
    def get_budgetary_position(self):
        self.env.cr.execute("""select bdg_position.id, bdg_position.name from 
        account_budget_post as bdg_position where bdg_position.company_id = %(company_id)s""",
                            {'company_id': self.env.company.id})
        return self.env.cr.dictfetchall()

    @api.model
    def get_budget_lines(self, options):
        """Used to get the budget lines"""
        cross_overed_budget = self.get_cross_overed_budget_lines(options)
        budgetory_position = self.get_budgetary_position()
        for position in budgetory_position:
            filtered_data = list(
                filter(lambda x: x['general_budget_id'] == position['id'],
                       cross_overed_budget))
            position.update({
                'planned_amount': sum(
                    list(map(lambda x: x['planned_amount'], filtered_data))),
                'practical_amount': sum(
                    list(map(lambda x: x['practical_amount'], filtered_data))),
                'remaining_amount': sum(list(
                    map(lambda x: x['remaining_amount'], filtered_data))),
                'percentage': sum(
                    list(map(lambda x: x['percentage'], filtered_data))),
                'lines': filtered_data
            })
        filtered_none = list(
            filter(lambda x: x['general_budget_id'] is None,
                   cross_overed_budget))
        if budgetory_position:
            budgetory_position.append({
                'id': 0,
                'name': 'Undefined',
                'planned_amount': sum(
                    list(map(lambda x: x['planned_amount'], filtered_none))),
                'practical_amount': sum(
                    list(map(lambda x: x['practical_amount'], filtered_none))),
                'remaining_amount': sum(
                    list(
                        map(lambda x: x['remaining_amount'], filtered_none))),
                'percentage': sum(
                    list(map(lambda x: x['percentage'], filtered_none))),
                'lines': filtered_none
            })
            report_date = budgetory_position
            return report_date
        else:
            report_date = [{
                'id': 0,
                'name': 'Undefined',
                'planned_amount': sum(
                    list(map(lambda x: x['planned_amount'], filtered_none))),
                'practical_amount': sum(
                    list(map(lambda x: x['practical_amount'], filtered_none))),
                'remaining_amount': sum(
                    list(
                        map(lambda x: x['remaining_amount'], filtered_none))),
                'percentage': sum(
                    list(map(lambda x: x['percentage'], filtered_none))),
                'lines': filtered_none
            }]
            return report_date

    def print_xlsx_budget_analysis(self, options, params):
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
        date_filter_name = self.env['cash.flow.statement'].get_cash_flow_header(
            options)
        budget_analysis_obj = self.sudo().search([])
        lines = json.loads(budget_analysis_obj.budget_line_json)
        headers = self.get_budget_header()
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet()
        sheet.set_row(4, 20)
        sheet.set_column('B5:M5', 30)
        main_head = workbook.add_format(
            {'font_size': 13, 'align': 'center', 'border': 1,
             'bg_color': '#fcd15b'})
        sub_head = workbook.add_format(
            {'font_size': 12, 'align': 'center', 'border': 1,
             'bg_color': '#5db5fc'})
        sub_line_style = workbook.add_format(
            {'font_size': 12})
        date_format = workbook.add_format(
            {'num_format': 'yyyy/mm/dd', 'align': 'center'})
        sheet.write('G3', date_filter_name['name'], main_head)
        sheet.write('I3', options['budget_name'], main_head)
        row_head = 4
        col_head = 1
        for header in headers:
            sheet.write(row_head, col_head, header, sub_head)
            col_head += 1
        row_line = 5
        for bd_line in lines:
            if bd_line['lines']:
                for sub_line in bd_line['lines']:
                    col_line = 1
                    sheet.write(row_line, col_line, bd_line['name'],
                                sub_line_style)
                    col_line += 1
                    sheet.write(row_line, col_line, sub_line['budget'],
                                sub_line_style)
                    col_line += 1
                    sheet.write(row_line, col_line, sub_line['analytic'],
                                sub_line_style)
                    col_line += 1
                    sheet.write(row_line, col_line, sub_line['project_site'],
                                sub_line_style)
                    col_line += 1
                    sheet.write(row_line, col_line, sub_line['date_from'],
                                date_format)
                    col_line += 1
                    sheet.write(row_line, col_line, sub_line['date_to'],
                                date_format)
                    col_line += 1
                    sheet.write(row_line, col_line, '{:20,.2f}'.format(round(sub_line['planned_amount'], 2)),
                                sub_line_style)
                    col_line += 1
                    sheet.write(row_line, col_line, '{:20,.2f}'.format(sub_line['practical_amount']),
                                sub_line_style)
                    col_line += 1
                    sheet.write(row_line, col_line, '{:20,.2f}'.format(sub_line['remaining_amount']),
                                sub_line_style)
                    col_line += 1
                    sheet.write(row_line, col_line, str(round(sub_line['percentage']))+'%',
                                sub_line_style)
                    col_line += 1
                    row_line += 1
        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()
