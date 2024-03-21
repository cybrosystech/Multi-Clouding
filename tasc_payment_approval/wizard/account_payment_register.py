from odoo import api,models, fields


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    @api.model
    def _default_purpose_code_id(self):
        default_purpose_code = self.env['default.purpose.code'].search([('company_id','=',self.env.company.id)])
        if default_purpose_code:
            return default_purpose_code.purpose_code_id.id
        else:
            return False

    purpose_code_id = fields.Many2one('purpose.code', string="Purpose Code",default=_default_purpose_code_id)

    def _create_payment_vals_from_wizard(self):
        vals = super()._create_payment_vals_from_wizard()
        vals.update({'purpose_code_id': self.purpose_code_id.id})
        return vals

    def _create_payment_vals_from_batch(self, batch_result):
        res = super()._create_payment_vals_from_batch(batch_result)
        res.update({'purpose_code_id': self.purpose_code_id.id})
        return res
