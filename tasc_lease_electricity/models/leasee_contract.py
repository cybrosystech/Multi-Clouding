# -*- coding: utf-8 -*-
import logging
_logger = logging.getLogger(__name__)

from datetime import timedelta
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.safe_eval import dateutil
import dateutil.relativedelta as relativedelta

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
