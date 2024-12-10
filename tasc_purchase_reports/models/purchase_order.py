from odoo import api, fields,models

PAYMENT_STATE_SELECTION = [
        ('not_paid', 'Not Paid'),
        ('in_payment', 'In Payment'),
        ('paid', 'Paid'),
        ('partial', 'Partially Paid'),
]


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'


    payment_term_id = fields.Many2one(
        comodel_name='account.payment.term',
        string="Payment Terms",
        check_company=True,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    supplier_representative = fields.Char(string="Supplier Representative")
    supplier_email = fields.Char(string="Supplier Email")
    supplier_phone = fields.Char(string="Supplier Phone")
    payment_state = fields.Selection(
        selection=PAYMENT_STATE_SELECTION,
        string="Payment Status",
        compute='_compute_payment_state', store=True, readonly=True,
        copy=False,
        tracking=True,
    )

    @api.depends('state', 'invoice_ids.payment_state')
    def _compute_payment_state(self):
        for rec in self:
            if rec.invoice_ids:
                payment_states = rec.invoice_ids.mapped('payment_state')
                # Use a set for unique states to avoid repeated computation
                unique_states = set(payment_states)
                if not unique_states or unique_states == {'not_paid'}:
                    rec.payment_state = 'not_paid'
                elif unique_states == {'paid'}:
                    rec.payment_state = 'paid'
                elif 'in_payment' in unique_states and unique_states <= {'not_paid',
                                                                         'in_payment'}:
                    rec.payment_state = 'in_payment'
                else:
                    rec.payment_state = 'partial'
            else:
                rec.payment_state = 'not_paid'


    def _prepare_invoice(self):
        invoice_vals = super()._prepare_invoice()
        invoice_vals['invoice_payment_term_id'] = self.payment_term_id.id
        return invoice_vals