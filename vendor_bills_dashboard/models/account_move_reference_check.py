from odoo import models, api, fields
from odoo.exceptions import ValidationError


class AccountMoveReferenceInherit(models.Model):
    _inherit = "account.move"

    @api.constrains('payment_reference')
    def payment_reference_check(self):
        if self.move_type == 'out_invoice':
            moves = self.env['account.move'].search([
                ('partner_id', '=',
                 self.partner_id.id),
                ('move_type', '=',
                 'out_invoice')])
            if self.payment_reference:
                move = (moves.filtered(
                    lambda
                        x: x.payment_reference == self.payment_reference)).filtered(
                    lambda x: x.id != self.id)
                if move:
                    raise ValidationError(
                        'The Payment reference already exists in ' + move.name)
        elif self.move_type == 'out_refund':
            moves = self.env['account.move'].search([
                ('partner_id', '=',
                 self.partner_id.id),
                ('move_type', '=',
                 'out_refund')])
            if self.payment_reference:
                move = (moves.filtered(
                    lambda
                        x: x.payment_reference == self.payment_reference)).filtered(
                    lambda x: x.id != self.id)
                if move:
                    raise ValidationError(
                        'The Payment reference already exists in ' + move.name)
        elif self.move_type == 'out_receipt':
            moves = self.env['account.move'].search([
                ('partner_id', '=',
                 self.partner_id.id),
                ('move_type', '=',
                 'out_receipt')])
            if self.payment_reference:
                move = (moves.filtered(
                    lambda
                        x: x.payment_reference == self.payment_reference)).filtered(
                    lambda x: x.id != self.id)
                if move:
                    raise ValidationError(
                        'The Payment reference already exists in ' + move.name)
        elif self.move_type == 'in_invoice':
            moves = self.env['account.move'].search([
                ('partner_id', '=',
                 self.partner_id.id),
                ('move_type', '=',
                 'in_invoice')])
            if self.payment_reference:
                move = (moves.filtered(
                    lambda
                        x: x.payment_reference == self.payment_reference)).filtered(
                    lambda x: x.id != self.id)
                if move:
                    raise ValidationError(
                        'The Payment reference already exists in ' + move.name)
        elif self.move_type == 'in_refund':
            moves = self.env['account.move'].search([
                ('partner_id', '=',
                 self.partner_id.id),
                ('move_type', '=',
                 'in_refund')])
            if self.payment_reference:
                move = (moves.filtered(
                    lambda
                        x: x.payment_reference == self.payment_reference)).filtered(
                    lambda x: x.id != self.id)
                if move:
                    raise ValidationError(
                        'The Payment reference already exists in ' + move.name)
        elif self.move_type == 'in_receipt':
            moves = self.env['account.move'].search([
                ('partner_id', '=',
                 self.partner_id.id),
                ('move_type', '=',
                 'in_receipt')])
            if self.payment_reference:
                move = (moves.filtered(
                    lambda
                        x: x.payment_reference == self.payment_reference)).filtered(
                    lambda x: x.id != self.id)
                if move:
                    raise ValidationError(
                        'The Payment reference already exists in ' + move.name)

    def request_approval_button(self):
        # inherit of the function from account.move to check the validation of payment reference
        res = super(AccountMoveReferenceInherit, self).request_approval_button()
        journal = self.env['account.journal'].search([('name', '=',
                                                       'Vendor Bills')])
        if self.journal_id.id == journal.id:
            if not self.payment_reference:
                raise ValidationError(
                    'please provide a Invoice no / payment reference for Vendor Bill')
        return res

    def action_post(self):
        # inherit of the function from account.move to check the validation of payment reference
        res = super(AccountMoveReferenceInherit, self).action_post()
        journal = self.env['account.journal'].search([('name', '=',
                                                       'Vendor Bills')])
        if self.journal_id.id == journal.id:
            if not self.payment_reference:
                raise ValidationError(
                    'please provide a Invoice no / payment reference for Vendor Bill')
        return res
