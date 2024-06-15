# -*- coding: utf-8 -*-
from odoo import fields, models, _


class AccoutGroup(models.Model):
    _inherit = 'account.group'

    group_sequence = fields.Integer(string="Sequence", required=False, )