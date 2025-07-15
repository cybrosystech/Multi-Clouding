# -*- coding: utf-8 -*-
from odoo import models, fields


class LeaseeElectricity(models.Model):
    _name = 'leasee.electricity'

    leasee_reference = fields.Char()
    leasee_contract_id = fields.Many2one('leasee.contract')