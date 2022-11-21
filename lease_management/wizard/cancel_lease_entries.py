# -*- coding: utf-8 -*-
""" init object """
from odoo import fields, models, api, _, tools, SUPERUSER_ID
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, date, timedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DTF
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from dateutil.relativedelta import relativedelta
from odoo.fields import Datetime as fieldsDatetime
import calendar
from odoo import http
from odoo.http import request
from odoo import tools


class CancelLeaseEntries(models.TransientModel):
    _name = 'cancel.lease.entries'
    _description = 'Cancel Lease Entries'

    date = fields.Date(default=lambda self: fields.Datetime.now(),
                       required=True, )
    asset_journal_include = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No')], string='Asset Entry Cancellation')
    leasee_contract_id = fields.Many2many('leasee.contract',
                                          string='Leasee Contract')

    def action_apply(self):
        if not self.leasee_contract_id:
            domain = [('date', '<=', self.date),
                      ('state', '!=', 'cancel'),
                      '|',
                      ('leasee_contract_id', '!=', False),
                      '&',
                      ('asset_id', '!=', False),
                      ('asset_id.leasee_contract_ids', '!=', False),
                      ('company_id', '=', self.env.company.id)]
            if self.asset_journal_include == 'yes':
                domain = [('date', '<=', self.date),
                          ('state', '!=', 'cancel'),
                          '|',
                          ('leasee_contract_id', '!=', False),
                          '&', ('company_id', '=', self.env.company.id)]
            account_moves = self.env['account.move'].search(domain).filtered(lambda m: m.date <= self.date)
            # account_moves.button_draft()
            account_moves.button_cancel()
            payments = self.env['account.payment'].search([
                ('date', '<=', self.date),
                ('state', '!=', 'cancel'),
                ('is_leasee_payment', '!=', False),
                ('company_id', '=', self.env.company.id)
            ]).filtered(lambda m: m.date <= self.date)
            payments.action_cancel()
        else:
            account_moves = self.leasee_contract_id.mapped(
                lambda x: x.account_move_ids.filtered(
                    lambda m: m.date <= self.date))
            if self.asset_journal_include == 'yes':
                asset_account_moves = self.leasee_contract_id.mapped(
                    lambda x: x.asset_id.depreciation_move_ids.filtered(
                        lambda m: m.date <= self.date))
                asset_account_moves.button_cancel()
            account_moves.button_cancel()
            payments = self.leasee_contract_id.mapped(
                lambda x: x.payment_ids.filtered(lambda m: m.date <= self.date))
            payments.action_cancel()
            for lease in self.leasee_contract_id:
                display_message = 'Journal Entries for the: ' + lease.name + '<br/>' \
                                                                             'Has been cancelled by: ' + \
                                  str(self.env.user.name) + 'till date:' + str(
                    self.date)
                lease.message_post(body=display_message)
