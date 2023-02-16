from odoo import models, api, fields
from odoo.exceptions import ValidationError


class AccountMoveReferenceInherit(models.Model):
    _inherit = "account.move"

    @api.constrains('payment_reference')
    def payment_reference_check(self):
        """This function is being performed at the time of saving a journal to
        check if the payment reference has been a unique"""
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

    @api.constrains('ref', 'move_type', 'partner_id', 'journal_id',
                    'invoice_date', 'state')
    def _check_duplicate_supplier_reference(self):
        """removed the validation of bill reference check"""
        moves = self.filtered(lambda
                                  move: move.state == 'posted' and move.is_purchase_document() and move.ref)
        if not moves:
            return

        self.env["account.move"].flush([
            "ref", "move_type", "invoice_date", "journal_id",
            "company_id", "partner_id", "commercial_partner_id",
        ])
        self.env["account.journal"].flush(["company_id"])
        self.env["res.partner"].flush(["commercial_partner_id"])

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
        # if duplicated_moves:
        #     raise ValidationError(
        #         _('Duplicated vendor reference detected. You probably encoded twice the same vendor bill/credit note:\n%s') % "\n".join(
        #             duplicated_moves.mapped(
        #                 lambda m: "%(partner)s - %(ref)s - %(date)s" % {
        #                     'ref': m.ref,
        #                     'partner': m.partner_id.display_name,
        #                     'date': format_date(self.env, m.invoice_date),
        #                 })
        #         ))

    def request_approval_button(self):
        """inherit of the function from account. Move to check the validation of
        payment reference"""
        res = super(AccountMoveReferenceInherit, self).request_approval_button()
        journal = self.env['account.journal'].search([('name', '=',
                                                       'Vendor Bills')])
        for rec in journal:
            if self.journal_id.id == rec.id:
                if not self.payment_reference:
                    raise ValidationError(
                        'please provide a Invoice no / payment reference for Vendor Bill')
            return res

    def action_post(self):
        """inherit of the function from account. Move to check the validation of
        payment reference"""
        res = super(AccountMoveReferenceInherit, self).action_post()
        journal = self.env['account.journal'].search([('name', '=',
                                                       'Vendor Bills')])
        for rec in journal:
            if self.journal_id.id == rec.id:
                if not self.payment_reference:
                    raise ValidationError(
                        'please provide a Invoice no / payment reference for Vendor Bill')
        return res

    def action_cancel_draft_entries(self):
        """server action has been defined to cancel draft journal entries"""
        for rec in self:
            if rec.state != 'draft':
                raise ValidationError('Cannot cancel the posted entries')
            rec.button_cancel()
