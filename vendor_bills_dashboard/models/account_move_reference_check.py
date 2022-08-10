from odoo import models, api
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
