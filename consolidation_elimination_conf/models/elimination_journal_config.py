from odoo import models, fields, api
from odoo.exceptions import ValidationError


class EliminationJournalConf(models.Model):
    _name = 'elimination.journal.conf'
    _description = 'Configuration for consolidated accounts for profit/loss and' \
                   'Balance sheet'

    name = fields.Char()
    consolidation_period_id = fields.Many2one('consolidation.period', copy=False)
    elimination_lines = fields.One2many('elimination.journal.line',
                                        'elimination_journal_id', copy=True)

    @api.constrains('consolidation_period_id')
    def consolidation_period_check(self):
        elimination_conf = self.search([('consolidation_period_id', '=', self.consolidation_period_id.id)])
        if len(elimination_conf) > 1:
            raise ValidationError('Consolidation period has already configured')


class EliminationJournalLines(models.Model):
    _name = 'elimination.journal.line'

    report_type = fields.Selection(string="Type", selection=[
        ('profit_loss', 'Profit and Loss'), ('bl', 'Balance Sheet'),
        ('share', 'Share Capital'), ('invest', 'Investment in company')])
    consolidation_period_line = fields.Many2one('consolidation.company_period')
    consolidation_account_ids = fields.Many2many('consolidation.account')
    elimination_journal_id = fields.Many2one('elimination.journal.conf')

    @api.onchange('report_type')
    def onchange_type_consolidation(self):
        for rec in self:
            if rec.report_type == 'share':
                return {'domain': {'consolidation_period_line': [
                    ('period_id', '=',
                     rec.elimination_journal_id.consolidation_period_id.id)]}}
