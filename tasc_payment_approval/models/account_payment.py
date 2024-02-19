from odoo import models, fields, api


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    payment_approval_batch_id = fields.Many2one('account.payment.approval',
                                                string="Payment Approval Batch",copy=False)
    invoice_number = fields.Char("Invoice Number",
                                 compute='compute_invoice_number_and_amount',
                                 )

    invoice_amount = fields.Float("Invoice Amount",
                                  compute="compute_invoice_number_and_amount",
                                 )

    @api.depends('reconciled_bill_ids', 'reconciled_invoice_ids')
    def compute_invoice_number_and_amount(self):
        for rec in self:
            rec.invoice_number=False
            rec.invoice_amount= False
            if rec.reconciled_bill_ids:
                rec.invoice_number = rec.reconciled_bill_ids[0].name
                rec.invoice_amount = rec.reconciled_bill_ids[0].amount_total
            if rec.reconciled_invoice_ids:
                rec.invoice_number = rec.reconciled_invoice_ids[0].name
                rec.invoice_amount = rec.reconciled_invoice_ids[0].amount_total
