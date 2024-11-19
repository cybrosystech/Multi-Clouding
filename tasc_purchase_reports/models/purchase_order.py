from odoo import fields,models

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



    def _prepare_invoice(self):
        invoice_vals = super()._prepare_invoice()
        invoice_vals['invoice_payment_term_id'] = self.payment_term_id.id
        return invoice_vals