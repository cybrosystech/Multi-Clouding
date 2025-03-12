from odoo import models, api, fields
from odoo.exceptions import ValidationError


class AccountMoveReferenceInherit(models.Model):
    _inherit = "account.move"

    @api.constrains('payment_reference')
    def payment_reference_check(self):
        print("payment_reference_check")
        """This function is being performed at the time of saving a journal to
        check if the payment reference has been a unique"""
        for rec in self:
            if rec.move_type == 'out_invoice':
                moves = rec.env['account.move'].search([
                    ('partner_id', '=',
                     rec.partner_id.id),
                    ('move_type', '=',
                     'out_invoice')])
                if rec.payment_reference:
                    move = (moves.filtered(
                        lambda
                            x: x.payment_reference == rec.payment_reference)).filtered(
                        lambda x: x.id != rec.id and not rec.is_from_sales)
                    if move:
                        raise ValidationError(
                            'The Payment reference already exists in ' + move.name)
            elif rec.move_type == 'out_refund':
                moves = rec.env['account.move'].search([
                    ('partner_id', '=',
                     rec.partner_id.id),
                    ('move_type', '=',
                     'out_refund')])
                if rec.payment_reference:
                    move = (moves.filtered(
                        lambda
                            x: x.payment_reference == rec.payment_reference)).filtered(
                        lambda x: x.id != rec.id)
                    if move:
                        raise ValidationError(
                            'The Payment reference already exists in ' + move.name)
            elif rec.move_type == 'out_receipt':
                moves = rec.env['account.move'].search([
                    ('partner_id', '=',
                     rec.partner_id.id),
                    ('move_type', '=',
                     'out_receipt')])
                if rec.payment_reference:
                    move = (moves.filtered(
                        lambda
                            x: x.payment_reference == rec.payment_reference)).filtered(
                        lambda x: x.id != rec.id)
                    if move:
                        raise ValidationError(
                            'The Payment reference already exists in ' + move.name)
            elif rec.move_type == 'in_invoice':
                moves = rec.env['account.move'].search([
                    ('partner_id', '=',
                     rec.partner_id.id),
                    ('move_type', '=',
                     'in_invoice')])
                if rec.payment_reference:
                    move = (moves.filtered(
                        lambda
                            x: x.payment_reference == rec.payment_reference)).filtered(
                        lambda x: x.id != rec.id and not rec.is_from_purchase)
                    if move:
                        raise ValidationError(
                            'The Payment reference already exists in ' + move.name)
            elif rec.move_type == 'in_refund':
                moves = rec.env['account.move'].search([
                    ('partner_id', '=',
                     rec.partner_id.id),
                    ('move_type', '=',
                     'in_refund')])
                if rec.payment_reference:
                    move = (moves.filtered(
                        lambda
                            x: x.payment_reference == rec.payment_reference)).filtered(
                        lambda x: x.id != rec.id)
                    if move:
                        raise ValidationError(
                            'The Payment reference already exists in ' + move.name)
            elif rec.move_type == 'in_receipt':
                moves = rec.env['account.move'].search([
                    ('partner_id', '=',
                     rec.partner_id.id),
                    ('move_type', '=',
                     'in_receipt')])
                if rec.payment_reference:
                    move = (moves.filtered(
                        lambda
                            x: x.payment_reference == rec.payment_reference)).filtered(
                        lambda x: x.id != rec.id)
                    if move:
                        raise ValidationError(
                            'The Payment reference already exists in ' + move.name)

    @api.constrains('ref', 'move_type', 'partner_id', 'journal_id',
                    'invoice_date', 'state')
    def _check_duplicate_supplier_reference(self):
        print("_check_duplicate_supplier_reference")
        """removed the validation of bill reference check"""
        moves = self.filtered(lambda
                                  move: move.state == 'posted' and move.is_purchase_document() and move.ref)
        if not moves:
            return

        # /!\ Computed stored fields are not yet inside the database.
        self._cr.execute('''
                SELECT move2.id
                FROM account_move move
                JOIN account_journal journal ON journal.id = move.journal_id
                JOIN res_partner partner ON partner.id = move.partner_id
                INNER JOIN account_move move2 ON
                    move2.ref = move.ref
                    AND move2.company_id = journal.company_id
                    AND move2.commercial_partner_id = partner.commercial_partner_id
                    AND move2.move_type = move.move_type
                    AND (move.invoice_date is NULL OR move2.invoice_date = move.invoice_date)
                    AND move2.id != move.id
                WHERE move.id IN %s
            ''', [tuple(moves.ids)])
        duplicated_moves = self.browse([r[0] for r in self._cr.fetchall()])

    def request_approval_button(self):
        print("request_approval_button3")
        """inherit of the function from account. Move to check the validation of
        payment reference"""
        journal = self.env['account.journal'].search([('name', '=',
                                                       'Vendor Bills')],
                                                     limit=1)
        for rec in journal:
            if self.journal_id.id == rec.id:
                if not self.payment_reference:
                    raise ValidationError(
                        'please provide a Invoice no / payment reference for '
                        'Vendor Bill')
        res = super(AccountMoveReferenceInherit, self).request_approval_button()
        return res

    def button_request_purchase_cycle(self):
        print("button_request_purchase_cycle")
        journal = self.env['account.journal'].search([('name', '=',
                                                       'Vendor Bills')],
                                                     limit=1)
        for record in self:
            for rec in journal:
                if record.journal_id.id == rec.id:
                    if not record.payment_reference:
                        raise ValidationError(
                            'please provide a Invoice no / payment reference for '
                            'Vendor Bill')
            res = super(AccountMoveReferenceInherit,
                        record).button_request_purchase_cycle()

            return res


    def action_post(self):
        """inherit of the function from account. Move to check the validation of
        payment reference"""
        journal = self.env['account.journal'].search([('name', '=',
                                                       'Vendor Bills')],
                                                     limit=1)
        for rec in self:
            if rec.journal_id.id == journal.id:
                if not rec.payment_reference:
                    raise ValidationError(
                        'please provide a Invoice no / payment reference for'
                        ' Vendor Bill')
        res = super(AccountMoveReferenceInherit, self).action_post()
        return res

    def action_cancel_draft_entries(self):
        """server action has been defined to cancel draft journal entries"""
        for rec in self:
            if rec.state != 'draft':
                raise ValidationError('Cannot cancel the posted entries')
            rec.button_cancel()

