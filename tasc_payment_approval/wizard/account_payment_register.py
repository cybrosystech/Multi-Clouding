from odoo import api, models, fields, _
from odoo.addons.account.wizard.account_payment_register import \
    AccountPaymentRegister

from odoo.exceptions import UserError

def _create_payment_vals_from_batch(self, batch_result):
    batch_values = self._get_wizard_values_from_batch(batch_result)

    if batch_values['payment_type'] == 'inbound':
        partner_bank_id = self.journal_id.bank_account_id.id
    else:
        # partner_bank_id = batch_result['payment_values']['partner_bank_id']
        if batch_result['payment_values']['partner_bank_id']:
            partner_bank_id = batch_result['payment_values']['partner_bank_id']
        elif batch_result['payment_values']['partner_id']:
            partner_id = self.env['res.partner'].browse(
                batch_result['payment_values']['partner_id'])

            bank_ids = partner_id.bank_ids \
                .filtered(lambda x: x.company_id.id in (
                False, batch_result['move_id'].company_id.id if batch_result.get('move_id') else False))._origin
            if bank_ids:
                bankid = bank_ids[:1]
                partner_bank_id = bankid.id
            else:
                partner_bank_id = False
        else:
            partner_bank_id = False

    payment_method_line = self.payment_method_line_id

    if batch_values['payment_type'] != payment_method_line.payment_type:
        payment_method_line = self.journal_id._get_available_payment_method_lines(
            batch_values['payment_type'])[:1]
    tasc_ref = ''
    if not batch_result.get("tasc_reference"):
        move = batch_result["lines"].mapped('move_id')
        tasc_ref = set(filter(None, move.mapped('reference')))
        if tasc_ref:
            tasc_ref = ', '.join(tasc_ref)
        else:
            tasc_ref = ''
    payment_vals = {
        'date': self.payment_date,
        'amount': batch_values['source_amount_currency'],
        'payment_type': batch_values['payment_type'],
        'partner_type': batch_values['partner_type'],
        'ref': self._get_batch_communication(batch_result),
        'journal_id': self.journal_id.id,
        'company_id': self.company_id.id,
        'currency_id': batch_values['source_currency_id'],
        'partner_id': batch_values['partner_id'],
        'partner_bank_id': partner_bank_id,
        'payment_method_line_id': payment_method_line.id,
        'destination_account_id': batch_result['lines'][0].account_id.id,
        'write_off_line_vals': [],
        'purpose_code_id': self.purpose_code_id.id,
        'tasc_reference': batch_result["tasc_reference"] if batch_result.get("tasc_reference") else tasc_ref,
    }

    total_amount, mode = self._get_total_amount_using_same_currency(
        batch_result)
    currency = self.env['res.currency'].browse(
        batch_values['source_currency_id'])
    if mode == 'early_payment':
        payment_vals['amount'] = total_amount

        epd_aml_values_list = []
        for aml in batch_result['lines']:
            if aml.move_id._is_eligible_for_early_payment_discount(currency,
                                                                   self.payment_date):
                epd_aml_values_list.append({
                    'aml': aml,
                    'amount_currency': -aml.amount_residual_currency,
                    'balance': currency._convert(
                        -aml.amount_residual_currency,
                        aml.company_currency_id, self.company_id,
                        self.payment_date),
                })

        open_amount_currency = (batch_values[
                                    'source_amount_currency'] - total_amount) * (
                                   -1 if batch_values[
                                             'payment_type'] == 'outbound' else 1)
        open_balance = currency._convert(open_amount_currency,
                                         aml.company_currency_id,
                                         self.company_id, self.payment_date)
        early_payment_values = self.env['account.move'] \
            ._get_invoice_counterpart_amls_for_early_payment_discount(
            epd_aml_values_list, open_balance)
        for aml_values_list in early_payment_values.values():
            payment_vals['write_off_line_vals'] += aml_values_list

    return payment_vals


def _create_payments(self):
    self.ensure_one()
    all_batches = self._get_batches()
    batches = []
    # Skip batches that are not valid (bank account not trusted but required)
    for batch in all_batches:
        batch_account = self._get_batch_account(batch)
        if self.require_partner_bank_account and not batch_account.allow_out_payment:
            continue
        batches.append(batch)

    if not batches:
        raise UserError(
            _('To record payments with %s, the recipient bank account must be'
              ' manually validated. You should go on the partner bank account '
              'in order to validate it.',
              self.payment_method_line_id.name))

    first_batch_result = batches[0]
    edit_mode = self.can_edit_wizard and (
            len(first_batch_result['lines']) == 1 or self.group_payment)
    to_process = []
    if edit_mode:
        payment_vals = self._create_payment_vals_from_wizard(first_batch_result)
        to_process.append({
            'create_vals': payment_vals,
            'to_reconcile': first_batch_result['lines'],
            'batch': first_batch_result,
        })
    else:
        # Don't group payments: Create one batch per move.
        if not self.group_payment:
            new_batches = []
            for batch_result in batches:
                for line in batch_result['lines']:
                    new_batches.append({
                        **batch_result,
                        'payment_values': {
                            **batch_result['payment_values'],
                            'payment_type': 'inbound' if line.balance > 0 else 'outbound'
                        },
                        'lines': line,
                        'move_id': line.move_id,
                        'tasc_reference':line.move_id.reference,
                    })
            batches = new_batches

        for batch_result in batches:
            to_process.append({
                'create_vals': self._create_payment_vals_from_batch(
                    batch_result),
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
        default_purpose_code = self.env['default.purpose.code'].search(
            [('company_id', '=', self.env.company.id)])
        if default_purpose_code:
            return default_purpose_code.purpose_code_id.id
        else:
            return False

    purpose_code_id = fields.Many2one('purpose.code', string="Purpose Code",
                                      default=_default_purpose_code_id)
    tasc_reference =  fields. Char(string="Tasc Reference")

    def _create_payment_vals_from_wizard(self, batch_result):
        vals = super()._create_payment_vals_from_wizard(batch_result)
        move = batch_result["lines"].mapped('move_id')
        tasc_ref = set(filter(None, move.mapped('reference')))
        if tasc_ref:
            tasc_ref = ', '.join(tasc_ref)
        else:
            tasc_ref = ''
        vals.update({'purpose_code_id': self.purpose_code_id.id,
                     'tasc_reference':tasc_ref if tasc_ref else '',})
        return vals

    def _create_payment_vals_from_batch(self, batch_result):
        res = super()._create_payment_vals_from_batch(batch_result)
        tasc_ref = ''
        if not batch_result.get("tasc_reference"):
            move = batch_result["lines"].mapped('move_id')
            tasc_ref = set(filter(None, move.mapped('reference')))
            if tasc_ref:
                tasc_ref = ', '.join(tasc_ref)
            else:
                tasc_ref = ''
        res.update({'purpose_code_id': self.purpose_code_id.id,
                    'tasc_reference':batch_result["tasc_reference"] if batch_result.get("tasc_reference") else tasc_ref,})
        return res
