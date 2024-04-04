import logging

from odoo import models, fields, api
from datetime import datetime
import calendar
from datetime import timedelta

LOGGER = logging.getLogger(__name__)


class AccountMoveInheritActive(models.Model):
    _inherit = "account.move"

    active = fields.Boolean(default=True)

    def active_journal_entry(self, date, limit):
        if not date:
            date = fields.Date.today()
        date_range = datetime.strptime(date, '%Y-%m-%d')
        journal_id = self.env['account.move'].search(
            [('date', '<=', date_range),
             ('active', '=', False)],
            limit=int(limit))
        journal_count = 0
        for i in journal_id:
            i.active = True
            journal_count += 1
        journals = self.env['account.move'].search(
            [('date', '<=', date_range),
             ('active', '=', False)])
        if len(journals) > 0 and journal_count == int(limit):
            LOGGER.info(limit + ' journal Entries activated')
            date = fields.Datetime.now()
            schedule = self.env.ref(
                'journals_active_cron.account_move_activate_cron_update')
            schedule.update({
                'nextcall': date + timedelta(seconds=30)
            })
            LOGGER.info('Account move active Cron Update')

    def active_journal_cron_update(self):
        date = fields.Datetime.now()
        schedule = self.env.ref(
            'journals_active_cron.account_move_activate_action')
        schedule.update({
            'nextcall': date + timedelta(seconds=30)
        })
        LOGGER.info('Account Move Active updated')

    def deactivate_journal_entry(self, date, limit):
        date_now = fields.datetime.now()
        date_range = datetime.strptime(date, '%Y-%m-%d')
        if date_range < date_now:
            date_range = date_now
        journal_id = self.env['account.move'].search(
            [('date', '>=', date_range),
             ('active', '=', True)], limit=int(limit))
        journal_count = 0
        for i in journal_id:
            i.active = False
            journal_count += 1
        journals = self.env['account.move'].search(
            [('date', '<=', date_range),
             ('active', '=', False)])
        if len(journals) > 0 and journal_count == int(limit):
            LOGGER.info(limit + ' journal Entries deactivated')
            date = fields.Datetime.now()
            schedule = self.env.ref(
                'journals_active_cron.account_move_deactivate_cron_update')
            schedule.update({
                'nextcall': date + timedelta(seconds=30)
            })
            LOGGER.info('Account move active Cron Update')

    def active_journal_cron_update_false(self):
        date = fields.Datetime.now()
        schedule = self.env.ref(
            'journals_active_cron.account_move_deactivate_action')
        schedule.update({
            'nextcall': date + timedelta(seconds=30)
        })
        LOGGER.info('Account Move Active False updated')
