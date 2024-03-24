from odoo import api,models, fields
from odoo.addons.account.wizard.account_payment_register import AccountPaymentRegister

class AccountPaymentRegisterMpatch(AccountPaymentRegister):

    def _create_payment_vals_from_batch(self, batch_result):
        batch_values = self._get_wizard_values_from_batch(batch_result)

        if batch_values['payment_type'] == 'inbound':
            partner_bank_id = self.journal_id.bank_account_id.id
        else:
            if batch_result['key_values']['partner_bank_id']:
                partner_bank_id = batch_result['key_values']['partner_bank_id']
            elif batch_result['key_values']['partner_id']:
                partner_id = self.env['res.partner'].browse(batch_result['key_values']['partner_id'])
                bank_ids = partner_id.bank_ids \
                    .filtered(lambda x: x.company_id.id in (False, batch_result['move_id'].company_id.id))._origin
                if bank_ids:
                    bankid = bank_ids[:1]
                    partner_bank_id = bankid.id
                else:
                    partner_bank_id = False
            else:
                partner_bank_id= False

        payment_method = self.payment_method_id

        if batch_values['payment_type'] != payment_method.payment_type:
            payment_method = self._get_batch_available_payment_methods(
                self.journal_id, batch_values['payment_type'])[:1]

        return {
            'date': self.payment_date,
            'amount': batch_values['source_amount_currency'],
            'payment_type': batch_values['payment_type'],
            'partner_type': batch_values['partner_type'],
            'ref': self._get_batch_communication(batch_result),
            'journal_id': self.journal_id.id,
            'currency_id': batch_values['source_currency_id'],
            'partner_id': batch_values['partner_id'],
            'partner_bank_id': partner_bank_id,
            'payment_method_id': payment_method.id,
            'destination_account_id': batch_result['lines'][0].account_id.id
        }

    def _create_payments(self):
        self.ensure_one()
        batches = self._get_batches()
        edit_mode = self.can_edit_wizard and (len(batches[0]['lines']) == 1 or self.group_payment)
        to_process = []

        if edit_mode:
            payment_vals = self._create_payment_vals_from_wizard()
            to_process.append({
                'create_vals': payment_vals,
                'to_reconcile': batches[0]['lines'],
                'batch': batches[0],
            })
        else:
            # Don't group payments: Create one batch per move.
            if not self.group_payment:
                new_batches = []
                for batch_result in batches:
                    for line in batch_result['lines']:
                        new_batches.append({
                            **batch_result,
                            'lines': line,
                            'move_id':line.move_id,
                        })
                batches = new_batches

            for batch_result in batches:
                to_process.append({
                    'create_vals': self._create_payment_vals_from_batch(batch_result),
                    'to_reconcile': batch_result['lines'],
                    'batch': batch_result,
                })

        payments = self._init_payments(to_process, edit_mode=edit_mode)
        self._post_payments(to_process, edit_mode=edit_mode)
        self._reconcile_payments(to_process, edit_mode=edit_mode)
        return payments

    AccountPaymentRegister._create_payment_vals_from_batch = _create_payment_vals_from_batch
    AccountPaymentRegister._create_payments = _create_payments

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
