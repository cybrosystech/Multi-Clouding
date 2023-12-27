from odoo import models, fields, api
from odoo.tools.safe_eval import json
from odoo.tools import date_utils, io, xlsxwriter


class ConsolidationReportWizard(models.Model):
    _name = 'wizard.consolidation.report'

    report_type = fields.Selection(selection=[('profit_loss', 'Profit And Loss')
        , ('balance_sheet', 'Balance Sheet'), ], required=True)
    consolidation_id = fields.Many2one('consolidation.chart', required=True)
    consolidation_period_id = fields.Many2one('consolidation.period', )
    consolidation_config_id = fields.Many2one('consolidation.report.config')

    def _get_account_values(self, accounts, consolidation, heading,
                            consolidation_period):
        if accounts:
            sql = '''select (CASE 
                     WHEN journal_line.journal_id = journal_line.journal_id THEN sum(journal_line.amount)
                     ELSE 0
                     END), journal_line.journal_id, group1.name, group2.name as parent_group from consolidation_journal_line as journal_line
                     left join consolidation_journal as journal on journal_line.journal_id = journal.id
                     left join consolidation_group as group1 on journal_line.group_id = group1.id
                     left join consolidation_group as group2 on group1.parent_id = group2.id
                     where journal_line.account_id in %(accounts)s and journal.chart_id = %(consolidation)s
                     and journal.period_id = %(consolidation_period)s
                     GROUP BY journal_line.journal_id, group1.name, journal.name, group2.name'''
            self.env.cr.execute(sql, {'accounts': tuple(accounts),
                                      'consolidation': consolidation.id,
                                      'consolidation_period': consolidation_period.id})
            results = self.env.cr.dictfetchall()
            return results
        else:
            sql = '''select journal_line.journal_id, group1.name, group2.name as parent_group from consolidation_journal_line as journal_line
                 left join consolidation_journal as journal on journal_line.journal_id = journal.id
                 left join consolidation_group as group1 on group1.id = %(group)s
                 left join consolidation_group as group2 on group1.parent_id = group2.id
                 where  journal.chart_id = %(consolidation)s and journal.period_id = %(consolidation_period)s
                 GROUP BY journal_line.journal_id, group1.name, journal.name, group2.name'''
            self.env.cr.execute(sql, {'group': heading.id,
                                      'consolidation': consolidation.id,
                                      'consolidation_period': consolidation_period.id})
            results = self.env.cr.dictfetchall()
            for rec in results:
                rec.update({'case': 0})
            return results

    def generate_total_lines(self, test, period, parent_name, total_list,
                             main_list):
        for journals in period.mapped('journal_ids').ids:
            total = 0
            filtered_data = list(
                filter(lambda x: x['journal_id'] == journals, test))
            for data in filtered_data:
                total += data['case']
            test.append({
                'name': 'Total ' + parent_name,
                'journal_id': journals,
                'case': total,
                'format': {'valign': 'vcenter',
                           'font_color': 'black', 'border': 2}
            })
            total_list.append({
                'name': 'Total ' + parent_name,
                'journal_id': journals,
                'case': total,
                'format': {'valign': 'vcenter',
                           'font_color': 'black', 'border': 2}
            })
            main_list.append({
                'name': 'Total ' + parent_name,
                'journal_id': journals,
                'case': total,
                'format': {'valign': 'vcenter',
                           'font_color': 'black', 'border': 2}
            })

    def _total_config_lines_generate(self, consolidation_conf, period,
                                     total_list, main_list):
        test_ab = []
        for journals in period.mapped('journal_ids').ids:
            total = 0
            for group in consolidation_conf.consolidation_parent:
                filtered_data = list(
                    filter(lambda x: x['journal_id'] == journals and x[
                        'name'] == 'Total ' + group.name, total_list))
                if filtered_data:
                    total += filtered_data[0]['case']
            test_ab.append({'name': consolidation_conf.config_name,
                            'journal_id': journals,
                            'case': total,
                            'format': {'valign': 'vcenter',
                                       'font_color': 'black', 'border': 2}})
            main_list.append({'name': consolidation_conf.config_name,
                              'journal_id': journals,
                              'case': total,
                              'format': {'valign': 'vcenter',
                                         'font_color': 'black', 'border': 2}})
        return test_ab

    @api.onchange('report_type')
    def onchange_report_type(self):
        """Updating the report config field based on change of report type"""
        if self.report_type:
            self.consolidation_config_id = self.env[
                'consolidation.report.config'].search([
                ('config_type', '=', self.report_type),
                ('active_bool', '=', True)]).id

    def generate_xlsx_report(self):
        demo_list = []
        group_name = []
        total_list = []
        main_list = []
        for parent_group in self.consolidation_config_id.profit_loss_related_ids:
            test = []
            if parent_group.line_type == 'main_lines':
                group_name.append(
                    {'name': parent_group.consolidation_parent_group_id.name,
                     'format': {'valign': 'vcenter',
                                'font_color': 'black',
                                'bold': True,
                                },
                     'formatting': 2,
                     'multiply_factor': parent_group.multiply_factor,
                     'not_show_on_report': parent_group.not_show_on_report, })
                for child in parent_group.consolidation_child_group_ids:
                    group_name.append({'name': child.name,
                                       'format': {'valign': 'vcenter',
                                                  'font_color': 'black'},
                                       'formatting': 1,
                                       'multiply_factor': parent_group.multiply_factor,
                                       'not_show_on_report': parent_group.not_show_on_report,
                                       })
                    sql_accounts = '''select account.id from consolidation_group as group1
                                              inner join consolidation_account as account on group1.id = account.group_id
                                              where group1.id = %(name)s'''
                    self.env.cr.execute(sql_accounts, {'name': child.id})
                    results = self.env.cr.fetchall()
                    dictionary = self._get_account_values(results,
                                                          self.consolidation_id
                                                          , child,
                                                          self.consolidation_period_id)
                    for dict in dictionary:
                        dict.update({'format': {'align': 'center',
                                                'font_color': 'black',
                                                }})
                        test.append(dict)
                        main_list.append(dict)
                if parent_group.consolidation_parent_group_id.name == 'Equity':
                    print("sql_accounts",sql_accounts)

                    pass
                else:
                    self.generate_total_lines(test,
                                              self.consolidation_period_id,
                                              parent_group.consolidation_parent_group_id.name,
                                              total_list, main_list)
                    demo_list.append(test)
                    group_name.append({
                        'name': 'Total ' + parent_group.consolidation_parent_group_id.name,
                        'format': {'valign': 'vcenter',
                                   'font_color': 'black',
                                   'bold': True},
                        'formatting': 1,
                        'multiply_factor': parent_group.multiply_factor,
                        'not_show_on_report': parent_group.not_show_on_report,
                    })
            else:
                group_name.append({
                    'name': parent_group.config_name,
                    'format': {'valign': 'vcenter',
                               'font_color': 'black',
                               'bold': True,
                               },
                    'formatting': 2,
                    'multiply_factor': parent_group.multiply_factor,
                    'not_show_on_report': parent_group.not_show_on_report,
                })
                total_config = self._total_config_lines_generate(parent_group,
                                                                 self.consolidation_period_id,
                                                                 total_list,
                                                                 main_list)
                demo_list.append(total_config)

        data = {
            'ids': self.ids,
            'state': self.report_type,
            'consolidation_id': self.consolidation_id.id,
            'consolidation_period': self.consolidation_period_id.id,
            'demo_list': demo_list,
            'group_name': group_name,
            'main_list': main_list
        }
        return {
            'type': 'ir.actions.report',
            'data': {'model': 'wizard.consolidation.report',
                     'options': json.dumps(data,
                                           default=date_utils.json_default),
                     'output_format': 'xlsx',
                     'report_name': 'Consolidation Report' + str(
                         self.report_type),
                     },
            'report_type': 'xlsx'
        }

    def get_xlsx(self, data, response):
        consolidation_period_journal = self.env['consolidation.period'].search([
            ('id', '=', data['consolidation_period'])])
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet()
        head = workbook.add_format(
            {'font_size': 13, 'align': 'center', 'valign': 'vcenter',
             'bg_color': '#1a1c99',
             'font_color': '#f2f7f4', 'border': 2})
        sub_heading = workbook.add_format(
            {'valign': 'vcenter',
             'font_color': 'black',
             })
        sheet.set_column('B3:B3', 15)
        row = 2
        col = 1
        journal_ids = []
        for journal in consolidation_period_journal.journal_ids:
            sheet.set_column(row, col, 25)
            sheet.write(row, col, journal.name, head)
            journal_ids.append({'id': journal.id, 'col': col})
            col += 1
        sheet.write(row, len(journal_ids) + 1, 'Total Company', head)
        for head in data['group_name']:
            total_comp = 0
            col = 0
            if not head['not_show_on_report']:
                row += head['formatting']
                head_format = workbook.add_format(head['format'])
                sheet.set_column(row, col, 20)
                sheet.write(row, col, head['name'], head_format)
            else:
                pass
            for demo in data['demo_list']:
                list_data = list(
                    filter(lambda x: x['name'] == head['name'], demo))
                if list_data:
                    for rec in list_data:
                        filter_demo = list(
                            filter(lambda x: x['id'] == rec['journal_id'],
                                   journal_ids))
                        dynamic_format = workbook.add_format(rec['format'])
                        if not head['not_show_on_report']:
                            if head['multiply_factor'] != 0:
                                sheet.write(row, filter_demo[0]['col'],
                                            head['multiply_factor'] * rec[
                                                'case'],
                                            dynamic_format)
                            else:
                                sheet.write(row, filter_demo[0]['col'],
                                            rec['case'],
                                            dynamic_format)
                        else:
                            pass

            final_comp_list = list(
                filter(lambda x: x['name'] == head['name'], data['main_list']))
            if final_comp_list:
                for cmp_list in final_comp_list:
                    total_comp += cmp_list['case']
                if not head['not_show_on_report']:
                    company_heading = workbook.add_format(
                        {'valign': 'vcenter',
                         'font_color': 'black',
                         'border': 2})
                    if head['multiply_factor'] != 0:
                        if (head["name"] and 'Total' in head["name"]) or head[
                            "name"] == False:
                            sheet.write(row, len(journal_ids) + 1,
                                        head['multiply_factor'] * total_comp,
                                        company_heading)
                        else:
                            line_format = workbook.add_format(
                                {'valign': 'vcenter',
                                 'font_color': 'black',
                                 })
                            if 'Current Profit' in head['name']:
                                sheet.write(row, len(journal_ids) + 1,
                                            head[
                                                'multiply_factor'] * total_comp,
                                            line_format)
                            else:
                                sheet.write(row, len(journal_ids) + 1,
                                            head[
                                                'multiply_factor'] * total_comp,
                                            sub_heading)

                    else:
                        if (head["name"] and 'Total' in head["name"]) or head[
                            "name"] == False:
                            sheet.write(row, len(journal_ids) + 1, total_comp,
                                        company_heading)
                        else:
                            if 'Current Profit' in head['name']:
                                line_format = workbook.add_format(
                                    {'valign': 'vcenter',
                                     'font_color': 'black',
                                     })
                                sheet.write(row, len(journal_ids) + 1,
                                            head[
                                                'multiply_factor'] * total_comp,
                                            line_format)
                            else:
                                sheet.write(row, len(journal_ids) + 1,
                                            total_comp,
                                            sub_heading)
                else:
                    pass
        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()
