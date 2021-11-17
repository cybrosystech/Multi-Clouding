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
    _inherit = 'account.account'

    group_sequence = fields.Char(related='group_id.group_sequence', store=1)
