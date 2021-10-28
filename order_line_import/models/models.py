# -*- coding: utf-8 -*-
# author     :guoyihot@outlook.com
# date       ：
# description:

from odoo import models, fields, api,_
from odoo.exceptions import UserError

# class order_line_import(models.Model):
#     _name = 'order_line_import.order_line_import'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         self.value2 = float(self.value) / 100