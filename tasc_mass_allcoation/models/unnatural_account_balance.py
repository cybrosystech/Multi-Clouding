from copyreg import constructor

from odoo import api, models, fields, _
from odoo.tools import float_compare
from odoo.exceptions import ValidationError, UserError
from dateutil.relativedelta import relativedelta


class UnnaturalAccountBalance(models.Model):
    _name = 'unnatural.account.balance'
    _description = 'Unnatural Account Balance'

    name = fields.Char(
        string='Name',
        required=1
    )
    date_period = fields.Date(string="Date", required=1)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)
    asset = fields.Boolean(string="Assets")
    liability = fields.Boolean(string="Liability")
    equity = fields.Boolean(string="Equity")
    unnatural_account_balance_line_ids = fields.One2many(
        comodel_name="unnatural.account.balance.line",
        inverse_name="unnatural_account_balance_id",
        string="",
        required=False, copy=False)
    unnatural_balance_move_id = fields.Many2one('account.move', string="Unnatural account balance Entry", copy=False)
    reversed_unnatural_balance_move_id = fields.Many2one('account.move', string="Reversed Unnatural account balance Entry", copy=False)


    def action_generate_unnatural_balance_lines(self):
        if self.unnatural_account_balance_line_ids:
            self.unnatural_account_balance_line_ids = [(5, 0, 0)]

        end_date = self.date_period + relativedelta(day=31)
        internal_groups = []
        if self.asset:
            internal_groups.append('asset')
        if self.liability:
            internal_groups.append('liability')

        query = """
            SELECT
                aml.account_id,
                SUM(aml.balance) AS balance
            FROM
                account_move_line aml
            JOIN
                account_account aa ON aml.account_id = aa.id
            WHERE
                aml.company_id = %s
                AND aml.parent_state != 'cancel'
                AND aml.date <= %s
                AND aa.account_type not in ('asset_fixed', 'asset_cash', 'asset_non_current')
                AND aa.internal_group IN %s
            GROUP BY
                aml.account_id, aa.internal_group
            HAVING
                (aa.internal_group = 'asset' AND SUM(aml.balance) < 0)
                OR
                (aa.internal_group IN ('liability') AND SUM(aml.balance) > 0)
        """
        self.env.cr.execute(query, (self.company_id.id, end_date,tuple(internal_groups)))
        res = self.env.cr.fetchall()

        if not res:
            raise UserError("No data to show.")

        cost_center = self.env['account.analytic.account'].search([('name','ilike','No Cost Center'),('company_id','=',self.company_id.id)],limit=1)
        project_site = self.env['account.analytic.account'].search([('name','ilike','No Project'),('company_id','=',self.company_id.id)],limit=1)

        for line in res:
            self.env['unnatural.account.balance.line'].create({
                'unnatural_account_balance_id': self.id,
                'account_id': line[0],
                'balance': line[1],
                'cost_center_id': cost_center.id if cost_center else False,
                'project_site_id': project_site.id if project_site else False,
            })


    def view_unnatural_account_balance_entry(self):
        action = {
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": 'account.move',
            "res_id": self.unnatural_balance_move_id.id,
            "target": 'current'
        }
        return action
    #
    def view_reversed_unnatural_account_balance_entry(self):
        action = {
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": 'account.move',
            "res_id": self.reversed_unnatural_balance_move_id.id,
            "target": 'current'
        }
        return action

    def action_generate_unnatural_entry(self):
        invoice_lines = []
        journal_id = self.env['account.journal'].search(
            [('name', '=ilike', 'Miscellaneous Operations'), ('company_id', '=', self.company_id.id),
             ('type', '=', 'general')], limit=1)
        ########################start##########################
        cost_center = self.env['account.analytic.account'].search(
            [('name', 'ilike', 'No Cost Center'), ('company_id', '=', self.company_id.id)], limit=1)
        project_site = self.env['account.analytic.account'].search(
            [('name', 'ilike', 'No Project'), ('company_id', '=', self.company_id.id)], limit=1)

        for rec in self.unnatural_account_balance_line_ids:
            invoice_lines.append((0, 0, {
                'analytic_account_id': rec.cost_center_id.id,
                'project_site_id': rec.project_site_id.id,
                'account_id': rec.account_id.id,
                'debit': abs(rec.balance) if rec.balance <0 else 0 ,
                'credit': abs(rec.balance) if rec.balance >0 else 0,
            }))
            invoice_lines.append((0, 0, {
                'analytic_account_id': cost_center.id,
                'project_site_id': project_site.id,
                'account_id': rec.counter_account_id.id,
                'debit': abs(rec.balance) if rec.balance >0 else 0,
                'credit': abs(rec.balance) if rec.balance <0 else 0,
            }))
        end_date = self.date_period + relativedelta(day=31)

        invoice = self.env['account.move'].create({
            'move_type': 'entry',
            'currency_id': self.env.company.currency_id.id,
            'ref': self.name if self.name else '',
            'line_ids': invoice_lines,
            'date': end_date,
            'journal_id': journal_id.id,
        })
        self.unnatural_balance_move_id = invoice.id
        invoice.action_post()
        reverse_move = invoice._reverse_moves(default_values_list=[{
            'ref': _("Reversal of: %s", invoice.ref),
        }])
        reverse_move.date = (end_date + relativedelta(months=1)).replace(day=1)
        reverse_move.action_post()
        self.reversed_unnatural_balance_move_id = reverse_move.id

        action = {
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": 'account.move',
            "res_id": invoice.id,
            "target": 'current'
        }
        return action


class UnnaturalAccountBalanceLine(models.Model):
    _name = 'unnatural.account.balance.line'

    unnatural_account_balance_id = fields.Many2one('unnatural.account.balance')
    balance = fields.Float(string="Balance")
    account_id = fields.Many2one('account.account', string="Account")
    counter_account_id = fields.Many2one('account.account', string="Counter Account",required=True)
    cost_center_id = fields.Many2one('account.analytic.account',string="Cost Center")
    project_site_id = fields.Many2one('account.analytic.account',string="Project Site")


