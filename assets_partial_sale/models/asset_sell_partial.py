from odoo import models, fields, _
from odoo.exceptions import UserError


class AssetModify(models.TransientModel):
    _inherit = 'asset.modify'

    partial_bool = fields.Boolean('Partial')
    partial_amount = fields.Float('amount')
    invoice_ids = fields.Many2many(
        comodel_name='account.move',
        string="Customer Invoice",
        check_company=True,
        domain="[('move_type', 'in', ['out_invoice','in_refund']), ('state', '=', 'posted')]",
        help="The disposal invoice is needed in order to generate the closing journal entry.",
    )

    def sell_dispose(self):
        self.ensure_one()
        if self.gain_account_id == self.asset_id.account_depreciation_id or self.loss_account_id == self.asset_id.account_depreciation_id:
            raise UserError(
                _("You cannot select the same account as the Depreciation Account"))
        invoice_lines = self.env[
            'account.move.line'] if self.modify_action == 'dispose' else self.invoice_line_ids or self.invoice_id.invoice_line_ids
        if self._context['active_model'] == 'leasee.contract':
            leasee_contract = self.env['leasee.contract'].browse(
                int(self._context['active_id']))
            leasee_contract.termination_date = self.date
        date = invoice_lines.move_id.invoice_date
        if self.modify_action == 'dispose':
            date = self.date
        return self.asset_id.set_to_close(
            invoice_line_ids=invoice_lines if self.invoice_line_ids or self.modify_action == 'dispose' else self.invoice_ids,
            partial=self.partial_bool,
            partial_amount=self.partial_amount,
            date=date)
