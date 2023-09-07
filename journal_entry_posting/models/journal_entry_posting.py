from odoo import models, fields, _
from odoo.exceptions import ValidationError
from datetime import datetime, date, timedelta


class JournalEntryPostingConfig(models.Model):
    _name = 'journal.entry.posting.config'
    _description = 'Journal Entry Posting Configuration'

    name = fields.Char()
    company_ids = fields.Many2many('res.company', default=lambda self: self.env.company)
    from_date = fields.Date()
    to_date = fields.Date()
    journals = fields.Many2many('account.journal',
                                domain=['|', ('type', '=', 'general'),
                                        ('name', 'ilike', 'ifrs')])
    active = fields.Boolean(default=False)
    limit = fields.Integer()
    state = fields.Selection(selection=[('draft', 'Draft'),
                                        ('scheduled', 'Scheduled')],
                             default='draft')
    scheduled_user = fields.Many2one('res.users',
                                     default=lambda self: self.env.user.id,
                                     )

    def journal_entry_posting(self, journal):
        journals = self.env['account.move.line'].search(
            [('move_id.state', '=', 'draft'),
             ('move_id.date', '>=', journal.from_date),
             ('move_id.date', '<=', journal.to_date),
             ('move_id.company_id', 'in', journal.company_ids.ids),
             ('move_id.journal_id', 'in', journal.journals.ids),
             ],limit=journal.limit).filtered(lambda line: not line.display_type).mapped(
            'move_id')
        for rec in journals:
            rec.auto_post = False
            rec.sudo().action_post()
            msg = _('This move posted by: %(user)s',
                    user=journal.scheduled_user.name)
            rec.message_post(body=msg)
        journals_lim = self.env['account.move'].search(
            [('state', '=', 'draft'),
             ('date', '>=', journal.from_date),
             ('date', '<=', journal.to_date),
             ('company_id', 'in', journal.company_ids.ids),
             ('journal_id', 'in', journal.journals.ids)])
        schedule = self.env.ref(
            'journal_entry_posting.account_move_config_cron_update')
        if journals_lim and schedule.active:
            self.journal_entry_posting_cron_update(journal)
        else:
            journal.state = 'draft'

    def journal_entry_posting_cron_update(self,journal):
        schedule = self.env.ref(
            'journal_entry_posting.journal_entry_posting_config_cron')
        if schedule.active:
            self.journal_entry_posting(journal)

    def schedule_journal_action(self):
        schedule = self.env.ref(
            'journal_entry_posting.journal_entry_posting_config_cron')
        if schedule.active:
            self.journal_entry_posting(self)
            self.state = 'scheduled'
        else:
            raise ValidationError(
                _('Please make the cron job active'))
