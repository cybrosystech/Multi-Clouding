# -*- coding: utf-8 -*-

from odoo import _,api, fields, models
from odoo.exceptions import UserError


class CipAccountAsset(models.Model):
    """Model for cip account asset"""
    _name = 'cip.account.asset'
    _description = 'CIP Account Asset'


    name = fields.Char(copy=False)
    site_status = fields.Selection(
        [('on_air', 'ON AIR'), ('off_air', 'OFF AIR'), ])
    t_budget = fields.Selection(
        [('capex', 'CAPEX'), ('opex', 'OPEX'), ],
        string='T.Budget')
    company_id = fields.Many2one('res.company',default=lambda self: self.env.company)
    cip_line_ids = fields.One2many('cip.account.move.line','cip_account_asset_id',copy=False)
    cip_asset_journal_entry_id = fields.Many2one('account.move',copy=False)
    project_site_id = fields.Many2one('account.analytic.account',
                                      domain=[('analytic_account_type', '=',
                                               'project_site')], )
    account_id = fields.Many2one('account.account')


    def button_action_create_entry(self):
        """Method for creating cip asset journal entry"""
        invoice_lines = []
        journal_id = self.env['account.journal'].search(
            [('name', '=ilike', 'Assets'), ('company_id', '=', self.company_id.id),
             ('type', '=', 'general')], limit=1)
        if not journal_id:
            raise UserError("No Journal with name Assets.")

        for rec in self.cip_line_ids:
            invoice_lines.append((0, 0, {
                'quantity': rec.quantity,
                'analytic_account_id': rec.analytic_account_id.id,
                'project_site_id': rec.project_site_id.id,
                'account_id': rec.cip_account_id.id,
                'debit': rec.amount ,
                'credit': 0,
                'product_uom_id': rec.product_id.uom_id.id,
            }))
            invoice_lines.append((0, 0, {
                'quantity': rec.quantity,
                'name': rec.product_id.name +" - "+self.name,
                'analytic_account_id': rec.analytic_account_id.id,
                'project_site_id': rec.project_site_id.id,
                'account_id': rec.asset_account_id.id,
                'debit': 0,
                'credit': rec.amount,
                'product_uom_id': rec.product_id.uom_id.id,
            }))

        invoice = self.env['account.move'].create({
            'move_type': 'entry',
            'ref': self.name,
            'currency_id': self.company_id.currency_id.id,
            'line_ids': invoice_lines,
            'date': fields.Date.today(),
            'journal_id': journal_id.id,
        })
        self.cip_asset_journal_entry_id = invoice.id
        invoice.with_context(cip_asset=True).action_post()
        action = {
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": 'account.move',
            "res_id": invoice.id,
            "target": 'current'
        }
        return action


    def action_generate_lines(self):
        """Method for generate cip asset lines"""
        if self.cip_line_ids:
            self.cip_line_ids = [(5, 0, 0)]

        domain = [('journal_id.name', '=', 'Inventory Valuation'),
                  ('account_id.name', 'ilike', 'CIP'),
                  ('company_id', '=', self.company_id.id),
                  ('cip_account_move_line_id', '=', False)]

        if self.project_site_id:
            domain.append(('project_site_id','=',self.project_site_id.id))
        if self.account_id:
            domain.append(('account_id', '=', self.account_id.id))
        if self.t_budget:
            domain.append(('t_budget', '=', self.t_budget))
        if self.site_status:
            domain.append(('site_status', '=', self.site_status))

        items = self.env['account.move.line'].search(domain)
        if not items:
            raise UserError("No data to show.")

        for item in items:
            cip_line_id = self.env['cip.account.move.line'].create({
                'cip_account_asset_id': self.id,
                'product_id': item.product_id.id,
                'quantity': abs(item.quantity),
                'amount': item.credit if item.credit else item.debit,
                'analytic_account_id': item.analytic_account_id.id,
                'project_site_id': item.project_site_id.id,
                'site_status': item.site_status,
                't_budget': item.t_budget,
                'cip_account_id': item.account_id.id,
                'asset_account_id': item.product_id.asset_account_id.id,
            })
            item.cip_account_move_line_id = cip_line_id.id


    def view_cip_asset_entry(self):
        """method to view cip asset entry"""
        action = {
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": 'account.move',
            "res_id": self.cip_asset_journal_entry_id.id,
            "target": 'current'
        }
        return action