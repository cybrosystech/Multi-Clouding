# -*- coding: utf-8 -*-

import math
from odoo import fields, models, _


class AccoutGroup(models.Model):
    _inherit = 'account.account'

    group_sequence = fields.Integer(related='group_id.group_sequence', store=True)
