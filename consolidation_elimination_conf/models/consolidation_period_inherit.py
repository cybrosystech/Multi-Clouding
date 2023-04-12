from odoo import models, api


class ConsolidationPeriodElimination(models.Model):
    _inherit = 'consolidation.period'

    def action_generate_elimination_journal(self):
        eliminated_journal = self.env['consolidation.journal'].search([(
            'name', '=', 'Elimination '+self.name),
            ('chart_id', '=', self.chart_id.id)])
        print('eliminated_journal', eliminated_journal)
        if not eliminated_journal:
            eliminated_journal = self.env['consolidation.journal'].create({
                'name': 'Elimination '+self.name,
                'period_id': self.id,
                'chart_id': self.chart_id.id
            })
        eliminated_journal.line_ids.with_context(allow_unlink=True).unlink()
        self.get_consolidation_journal_lines(eliminated_journal)

    def get_consolidation_journal_lines(self, eliminated_journal):
        test = []
        for company_period in self.company_period_ids:
            companies = self.company_period_ids.mapped('company_id').ids
            companies.remove(company_period.company_id.id)
            for elimination_conf in self.env['elimination.journal.conf'].search(
                    [('consolidation_period_id', '=', self.id)],
                    limit=1).elimination_lines:
                if elimination_conf.report_type not in ['share', 'invest']:
                    domain = ''
                    if elimination_conf.report_type == 'bl':
                        domain = ('date', '<=', company_period.date_company_end)
                    for account in elimination_conf.consolidation_account_ids:
                        if domain:
                            abc = self.env['account.move'].search(
                                [('line_ids.account_id',
                                  'in', account.mapped(
                                    'account_ids').ids), ('company_id', '=',
                                                          company_period.company_id.id),
                                 domain]).mapped(
                                'line_ids').filtered(
                                lambda x: x.account_id.id in account.mapped(
                                    'account_ids').ids)
                        else:
                            abc = self.env['account.move'].search(
                                [('line_ids.account_id',
                                  'in', account.mapped(
                                    'account_ids').ids), ('company_id', '=',
                                                          company_period.company_id.id),
                                 ('date', '>=',
                                  company_period.date_company_begin),
                                 ('date', '<=',
                                  company_period.date_company_end)]).mapped(
                                'line_ids').filtered(
                                lambda x: x.account_id.id in account.mapped(
                                    'account_ids').ids)
                        currency_amount = sum(abc.mapped('debit')) + (
                            -sum(abc.mapped('credit')))
                        amount = company_period._apply_rates(
                            currency_amount, account)
                        if test:
                            filtered_data = list(
                                filter(
                                    lambda x: x['name'] == account.name,
                                    test))
                            if filtered_data:
                                filtered_data[0].update({
                                    'amount': filtered_data[0]['amount'] + amount
                                })
                            else:
                                test.append({
                                    'name': account.name,
                                    'account_id': account.id,
                                    'amount': amount
                                })
                        else:
                            test.append({
                                'name': account.name,
                                'account_id': account.id,
                                'amount': amount
                            })
        for elimination_conf1 in self.env['elimination.journal.conf'].search(
                [('consolidation_period_id', '=', self.id)],
                limit=1).elimination_lines:

            if elimination_conf1.report_type in ['share', 'invest']:
                if elimination_conf1.report_type == 'share':
                    for account in elimination_conf1.consolidation_account_ids:
                        total_amount = 0
                        abc = self.env['account.move.line'].search(
                            [('account_id',
                              'in', account.mapped(
                                'account_ids').ids), ('company_id', '=',
                                                      elimination_conf1.consolidation_period_line.company_id.id),
                             ('date', '<=',
                              elimination_conf1.consolidation_period_line.date_company_end)])
                        for move_line in abc:
                            total_amount += elimination_conf1.consolidation_period_line._apply_historical_rates(
                                move_line)
                        if test:
                            filtered_data = list(
                                filter(
                                    lambda x: x['name'] == account.name,
                                    test))
                            if filtered_data:
                                filtered_data[0].update({
                                    'amount': filtered_data[0][
                                                  'amount'] + total_amount
                                })
                            else:
                                test.append({
                                    'name': account.name,
                                    'account_id': account.id,
                                    'amount': total_amount
                                })
                        else:
                            test.append({
                                'name': account.name,
                                'account_id': account.id,
                                'amount': total_amount
                            })
                else:
                    for account in elimination_conf1.consolidation_account_ids:
                        move_lines = self.env['account.move.line'].search(
                            [('account_id',
                              'in', account.mapped(
                                'account_ids').ids), ('company_id', '=',
                                                      elimination_conf1.consolidation_period_line.company_id.id),
                             ('date', '<=',
                              elimination_conf1.consolidation_period_line.date_company_end)])
                        currency_amount = sum(move_lines.mapped('debit')) + (
                            -sum(move_lines.mapped('credit')))
                        amount = elimination_conf1.consolidation_period_line._apply_rates(
                            currency_amount, account)
                        if test:
                            filtered_data = list(
                                filter(
                                    lambda x: x['name'] == account.name,
                                    test))
                            if filtered_data:
                                filtered_data[0].update({
                                    'amount': filtered_data[0][
                                                  'amount'] + amount
                                })
                            else:
                                test.append({
                                    'name': account.name,
                                    'account_id': account.id,
                                    'amount': amount
                                })
                        else:
                            test.append({
                                'name': account.name,
                                'account_id': account.id,
                                'amount': amount
                            })
        for lines in test:
            self.env['consolidation.journal.line'].create({
                'account_id': lines['account_id'],
                'amount': -1 * (lines['amount']),
                'journal_id': eliminated_journal.id
            })
