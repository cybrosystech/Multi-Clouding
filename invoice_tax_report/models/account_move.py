# -*- coding: utf-8 -*-

import math
from odoo import api, fields, models, _

class AccountMove(models.Model):
    _inherit = 'account.move'

    service_date_from = fields.Date('Service Date From')
    service_date_to = fields.Date('Service Date To')
    subtotal_local_amount = fields.Float('Subtotal Local Amount', compute='calc_local_amount',store=True)
    total_local_amount = fields.Float('Total Local Amount',compute='calc_local_amount',store=True )
    local_tax_amount = fields.Float('Total Local Tax',compute='calc_local_tax_amount',store=True)
    @api.depends('invoice_line_ids.subtotal_local_amount', 'invoice_line_ids.total_local_amount')
    def calc_local_amount(self):
        for rec in self:
            rec.subtotal_local_amount = round(sum(rec.invoice_line_ids.mapped('subtotal_local_amount')),2)
            rec.total_local_amount = round(sum(rec.invoice_line_ids.mapped('total_local_amount')),2)

    @api.depends('invoice_line_ids.local_tax_amount')
    def calc_local_tax_amount(self):
        for rec in self:
            rec.local_tax_amount = round(sum(rec.invoice_line_ids.mapped('local_tax_amount')),2)

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'
    new_rate = fields.Float('Rate',digits=(3,5))
    subtotal_local_amount = fields.Float('Subtotal Total Amount',compute='calc_local_amount',store=True)
    total_local_amount = fields.Float('Total Amount',compute='calc_local_amount',store=True)
    local_tax_amount = fields.Float('Local Tax',compute='calc_local_tax_amount',store=True)

    @api.onchange('company_currency_id')
    def _onchange_local_curr(self):
        for rec in self:
            rate = rec.company_currency_id._get_rates(rec.company_id, fields.date.today())
            exchange_rate = rate.get(rec.company_currency_id.id)
            rec.new_rate = exchange_rate

    @api.depends('new_rate','price_subtotal','price_total')
    def calc_local_amount(self):
        for rec in self:
            if rec.new_rate:
                rec.subtotal_local_amount = round((rec.price_subtotal / rec.new_rate), 2)
                rec.total_local_amount = round((rec.price_total / rec.new_rate), 2)
            else:
                rec.subtotal_local_amount = rec.total_local_amount = 0
    @api.depends('subtotal_local_amount','total_local_amount')
    def calc_local_tax_amount(self):
        for rec in self:
            rec.local_tax_amount = rec.total_local_amount - rec.subtotal_local_amount
