from odoo import models, fields


class ExpenseJournal(models.Model):
    _name = 'expense.journal'

    journal_id = fields.Many2one('account.journal', string="Journal",domain="['|',('company_id','=',company_id),('company_id','=',False)]")
    company_id = fields.Many2one('res.company', string="Company")
