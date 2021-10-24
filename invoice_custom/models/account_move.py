# -*- coding: utf-8 -*-

import math
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_round
from odoo.tools.misc import formatLang
from dateutil.relativedelta import relativedelta
from datetime import date
import random


class AccountMove(models.Model):
    _inherit = 'account.move'

    def create(self, vals_list):
        todays_date = date.today()
        res = super(AccountMove, self).create(vals_list)
        # Invoice
        str = ''
        if res.move_type == 'out_invoice':
            str = 'INV/'+todays_date.year+'/'+todays_date.month+'/'+todays_date.day+''+random.randint(1,10)
        # Bill
        if res.move_type == 'in_invoice':
            str = 'BILL/'+todays_date.year+'/'+todays_date.month+'/'+todays_date.day+''+random.randint(1,10)

        res.name = str
        return res
