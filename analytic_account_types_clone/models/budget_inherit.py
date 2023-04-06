from odoo.addons.analytic_account_types.models.budget import CrossOveredBudgetLines


def _compute_practical_amount(self):
    lines = self.env['crossovered.budget.lines'].search(
        [('crossovered_budget_id', '=',
          self.mapped('crossovered_budget_id').id)])
    analytic_line_ids = []
    for line in lines:
        analytic_accounts = self.filtered(lambda
                                              x: x.general_budget_id.id == line.general_budget_id.id).mapped(
            'analytic_account_id').ids
        project_site_ids = self.filtered(lambda
                                             x: x.general_budget_id.id == line.general_budget_id.id).mapped(
            'project_site_id').ids
        acc_ids = line.general_budget_id.account_ids.ids
        date_to = line.date_to
        date_from = line.date_from
        if acc_ids and line.analytic_account_id and line.project_site_id:
            analytic_line_obj = self.env['account.analytic.line']
            domain = [('id', 'not in', analytic_line_ids),
                      ('account_id', '=', line.analytic_account_id.id),
                      ('date', '>=', date_from),
                      ('date', '<=', date_to),
                      ('project_site_id', '=', line.project_site_id.id),
                      ('general_account_id', 'in', acc_ids)]
            where_query = analytic_line_obj._where_calc(domain)
            analytic_line_obj._apply_ir_rules(where_query, 'read')
            from_clause, where_clause, where_clause_params = where_query.get_sql()
            select = "SELECT id , amount from " + from_clause + " where " + where_clause
            self.env.cr.execute(select, where_clause_params)
            fetched_dict = self.env.cr.dictfetchall()
            if fetched_dict:
                total = sum(list(map(lambda x: x['amount'], fetched_dict)))
                analytic_line_ids += list(
                    map(lambda x: x['id'], fetched_dict))
                line.practical_amount = total if total else 0
            else:
                line.practical_amount = 0
        elif acc_ids and line.analytic_account_id:
            analytic_line_obj = self.env['account.analytic.line']
            domain = [('id', 'not in', analytic_line_ids),
                      ('account_id', '=', line.analytic_account_id.id),
                      ('date', '>=', date_from),
                      ('date', '<=', date_to),
                      ('general_account_id', 'in', acc_ids)]
            where_query = analytic_line_obj._where_calc(domain)
            analytic_line_obj._apply_ir_rules(where_query, 'read')
            from_clause, where_clause, where_clause_params = where_query.get_sql()
            select = "SELECT id ,amount from " + from_clause + " where " + where_clause
            self.env.cr.execute(select, where_clause_params)
            fetched_dict = self.env.cr.dictfetchall()
            if fetched_dict:
                total = sum(list(map(lambda x: x['amount'], fetched_dict)))
                analytic_line_ids += list(
                    map(lambda x: x['id'], fetched_dict))
                line.practical_amount = total if total else 0
            else:
                line.practical_amount = 0
        elif acc_ids and line.project_site_id:
            analytic_line_obj = self.env['account.analytic.line']
            domain = [('id', 'not in', analytic_line_ids),
                      ('date', '>=', date_from),
                      ('date', '<=', date_to),
                      ('general_account_id', 'in', acc_ids),
                      ('project_site_id', '=', line.project_site_id.id)]
            where_query = analytic_line_obj._where_calc(domain)
            analytic_line_obj._apply_ir_rules(where_query, 'read')
            from_clause, where_clause, where_clause_params = where_query.get_sql()
            select = "SELECT id, amount from " + from_clause + " where " + where_clause
            self.env.cr.execute(select, where_clause_params)
            fetched_dict = self.env.cr.dictfetchall()
            if fetched_dict:
                total = sum(list(map(lambda x: x['amount'], fetched_dict)))
                analytic_line_ids += list(
                    map(lambda x: x['id'], fetched_dict))
                line.practical_amount = total if total else 0
            else:
                line.practical_amount = 0
        else:
            analytic_line_obj = self.env['account.analytic.line']
            domain = [('id', 'not in', analytic_line_ids),
                      ('account_id', 'not in', analytic_accounts),
                      ('date', '>=', date_from),
                      ('date', '<=', date_to),
                      ('project_site_id', 'not in', project_site_ids),
                      ('general_account_id', 'in', acc_ids)]
            where_query = analytic_line_obj._where_calc(domain)
            analytic_line_obj._apply_ir_rules(where_query, 'read')
            from_clause, where_clause, where_clause_params = where_query.get_sql()
            select = "SELECT id , amount from " + from_clause + " where " + where_clause
            self.env.cr.execute(select, where_clause_params)
            fetched_dict = self.env.cr.dictfetchall()
            if fetched_dict:
                total = sum(list(map(lambda x: x['amount'], fetched_dict)))
                analytic_line_ids += list(
                    map(lambda x: x['id'], fetched_dict))
                line.practical_amount = total if total else 0
            else:
                line.practical_amount = 0
        line.practical_demo = line.practical_amount


CrossOveredBudgetLines._compute_practical_amount = _compute_practical_amount