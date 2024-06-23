from odoo import fields, models, api, _
from odoo.exceptions import UserError



class AssetBulkWizard(models.TransientModel):
    _name = 'asset.bulk.wizard'

    asset_sell_disposal_ids = fields.One2many('asset.sell.disposal.lines', 'asset_bulk_wizard_id')

    def action_apply(self):
        for record in self.asset_sell_disposal_ids:
            if record.asset_id.leasee_contract_ids:
                if not record.contract_end_date:
                    raise UserError('Please provide contract end date '+str(record.asset_id.name))
            # else:
            #     if not record.invoice_id:
            #         raise UserError('Please choose a invoice '+str(record.asset_id.name))

            record.ensure_one()
            invoice_line = self.env[
                'account.move.line'] if record.action == 'dispose' else record.invoice_line_id or record.invoice_id.invoice_line_ids
            date = invoice_line.move_id.invoice_date
            if record.action == 'dispose':
                date = record.contract_end_date
            record.asset_id.set_to_close_bulk(
                invoice_line_ids=invoice_line if record.invoice_line_id or record.action == 'dispose' else record.invoice_id,
                partial=record.partial_bool,
                partial_amount=record.partial_amount,
                date=date)


class AssetSellDisposalLines(models.TransientModel):
    _name = 'asset.sell.disposal.lines'

    asset_bulk_wizard_id = fields.Many2one('asset.bulk.wizard')

    asset_id = fields.Many2one('account.asset', required=True)
    company_id = fields.Many2one('res.company',
                                 default=lambda self: self.env.company)

    action = fields.Selection([('sell', 'Sell'), ('dispose', 'Dispose')],
                              required=True, default='sell')
    partial_bool = fields.Boolean('Partial')
    partial_amount = fields.Float('amount')
    invoice_id = fields.Many2one('account.move', string="Customer Invoice",
                                 help="The disposal invoice is needed in order to generate the closing journal entry.",
                                 domain="[('move_type', 'in', ['out_invoice','in_refund']), ('state', '=', 'posted')]")
    invoice_line_id = fields.Many2one('account.move.line',
                                      help="There are multiple lines that could be the related to this asset",
                                      domain="[('move_id', '=', invoice_id)]")
    select_invoice_line_id = fields.Boolean(
        compute="_compute_select_invoice_line_id")
    gain_account_id = fields.Many2one('account.account',
                                      domain="[('deprecated', '=', False), ('company_id', '=', company_id)]",
                                    compute='_compute_accounts',inverse='_inverse_gain_account',
                                      help="Account used to write the journal item in case of gain",
                                      readonly=False)
    loss_account_id = fields.Many2one('account.account',
                                      domain="[('deprecated', '=', False), ('company_id', '=', company_id)]",
                                      compute='_compute_accounts',
                                      inverse='_inverse_loss_account',
                                      help="Account used to write the journal item in case of loss",
                                      readonly=False)

    gain_or_loss = fields.Selection(
        [('gain', 'Gain'), ('loss', 'Loss'), ('no', 'No')],
        compute='_compute_gain_or_loss',
        help="Technical field to know is there was a gain or a loss in the selling of the asset")
    from_leasee_contract = fields.Boolean(default=False)
    contract_end_date = fields.Date(required=False, )

    @api.depends('company_id')
    def _compute_accounts(self):
        for record in self:
            record.gain_account_id = record.company_id.gain_account_id
            record.loss_account_id = record.company_id.loss_account_id

    def _inverse_gain_account(self):
        for record in self:
            record.company_id.sudo().gain_account_id = record.gain_account_id

    def _inverse_loss_account(self):
        for record in self:
            record.company_id.sudo().loss_account_id = record.loss_account_id

    @api.depends('invoice_id', 'action')
    def _compute_select_invoice_line_id(self):
        for record in self:
            record.select_invoice_line_id = record.action == 'sell' and len(
                record.invoice_id.invoice_line_ids) > 1

    @api.onchange('action')
    def _onchange_action(self):
        if self.action == 'sell' and self.asset_id.children_ids.filtered(
                lambda a: a.state in ('draft', 'open') or a.value_residual > 0):
            raise UserError(
                _("You cannot automate the journal entry for an asset that has a running gross increase. Please use 'Dispose' on the increase(s)."))

    @api.depends('asset_id', 'invoice_id', 'invoice_line_id')
    def _compute_gain_or_loss(self):
        for record in self:
            line = record.invoice_line_id or len(
                record.invoice_id.invoice_line_ids) == 1 and record.invoice_id.invoice_line_ids or \
                   self.env['account.move.line']
            if record.asset_id.value_residual < abs(line.balance):
                record.gain_or_loss = 'gain'
            elif record.asset_id.value_residual > abs(line.balance):
                record.gain_or_loss = 'loss'
            else:
                record.gain_or_loss = 'no'
