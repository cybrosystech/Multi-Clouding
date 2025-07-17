# -*- coding: utf-8 -*-
import json
import logging
_logger = logging.getLogger(__name__)

from datetime import timedelta
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.safe_eval import dateutil
import dateutil.relativedelta as relativedelta

BATCH_SIZE = 500  # Adjust as needed


class LeaseeContract(models.Model):
    """Inherit leasee contract to add electricity details"""
    _inherit = 'leasee.contract'

    electricity_amount = fields.Monetary(currency_field='leasee_currency_id')
    electricity_expense_account_id = fields.Many2one('account.account',
                                               string="Electricity Expenses")
    electricity_due_account_id = fields.Many2one('account.account',
                                                     string="Electricity Due From")
    electricity_bool = fields.Boolean(default=False, copy=False)
    electricity_button_bool = fields.Boolean(default=False, copy=False)
    electricity_id = fields.Many2one('leasee.electricity', copy=False)
    pass_through = fields.Boolean()

    @api.onchange('leasee_template_id')
    def onchange_leasee_template_id(self):
        self.update({
            'electricity_expense_account_id': self.leasee_template_id.electricity_expense_account_id.id,
            'electricity_due_account_id': self.leasee_template_id.electricity_due_account_id.id
        })
        super().onchange_leasee_template_id()


    def action_activate(self):
        """Inherit the function to set electricity_button_bool value as True"""
        self.electricity_button_bool = True
        return super(LeaseeContract, self).action_activate()

    def action_electricity(self):
        """Method that creates electricity bills from lease"""
        if (not self.electricity_expense_account_id and not self.electricity_due_account_id) or self.electricity_amount <= 0:
            raise ValidationError(
                _('Please choose the electricity expense account or electricity due from account and electricity amount'))
        lease_electricity_id = self.env['leasee.electricity'].create({
            'leasee_reference': self.name,
            'leasee_contract_id': self.id
        })
        self.electricity_id = lease_electricity_id.id
        instalment_date = []
        invoice_date = False

        for instalment in self.installment_ids:
            if instalment.date not in instalment_date:
                if self.leasor_type == 'single':
                    self.create_electricity_moves(instalment,
                                              lease_electricity_id,
                                              self.electricity_amount,
                                              self.vendor_id,
                                              invoice_date)
                    instalment_date.append(instalment.date)
                else:
                    for leasor in self.multi_leasor_ids:
                        partner = leasor.partner_id
                        leasor_amount = leasor.amount / sum(
                            self.multi_leasor_ids.mapped(
                                'amount')) * self.electricity_amount if leasor.type == 'amount' else leasor.percentage / sum(
                            self.multi_leasor_ids.mapped(
                                'percentage')) * self.electricity_amount
                        self.create_electricity_moves(instalment,
                                                  lease_electricity_id,
                                                  leasor_amount,
                                                  partner, invoice_date)
                        instalment_date.append(instalment.date)
        self.electricity_bool = True
        self.electricity_button_bool = False


    def create_electricity_moves(self, instalment, electricity_id, amount,
                              partner, invoice_date):
        """Method to create electricity moves from lease contract"""
        invoice_lines = [(0, 0, {
            'name': self.name + ' - ' + instalment.date.strftime(
                '%d/%m/%Y'),
            'account_id': self.electricity_expense_account_id.id if not self.pass_through else self.electricity_due_account_id.id,
            'price_unit': amount,
            'quantity': 1,
            'analytic_account_id': self.analytic_account_id.id,
            'project_site_id': self.project_site_id.id,
            'business_unit_id': self.business_unit_id.id,
            'analytic_distribution': self.analytic_distribution,
        })]
        if self.payment_frequency_type == 'years':
            end_date = instalment.date + dateutil.relativedelta.relativedelta(
                years=self.payment_frequency) - dateutil.relativedelta.relativedelta(
                days=1)
        else:
            end_date = instalment.date + dateutil.relativedelta.relativedelta(
                months=self.payment_frequency) - dateutil.relativedelta.relativedelta(
                days=1)

        invoice = self.env['account.move'].create({
            'partner_id': partner.id,
            'move_type': 'in_invoice',
            'currency_id': self.leasee_currency_id.id,
            'ref': self.name + '- EB - ' + instalment.date.strftime(
                '%d/%m/%Y') + ' - ' + end_date.strftime('%d/%m/%Y'),
            'invoice_date': instalment.date,
            'invoice_date_due': instalment.date,
            'invoice_payment_term_id': self.env.ref(
                'account.account_payment_term_immediate').id,
            'invoice_line_ids': invoice_lines,
            'journal_id': self.installment_journal_id.id,
            'lease_electricity_id': electricity_id.id,
            'dimension': 'electricity',
        })

        if self.commencement_date <= invoice.date <= self.inception_date:
            invoice.date = self.inception_date
            invoice.invoice_date_due = self.inception_date
            invoice.auto_post = 'at_date'

        payable_lines = invoice.line_ids.filtered(
            lambda x: x.account_id.internal_group == 'liability')
        payable_lines.write({'account_id': instalment.leasee_contract_id.leasee_template_id.electricity_liability_account_id.id})

    def action_electricity_bills(self):
        """Method to open electricity bills"""
        electricity_id = self.env['leasee.electricity'].search(
            [('leasee_contract_id', '=', self.id)])
        if electricity_id:
            domain = [
                ('lease_electricity_id', 'in', electricity_id.ids),
                ('move_type', 'in', ['in_invoice'])]
            view_tree = {
                'name': _(' Vendor Bills '),
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'account.move',
                'type': 'ir.actions.act_window',
                'domain': domain,
            }
            return view_tree

    def process_termination(self, disposal_date):
        """Override process termination to unlink future electricity moves
        while terminating lease"""
        if self.electricity_id:
            electricity_moves = self.env['account.move'].search(
                [(
                    'lease_electricity_id', '=',
                    self.electricity_id.id),
                    ('date', '>', disposal_date)])
            electricity_moves.filtered(lambda x: x.state != 'draft').button_draft()
            electricity_moves.button_cancel()
        return super(LeaseeContract, self).process_termination(
            disposal_date)


    def action_set_lease_type(self):
        self._process_dimension_batch('leasee_contract_id', 'rent', BATCH_SIZE)
        self._process_dimension_batch('lease_security_advance_id', 'security',
                                      BATCH_SIZE)
        self._process_dimension_batch('lease_electricity_id', 'electricity',
                                      BATCH_SIZE)


    def _process_dimension_batch(self, related_field, dimension_value, batch_size):
        """Method to update security,installment and electricity bills in batches"""
        domain = [
            ('dimension', '=', False),
            (related_field, '!=', False),
            ('move_type', 'in', ['in_invoice', 'in_refund'])
        ]

        moves = self.env['account.move'].search(domain, limit=batch_size)
        _logger.info(f"[Dimension Update] Found {len(moves)} records to update to '{dimension_value}'.")

        for move in moves:
            try:
                with self.env.cr.savepoint():
                    move.dimension = dimension_value
                    if move.state == 'posted' and move.payment_state != 'not_paid':
                        raw_widget = move.invoice_payments_widget
                        if not raw_widget:
                            continue

                        # Step 2: Parse the JSON safely
                        try:
                            widget_data = json.loads(raw_widget)
                        except Exception as e:
                            _logger.warning(
                                f"Failed to parse invoice_payments_widget for move {move.name}: {e}")
                            continue

                        # Step 3: Extract payment IDs
                        payment_ids = set()
                        for section in widget_data.get('content', []):
                            account_payment_id = section.get('account_payment_id')
                            if account_payment_id:
                                payment_ids.add(account_payment_id)

                        if not payment_ids:
                            _logger.info(
                                f"No payment IDs found for move {move.name}")
                            continue

                        # Step 4: Update related payments with the move’s dimension
                        payments = self.env['account.payment'].browse(payment_ids)
                        payments_to_update = payments.filtered(
                            lambda p: not p.dimension)
                        payments_to_update.write({'dimension': move.dimension})

                        _logger.info(
                            f"Updated {len(payments_to_update)} payments for move {move.name} with dimension '{move.dimension}'")
            except Exception as e:
                _logger.warning(f"[Dimension Update] Failed on {move.name or move.id}: {str(e)}")


    def action_update_payable_account(self, batch_size=500):
        _logger.info("Scheduled batch: Updating payable accounts")

        AccountMoveLine = self.env['account.move.line']
        ICP = self.env['ir.config_parameter'].sudo()

        # Get last processed record ID
        last_id = int(ICP.get_param('update_payable_last_id', '0'))

        # Fetch next batch
        lines = AccountMoveLine.search([
            ('id', '>', last_id),
            ('move_id.lease_security_advance_id', '!=', False),
            ('parent_state', '=', 'draft'),
            ('account_id.internal_group', '=', 'liability'),
        ], order='id', limit=batch_size)

        if not lines:
            _logger.info("✅ All records processed. Resetting progress.")
            ICP.set_param('update_payable_last_id', '0')  # Reset for next run
            return

        for line in lines:
            correct_account = line.move_id.lease_security_advance_id.leasee_contract_id.leasee_template_id.security_liability_account_id
            if correct_account and line.account_id != correct_account:
                line.account_id = correct_account.id

        # Save progress
        max_id = max(lines.mapped('id'))
        ICP.set_param('update_payable_last_id', str(max_id))

        _logger.info(f"✅ Processed batch up to line ID {max_id}")
        self._cr.commit()
