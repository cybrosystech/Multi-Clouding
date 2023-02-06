from odoo import models, fields, _
from odoo.exceptions import ValidationError
from datetime import datetime, date, timedelta


class AccountMoveConfig(models.Model):
    _name = 'account.move.config'

    name = fields.Char()
    company_id = fields.Many2one('res.company')
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
                                     readonly=True)

    def journal_entry_posting(self):
        journal_config = self.search([('active', '=', True)])
        journals = self.env['account.move'].search(
            [('state', '=', 'draft'),
             ('date', '>=', journal_config.from_date),
             ('date', '<=', journal_config.to_date),
             ('company_id', '=', journal_config.company_id.id),
             ('journal_id', 'in', journal_config.journals.ids)],
            limit=journal_config.limit)
        for rec in journals:
            rec.auto_post = False
            rec.sudo().action_post()
            msg = _('This move posted by: %(user)s',
                    user=journal_config.scheduled_user.name)
            rec.message_post(body=msg)
        journals_lim = self.env['account.move'].search(
            [('state', '=', 'draft'),
             ('date', '>=', journal_config.from_date),
             ('date', '<=', journal_config.to_date),
             ('company_id', '=', journal_config.company_id.id),
             ('journal_id', 'in', journal_config.journals.ids)])
        schedule = self.env.ref(
            'journal_entry_posting.account_move_config_cron_update')
        if journals_lim and schedule.active:
            # LOGGER.info(str(limits) + ' Entries activated')
            date = fields.Datetime.now()

            schedule.update({
                'nextcall': date + timedelta(seconds=20)
            })
        else:
            journal_config.state = 'draft'

    def journal_entry_posting_cron_update(self):
        schedule = self.env.ref(
            'journal_entry_posting.account_move_config_cron')
        if schedule.active:
            # LOGGER.info(str(limits) + ' Entries activated')
            date = fields.Datetime.now()

            schedule.update({
                'nextcall': date + timedelta(seconds=20)
            })

    def schedule_journal_action(self):
        self.scheduled_user = self.env.user.id
        schedule = self.env.ref(
            'journal_entry_posting.account_move_config_cron')
        journal_config = self.env['account.move.config'].search(
            [('state', '=', 'scheduled')])
        if journal_config:
            raise ValidationError(
                _('Already you have scheduled the journal action'))
        if schedule.active:
            # LOGGER.info(str(limits) + ' Entries activated')
            date = fields.Datetime.now()

            schedule.update({
                'nextcall': date + timedelta(seconds=20)
            })
            self.state = 'scheduled'
        else:
            raise ValidationError(
                _('Please make the cron job active'))
