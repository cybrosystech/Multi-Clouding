from odoo import api,models, fields, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta


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

    @api.constrains('to_date','from_date')
    def onsave_period(self):
        if self.to_date < self.from_date:
            raise UserError(
                "The end date should be greater than or equal to start date.")
        else:
            today = datetime.today().date()
            end_of_month = today.replace(day=1) + relativedelta(months=1, days=-1)
            # Adjust dates or default to today
            if  self.from_date > end_of_month or  self.to_date > end_of_month:
                raise UserError("The start date or end date should not exceed the"
                                " end date of the current month.")

    def journal_entry_posting_general(self):
        cron_id = self.env.ref(
            'journal_entry_posting.journal_entry_posting_config_cron_general').id
        journal = self.env['journal.entry.posting.config'].search(
            [('cron_id', '=', cron_id)], limit=1)
        today = datetime.today().date()

        # Adjust dates or default to today
        from_date = journal.from_date if journal.from_date and journal.from_date <= today else today
        to_date = journal.to_date if journal.to_date and journal.to_date <= today else today
        journals = self.env['account.move'].search(
            [('state', '=', 'draft'),
             ('date', '>=', from_date),
             ('date', '<=', to_date),
             ('company_id', 'in', journal.company_ids.ids),
             ('journal_id', 'in', journal.journals.ids),
             ],order="id ASC", limit=journal.limit)
        journals.auto_post = 'no'
        journals._post()
        msg = _('This move posted by: %(user)s',
                user=journal.scheduled_user.name)
        journals.mapped(lambda journal: journal.message_post(body=msg))

        journals_lim = self.env['account.move'].search(
            [('state', '=', 'draft'),
             ('date', '>=', from_date),
             ('date', '<=', to_date),
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
        today = datetime.today().date()
        # Adjust dates or default to today
        from_date = journal.from_date if journal.from_date and journal.from_date <= today else today
        to_date = journal.to_date if journal.to_date and journal.to_date <= today else today
        journals = self.env['account.move'].search(
            [('state', '=', 'draft'),
             ('date', '>=', from_date),
             ('date', '<=', to_date),
             ('company_id', 'in', journal.company_ids.ids),
             ('journal_id', 'in', journal.journals.ids),
             ], order="id ASC", limit=journal.limit)
        journals.auto_post = 'no'
        journals._post()
        msg = _('This move posted by: %(user)s',
                user=journal.scheduled_user.name)
        journals.mapped(lambda journal: journal.message_post(body=msg))
        journals_lim = self.env['account.move'].search(
            [('state', '=', 'draft'),
             ('date', '>=', from_date),
             ('date', '<=', to_date),
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
        today = datetime.today().date()
        # Adjust dates or default to today
        from_date = journal.from_date if journal.from_date and journal.from_date <= today else today
        to_date = journal.to_date if journal.to_date and journal.to_date <= today else today
        journals = self.env['account.move'].search(
            [('state', '=', 'draft'),
             ('date', '>=', from_date),
             ('date', '<=', to_date),
             ('company_id', 'in', journal.company_ids.ids),
             ('journal_id', 'in', journal.journals.ids),
             ], order="id ASC", limit=journal.limit)
        journals.auto_post = 'no'
        journals._post()
        msg = _('This move posted by: %(user)s',
                user=journal.scheduled_user.name)
        journals.mapped(lambda journal: journal.message_post(body=msg))
        journals_lim = self.env['account.move'].search(
            [('state', '=', 'draft'),
             ('date', '>=', from_date),
             ('date', '<=', to_date),
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
        today = datetime.today().date()
        # Adjust dates or default to today
        from_date = journal.from_date if journal.from_date and journal.from_date <= today else today
        to_date = journal.to_date if journal.to_date and journal.to_date <= today else today
        journals = self.env['account.move'].search(
            [('state', '=', 'draft'),
             ('date', '>=', from_date),
             ('date', '<=', to_date),
             ('company_id', 'in', journal.company_ids.ids),
             ('journal_id', 'in', journal.journals.ids),
             ], order="id ASC", limit=journal.limit)
        journals.auto_post = 'no'
        journals._post()
        msg = _('This move posted by: %(user)s',
                user=journal.scheduled_user.name)
        journals.mapped(lambda journal: journal.message_post(body=msg))
        journals_lim = self.env['account.move'].search(
            [('state', '=', 'draft'),
             ('date', '>=', from_date),
             ('date', '<=', to_date),
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

    def split_list(self, lst, limit):
        return [lst[i:i + limit] for i in range(0, len(lst), limit)]

    def action_post_journal_entries(self):
        today = datetime.today().date()
        # Adjust dates or default to today
        from_date = self.from_date if self.from_date  else today
        to_date = self.to_date if self.to_date else today
        journals = self.env['account.move'].search(
            [('state', '=', 'draft'),
             ('date', '>=', from_date),
             ('date', '<=', to_date),
             ('company_id', 'in', self.company_ids.ids),
             ('journal_id', 'in', self.journals.ids),
             ])
        if journals:
            sublists = self.split_list(journals, self.limit)
            self.create_jobs(sublists)

    def create_jobs(self, sublist):
        for i in sublist:
            self.with_delay(priority=5)._process_job(i)

    def _process_job(self, iteration):
        # Process the job
        # Perform your task here
        moves = iteration
        moves.auto_post = 'no'
        moves._post(False)
        msg = _('This move posted by: %(user)s',
            user=self.scheduled_user.name)
        moves.mapped(lambda journal: journal.message_post(body=msg))
