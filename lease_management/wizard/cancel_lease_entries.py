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

    def action_apply(self):
        print(self.env.company.id)
        print(self.env.company.name)
        account_moves = self.env['account.move'].search([
            ('date', '<', self.date),
            ('state', '!=', 'cancel'),
            '|',
            ('leasee_contract_id', '!=', False),
            '&',
            ('asset_id', '!=', False),
            ('asset_id.leasee_contract_ids', '!=', False),
            ('company_id', '=', self.env.company.id)
        ]).filtered(lambda m: m.date < self.date)
        # account_moves.button_draft()
        print('account_moves', account_moves)
        account_moves.button_cancel()
        payments = self.env['account.payment'].search([
            ('date', '<', self.date),
            ('state', '!=', 'cancel'),
            ('is_leasee_payment', '!=', False),
            ('company_id', '=', self.env.company.id)
        ]).filtered(lambda m: m.date < self.date)
        payments.action_cancel()
