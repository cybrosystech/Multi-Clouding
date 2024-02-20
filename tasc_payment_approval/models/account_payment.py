from odoo import models, fields, api


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    payment_approval_batch_id = fields.Many2one('account.payment.approval',
                                                string="Payment Approval Batch",
                                                copy=False)
    invoice_number = fields.Char("Invoice Number",
                                 compute='compute_invoice_number_and_amount',
                                 )

    invoice_amount = fields.Float("Invoice Amount",
                                  compute="compute_invoice_number_and_amount",
                                  )

    @api.depends('reconciled_bill_ids', 'reconciled_invoice_ids')
    def compute_invoice_number_and_amount(self):
        for rec in self:
            rec.invoice_number = False
            rec.invoice_amount = False
            if rec.reconciled_bill_ids:
                bill_name = ""
                bill_amt = 0
                for bill in rec.reconciled_bill_ids:
                    bill_name += bill.name + " , "
                    bill_amt += bill.amount_total + bill_amt
                rec.invoice_number = bill_name
                rec.invoice_amount = bill_amt
            else:
                rec.invoice_number = "Manual"
            if rec.reconciled_invoice_ids:
                inv_name = ""
                inv_amt = 0
                for inv in rec.reconciled_invoice_ids:
                    inv_name += inv.name + " , "
                    inv_amt += inv.amount_total + inv_amt
                rec.invoice_number = inv_name
                rec.invoice_amount = inv_amt
            else:
                rec.invoice_number = "Manual"
