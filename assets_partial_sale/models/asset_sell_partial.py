from odoo import models, fields, _
from odoo.exceptions import ValidationError


class AssetSellPartial(models.TransientModel):
    _inherit = 'account.asset.sell'

    partial_bool = fields.Boolean('Partial')
    partial_amount = fields.Float('amount')

    def do_action(self):
        self.ensure_one()
        invoice_line = self.env[
            'account.move.line'] if self.action == 'dispose' else self.invoice_line_id or self.invoice_id.invoice_line_ids
        if self._context['active_model'] == 'leasee.contract':
            leasee_contract = self.env['leasee.contract'].browse(
                int(self._context['active_id']))
            leasee_contract.termination_date = self.contract_end_date
        date = invoice_line.move_id.invoice_date
        if self.action == 'dispose':
            date = self.contract_end_date
        return self.asset_id.set_to_close(invoice_line_id=invoice_line,
                                          partial=self.partial_bool,
                                          partial_amount=self.partial_amount,
                                          date=date)
