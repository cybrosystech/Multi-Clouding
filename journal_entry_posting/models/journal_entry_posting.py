from odoo import models, fields, _
from odoo.exceptions import ValidationError
from datetime import datetime, date, timedelta


class JournalEntryPostingConfig(models.Model):
    _name = 'journal.entry.posting.config'
    _description = 'Journal Entry Posting Configuration'

    name = fields.Char()
    company_ids = fields.Many2many('res.company',
                                   default=lambda self: self.env.company)
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
    cron_id = fields.Many2one('ir.cron', String="Scheduled Action",
                              domain=[('name', 'ilike',
                                       'Account Journal Entry Posting :')])

    def journal_entry_posting_general(self):
        cron_id = self.env.ref(
            'journal_entry_posting.journal_entry_posting_config_cron_general').id
        journal = self.env['journal.entry.posting.config'].search(
            [('cron_id', '=', cron_id)], limit=1)
        journals = self.env['account.move.line'].search(
            [('move_id.state', '=', 'draft'),
             ('move_id.asset_id', '=', False),
             ('move_id.date', '>=', journal.from_date),
             ('move_id.date', '<=', journal.to_date),
             ('move_id.company_id', 'in', journal.company_ids.ids),
             ('move_id.journal_id', 'in', journal.journals.ids),
             ], limit=journal.limit).mapped('move_id')
        for rec in journals:
            rec.auto_post = 'no'
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
            'journal_entry_posting.journal_entry_posting_config_cron_update_general')
        if journals_lim and schedule.active:
            date = fields.Datetime.now()
            schedule.update({
                'nextcall': date + timedelta(seconds=15)
            })
        else:
            journal.state = 'draft'

    def journal_entry_posting(self):
        cron_id = self.env.ref(
            'journal_entry_posting.journal_entry_posting_config_cron').id
        journal = self.env['journal.entry.posting.config'].search(
            [('cron_id', '=', cron_id)], limit=1)
        journals = self.env['account.move.line'].search(
            [('move_id.state', '=', 'draft'),
             ('move_id.asset_id', '=', False),
             ('move_id.date', '>=', journal.from_date),
             ('move_id.date', '<=', journal.to_date),
             ('move_id.company_id', 'in', journal.company_ids.ids),
             ('move_id.journal_id', 'in', journal.journals.ids),
             ], limit=journal.limit).mapped('move_id')
        for rec in journals:
            rec.auto_post = 'no'
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
            'journal_entry_posting.journal_entry_posting_config_cron_update')
        if journals_lim and schedule.active:
            date = fields.Datetime.now()
            schedule.update({
                'nextcall': date + timedelta(seconds=15)
            })
        else:
            journal.state = 'draft'

    def journal_entry_posting_baghdad(self):
        cron_id = self.env.ref(
            'journal_entry_posting.journal_entry_posting_config_cron_baghdad').id
        journal = self.env['journal.entry.posting.config'].search(
            [('cron_id', '=', cron_id)], limit=1)
        journals = self.env['account.move.line'].search(
            [('move_id.state', '=', 'draft'),
             ('move_id.asset_id', '=', False),
             ('move_id.date', '>=', journal.from_date),
             ('move_id.date', '<=', journal.to_date),
             ('move_id.company_id', 'in', journal.company_ids.ids),
             ('move_id.journal_id', 'in', journal.journals.ids),
             ], limit=journal.limit).mapped('move_id')
        for rec in journals:
            rec.auto_post = 'no'
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
        schedule = self.env.ref('journal_entry_posting.journal_entry_posting_config_cron_update_baghdad')
        if journals_lim and schedule.active:
            date = fields.Datetime.now()
            schedule.update({
                'nextcall': date + timedelta(seconds=15)
            })
        else:
            journal.state = 'draft'

    def journal_entry_posting_erbill(self):
        cron_id = self.env.ref(
            'journal_entry_posting.journal_entry_posting_config_cron_erbill').id
        journal = self.env['journal.entry.posting.config'].search(
            [('cron_id', '=', cron_id)], limit=1)
        journals = self.env['account.move.line'].search(
            [('move_id.state', '=', 'draft'),
             ('move_id.asset_id', '=', False),
             ('move_id.date', '>=', journal.from_date),
             ('move_id.date', '<=', journal.to_date),
             ('move_id.company_id', 'in', journal.company_ids.ids),
             ('move_id.journal_id', 'in', journal.journals.ids),
             ], limit=journal.limit).mapped('move_id')
        for rec in journals:
            rec.auto_post = 'no'
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
            'journal_entry_posting.journal_entry_posting_config_cron_update_erbill')
        if journals_lim and schedule.active:
            date = fields.Datetime.now()
            schedule.update({
                'nextcall': date + timedelta(seconds=15)
            })
        else:
            journal.state = 'draft'

    def journal_entry_posting_cron_update_general(self):
        schedule = self.env.ref(
            'journal_entry_posting.journal_entry_posting_config_cron_general')
        if schedule.active:
            date = fields.Datetime.now()

            schedule.update({
                'nextcall': date + timedelta(seconds=15)
            })

    def journal_entry_posting_cron_update(self):
        schedule = self.env.ref(
            'journal_entry_posting.journal_entry_posting_config_cron')
        if schedule.active:
            # LOGGER.info(str(limits) + ' Entries activated')
            date = fields.Datetime.now()

            schedule.update({
                'nextcall': date + timedelta(seconds=15)
            })

    def journal_entry_posting_cron_update_baghdad(self):
        schedule = self.env.ref(
            'journal_entry_posting.journal_entry_posting_config_cron_baghdad')
        if schedule.active:
            date = fields.Datetime.now()

            schedule.update({
                'nextcall': date + timedelta(seconds=15)
            })

    def journal_entry_posting_cron_update_erbill(self):
        schedule = self.env.ref(
            'journal_entry_posting.journal_entry_posting_config_cron_erbill')
        if schedule.active:
            date = fields.Datetime.now()

            schedule.update({
                'nextcall': date + timedelta(seconds=15)
            })

    def schedule_journal_action(self):
        schedule = self.cron_id
        if schedule.active:
            date = fields.Datetime.now()
            schedule.update({
                'nextcall': date + timedelta(seconds=15)
            })
            self.state = 'scheduled'
        else:
            raise ValidationError(
                _('Please make the cron job active'))
