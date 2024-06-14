# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright 2019 EquickERP
#
##############################################################################

from odoo import models, api, fields, _
from odoo.exceptions import ValidationError


class purchase_order(models.Model):
    _inherit = 'purchase.order'

    adv_payment_ids = fields.Many2many('account.payment',
                                       string="Advance Payment", copy=False)

    def action_view_adv_payments(self):
        action = self.env.ref('account.action_account_payments_payable').read()[
            0]
        action['domain'] = [('id', 'in', self.adv_payment_ids.ids)]
        action['context'] = {'create': 0}
        return action

    def btn_advance_payment(self):
        ctx = {'default_payment_type': 'outbound',
               'default_partner_type': 'supplier',
               'search_default_outbound_filter': 1,
               'res_partner_search_mode': 'supplier',
               'default_partner_id': self.partner_id.id,
               'default_ref': self.name,
               'default_currency_id': self.currency_id.id, }
        return {'name': _("Advance Payment"),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'view_type': 'form',
                'res_model': 'account.payment',
                'target': 'new',
                'view_id': self.env.ref(
                    'eq_purchase_advance_payment.view_purchase_advance_account_payment_form').id,
                'context': ctx}


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    create_in_state_purchase = fields.Selection([('draft', 'Draft'),
                                                 ('confirm', 'Confirm')],
                                                default='confirm',
                                                string="Payment Status")

    @api.depends('journal_id')
    def _compute_currency_id(self):
        for pay in self:
            if not pay.currency_id:
                pay.currency_id = pay.journal_id.currency_id or pay.journal_id.company_id.currency_id

    def create_purchase_adv_payment(self):
        if self.amount <= 0.0:
            raise ValidationError(
                _("The payment amount cannot be negative or zero."))
        if self.create_in_state_purchase == 'confirm':
            self.action_post()
        if self.env.context.get('active_id'):
            purchase_id = self.env['purchase.order'].browse(
                self.env.context.get('active_id'))
            purchase_id.write({'adv_payment_ids': [(4, self.id)]})
        return True
