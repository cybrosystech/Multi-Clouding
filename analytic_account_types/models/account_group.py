# -*- coding: utf-8 -*-

import math
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_round
from odoo.tools.misc import formatLang
from dateutil.relativedelta import relativedelta
from datetime import datetime
import random


class AccoutGroup(models.Model):
    _inherit = 'account.group'

    group_sequence = fields.Char(string="Sequence", required=False, )

    # @api.model_create_multi
    # def create(self, vals_list):
    #     res = super(AccoutGroup, self).create(vals_list)
    #     for rec in res:
    #         rec.group_sequence = self.env['ir.sequence'].next_by_code('account.group.temporary.seq')
    #     return res