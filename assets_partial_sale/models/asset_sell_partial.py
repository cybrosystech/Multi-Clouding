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
        return self.asset_id.set_to_close(invoice_line_id=invoice_line,
                                          partial=self.partial_bool,
                                          partial_amount=self.partial_amount,
                                          date=invoice_line.move_id.invoice_date)
