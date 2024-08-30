# -*- coding: utf-8 -*-
""" init object """
import datetime

from odoo import fields, models, api, _
from dateutil.relativedelta import relativedelta
import logging

LOGGER = logging.getLogger(__name__)


class Reassessment(models.TransientModel):
    _name = 'leasee.contract.reassessment'
    _description = 'Leasee Contract Reassessment'

    reassessment_start_Date = fields.Date(default=lambda self: fields.Date.today(), required=True, )
    leasee_contract_id = fields.Many2one(comodel_name="leasee.contract", string="", required=False, ondelete='cascade')
    new_installment_amount = fields.Float(string="", default=0.0, required=True, )

    @api.model
    def default_get(self, fields):
        res = super(Reassessment, self).default_get(fields)
        leasee_contract_id = self.env.context.get('active_id')
        leasee_contract = self.env['leasee.contract'].browse(leasee_contract_id)
        res['leasee_contract_id'] = leasee_contract_id
        res['new_installment_amount'] = leasee_contract.installment_amount
        return res

    def action_apply(self, reassessment=None):
        journal_update_date = ''
        subsequent_amount_data = 0
        contract = self.leasee_contract_id
        self.env['leasee.reassessment.increase'].create({
            'leasee_contract_id': contract.id,
            'installment_amount': self.new_installment_amount,
            'installment_date': self.reassessment_start_Date,
        })
        reassessment_installments = contract.installment_ids.filtered(lambda i: i.date >= self.reassessment_start_Date)
        first_installment = reassessment_installments[0]
        before_first = contract.installment_ids.filtered(
            lambda i: i.get_period_order() == (first_installment.get_period_order() - 1))
        days_before_reassessment = (self.reassessment_start_Date - before_first.date).days
        days_after_reassessment = (first_installment.date - self.reassessment_start_Date).days
        old_amount = first_installment.amount
        old_subsequent = first_installment.subsequent_amount
        days = (first_installment.date - before_first.date).days
        old_remaining_liability = before_first.remaining_lease_liability + old_subsequent * days_before_reassessment / days
        remaining_lease_liability_before = self.get_before_remaining_lease(reassessment_installments,
                                                                           days_before_reassessment, days)
        installment_amount = self.new_installment_amount
        for i, installment in enumerate(reassessment_installments):
            installment.amount = installment_amount
            installment_amount = contract.get_future_value(
                installment_amount,
                0, 1, 0, 0)
        start = 1 if contract.payment_method == 'end' else 0
        new_lease_liability = sum([contract.get_present_value_modified(installment.amount, contract.interest_rate,
                                                                       i + start, self.reassessment_start_Date,
                                                                       installment.date) for i, installment in
                                   enumerate(reassessment_installments)])
        period_ratio = ((
                                first_installment.date - self.reassessment_start_Date).days) / 365
        interest_recognition = new_lease_liability * (
                (1 + contract.interest_rate / 100) ** period_ratio - 1)
        remaining_liability = new_lease_liability - (
                first_installment.amount - interest_recognition)
        if self.reassessment_start_Date.month == contract.inception_date.month:
            journal_update_date = datetime.date(
                self.reassessment_start_Date.year,
                contract.inception_date.month,
                contract.inception_date.day)
            if first_installment.date == journal_update_date:
                subsequent_amount_data = interest_recognition

        first_installment.write({
            'remaining_lease_liability': new_lease_liability,
            'subsequent_amount': interest_recognition,
        })
        prev_install = first_installment
        for i, installment in enumerate(reassessment_installments[1:]):
            period_ratio = ((installment.date - prev_install.date).days) / 365
            interest_recognition = remaining_liability * ((1 + contract.interest_rate / 100) ** period_ratio - 1)
            remaining_liability -= (installment.amount - interest_recognition)
            installment.subsequent_amount = interest_recognition
            installment.remaining_lease_liability = remaining_liability
            prev_install = installment
        self.create_reassessment_move(contract, new_lease_liability - old_remaining_liability)
        self.update_asset_value(new_lease_liability - old_remaining_liability)
        self.update_related_journal_items(reassessment_installments)
        if first_installment.date != self.reassessment_start_Date:
            self.update_first_installment_entries(first_installment,
                                                  old_subsequent,
                                                  days_after_reassessment, days,
                                                  subsequent_amount_data)
        remaining_lease_liability_after = self.get_after_remaining_lease(
            reassessment_installments)
        stl_amount = remaining_lease_liability_after - remaining_lease_liability_before
        self.create_installment_entry(contract, stl_amount)
        body = self.env.user.name + _(' reassess the contract to ') + str(
            self.new_installment_amount) + ' starting from ' + self.reassessment_start_Date.strftime('%d/%m/%Y') + ' .'
        contract.message_post(body=body)

    def create_reassessment_move(self, contract, amount):
        rou_account = contract.asset_model_id.account_asset_id
        if amount:
            base_amount = amount

            if contract.leasee_currency_id != contract.company_id.currency_id:
                amount = contract.leasee_currency_id._convert(amount, contract.company_id.currency_id, contract.company_id, self.reassessment_start_Date)
            move = self.env['account.move'].create({
                'partner_id': contract.vendor_id.id,
                'move_type': 'entry',
                'currency_id': contract.leasee_currency_id.id,
                'ref': contract.name,
                'date': self.reassessment_start_Date,
                'journal_id': contract.asset_model_id.journal_id.id,
                'leasee_contract_id': contract.id,
                'auto_post': 'at_date',
            })
            move.line_ids = [(0, 0, {
                'name': 'Reassessment contract number %s' % contract.name,
                'account_id': rou_account.id,
                'credit': -amount if amount < 0 else 0,
                'debit': amount if amount > 0 else 0,
                'move_id': move.id,
                'analytic_account_id': contract.analytic_account_id.id,
                'project_site_id': contract.project_site_id.id,
                'analytic_distribution': contract.analytic_distribution,
                'currency_id': contract.leasee_currency_id.id
            }), (0, 0, {
                'name': 'Reassessment contract number %s' % contract.name,
                'account_id': contract.long_lease_liability_account_id.id,
                'debit': -amount if amount < 0 else 0,
                'credit': amount if amount > 0 else 0,
                'move_id': move.id,
                'analytic_account_id': contract.analytic_account_id.id,
                'project_site_id': contract.project_site_id.id,
                'analytic_distribution': contract.analytic_distribution,
                'currency_id': contract.leasee_currency_id.id
            })]
            if contract.leasee_currency_id != contract.company_id.currency_id:
                test_amount_c = move.line_ids.filtered(lambda x: x.credit > 0)
                test_amount_c.amount_currency = test_amount_c.amount_currency * -1

    def update_asset_value(self, new_value):
        print("update_asset_value")
        asset = self.leasee_contract_id.asset_id
        self.env['asset.modify'].create({
            'name': "Reassessment Leasee Contract",
            'date': self.reassessment_start_Date,
            'asset_id': asset.id,
            'value_residual': new_value,
            'salvage_value': asset.salvage_value,
            "account_asset_counterpart_id": self.leasee_contract_id.lease_liability_account_id.id,
        }).with_context(reasset_leasee_contract=True).modify()

    def update_related_journal_items(self, installments_to_modify):
        contract = self.leasee_contract_id
        for i, ins in enumerate(installments_to_modify):
            if contract.leasor_type == 'single':
                self.update_invoice_amount(ins.installment_invoice_id, ins.amount)
            else:
                for ml in contract.multi_leasor_ids:
                    invoice = contract.account_move_ids.filtered(lambda
                                                                     inv: inv.move_type == 'in_invoice' and ml.partner_id == inv.partner_id and ins.date == inv.date)
                    amount = (
                                         ml.amount / contract.installment_amount) * ins.amount if ml.type == 'amount' else ml.percentage * ins.amount / 100
                    if invoice:
                        self.update_invoice_amount(invoice, amount)
            if i:
                # delay = ins.interest_move_ids.sudo().with_delay(priority=1, eta=5)
                # delay.with_context(force_delete=True).unlink()
                ins.interest_move_ids.sudo().unlink()
        contract.create_contract_installment_entries(installments_to_modify[1].date)
        contract.leasee_action_generate_interest_entries_reassessment(installments_to_modify[1].date)

    def update_invoice_amount(self, invoice, new_amount):
        if invoice:
            inv_state = invoice.state
            if inv_state == 'posted':
                invoice.button_draft()

            invoice_line = invoice.invoice_line_ids
            line_values = {
                'product_id': invoice_line.product_id.id,
                'currency_id': invoice_line.currency_id.id,
                'account_id': invoice_line.account_id.id,
                'analytic_account_id': invoice_line.analytic_account_id.id,
                'project_site_id': invoice_line.project_site_id.id,
                # 'type_id': invoice_line.type_id.id,
                # 'location_id': invoice_line.location_id.id,
                'analytic_distribution':invoice_line.analytic_distribution,
                'tax_ids': [(4, tax_id) for tax_id in invoice_line.tax_ids.ids],
                'price_unit': new_amount
            }
            invoice.invoice_line_ids = [(5,), (0, 0, line_values)]
            if inv_state == 'posted':
                invoice.action_post()

    def update_first_installment_entries(self, first_installment,
                                         old_subsequent,
                                         days_after_reassessment, days,
                                         subsequent_amount_data):
        contract = first_installment.leasee_contract_id
        interest_move_accounts = [contract.interest_expense_account_id.id, contract.lease_liability_account_id.id]
        beginning_entries = first_installment.interest_move_ids.filtered(lambda
                                                                             m: m.date.month == self.reassessment_start_Date.month and m.date.year == self.reassessment_start_Date.year)
        after_reassessment_moves = first_installment.interest_move_ids.filtered(
            lambda m: m.date > self.reassessment_start_Date and set(m.line_ids.mapped('account_id').ids) == set(
                interest_move_accounts))
        beginning_interest_move = beginning_entries.filtered(
            lambda m: set(m.line_ids.mapped('account_id').ids) == set(interest_move_accounts))
        if beginning_interest_move:
            after_reassessment_moves -= beginning_interest_move
            debit_line = beginning_interest_move.line_ids.filtered(lambda l: l.debit > 0)
            credit_line = beginning_interest_move.line_ids.filtered(lambda l: l.credit > 0)
            start_month = beginning_interest_move.date.replace(day=1)
            end_month = start_month + relativedelta(months=1, days=-1)
            prev_start = start_month
            prev_installment = self.leasee_contract_id.installment_ids.filtered(
                lambda i: i.get_period_order() == first_installment.get_period_order() - 1)
            if prev_installment.date.month == self.reassessment_start_Date.month and prev_installment.date.year == self.reassessment_start_Date.year:
                prev_start = prev_installment.date
            interest_amount = old_subsequent * (
                    self.reassessment_start_Date - prev_start).days / days + first_installment.subsequent_amount * (
                                      (
                                              end_month - self.reassessment_start_Date).days + 1) / days_after_reassessment
            if subsequent_amount_data != 0:
                subsequent_amount_base = subsequent_amount_data
                if beginning_interest_move.currency_id != self.env.company.currency_id:
                    subsequent_amount_data = beginning_interest_move.currency_id._convert(subsequent_amount_data,
                                                          self.env.company.currency_id,
                                                          self.env.company,
                                                          beginning_interest_move.date)
                beginning_interest_move.write(
                    {'line_ids': [
                        (1, debit_line.id, {'debit': subsequent_amount_data,
                                            'amount_currency': subsequent_amount_base}),
                        (
                            1, credit_line.id, {'credit': subsequent_amount_data,
                                                'amount_currency': -subsequent_amount_base})]})
            else:
                beginning_interest_base = interest_amount
                if beginning_interest_move.currency_id != self.env.company.currency_id:
                    interest_amount = beginning_interest_move.currency_id._convert(
                        interest_amount,
                        self.env.company.currency_id,
                        self.env.company,
                        beginning_interest_move.date)
                beginning_interest_move.write(
                    {'line_ids': [
                        (1, debit_line.id, {'debit': interest_amount,
                                            'amount_currency': beginning_interest_base}),
                        (
                            1, credit_line.id, {'credit': interest_amount,
                                                'amount_currency': -beginning_interest_base})]})
        for move in after_reassessment_moves:
            debit_line = move.line_ids.filtered(lambda l: l.debit > 0)
            credit_line = move.line_ids.filtered(lambda l: l.credit > 0)
            start_month = move.date.replace(day=1)
            end_month = start_month + relativedelta(months=1, days=-1)
            if first_installment.date.month == move.date.month and first_installment.date.year == move.date.year:
                interest_amount = first_installment.subsequent_amount * (
                            first_installment.date - start_month).days / days_after_reassessment
            else:
                interest_amount = first_installment.subsequent_amount * (
                            (end_month - start_month).days + 1) / days_after_reassessment
            after_reassessment_base = interest_amount
            if move.currency_id != self.env.company.currency_id:
                interest_amount = move.currency_id._convert(
                    interest_amount,
                    self.env.company.currency_id,
                    self.env.company,
                    move.date)
            move.write({'line_ids': [(1, debit_line.id, {'debit': interest_amount,
                                                         'amount_currency': after_reassessment_base
                                                         }),
                                     (1, credit_line.id, {'credit': interest_amount,
                                                          'amount_currency': -after_reassessment_base
                                                          })]})
        lease_liability_accounts = [contract.long_lease_liability_account_id.id, contract.lease_liability_account_id.id]
        amount = self.get_installment_entry_amount(first_installment)
        if amount:
            installment_entry = first_installment.interest_move_ids.filtered(
                lambda m: set(m.line_ids.mapped('account_id').ids) == set(lease_liability_accounts))
            debit_line = installment_entry.line_ids.filtered(lambda l: l.debit > 0)
            credit_line = installment_entry.line_ids.filtered(lambda l: l.credit > 0)
            installment_entry_base = amount
            if installment_entry.currency_id != self.env.company.currency_id:
                amount = installment_entry.currency_id._convert(
                    amount,
                    self.env.company.currency_id,
                    self.env.company,
                    installment_entry.date)
            installment_entry.write(
                {'line_ids': [(1, debit_line.id, {'debit': amount,
                                                  'amount_currency': installment_entry_base}),
                              (1, credit_line.id, {'credit': amount,
                                                   'amount_currency': -installment_entry_base})]})

    def get_installment_entry_amount(self, installment):
        contract = self.leasee_contract_id
        installments_count = len(contract.installment_ids) - 1
        if not contract.is_contract_not_annual():
            if contract.payment_method == 'beginning':
                amount = contract.get_installment_entry_amount(installment)
            else:
                period = installment.get_period_order()
                current_installment = contract.installment_ids.filtered(
                    lambda i: i.get_period_order() <= installments_count and i.get_period_order() == (period + 1))
                if current_installment:
                    amount = contract.get_installment_entry_amount(current_installment)
                else:
                    amount = 0
        else:
            installments_per_year = contract.get_installments_per_year()
            if contract.payment_method == 'beginning':
                period = installment.get_period_order()
                current_installment = installment
                if current_installment:
                    amount = contract.get_installment_entry_amount(current_installment)
                else:
                    amount = 0
            else:
                period = installment.get_period_order()
                current_installment = contract.installment_ids.filtered(
                    lambda i: i.get_period_order() <= installments_count and i.get_period_order() == (
                                period + installments_per_year))
                if current_installment:
                    amount = contract.get_installment_entry_amount(current_installment)
                else:
                    amount = 0

        return amount

    def create_installment_entry(self, contract, stl_amount):
        amount = stl_amount
        if round(abs(amount), 3) > 0:
            amount_base = amount
            if contract.leasee_currency_id != contract.company_id.currency_id:
                amount = contract.leasee_currency_id._convert(amount,
                                                          contract.company_id.currency_id,
                                                          contract.company_id,
                                                          self.reassessment_start_Date)
            move = self.env['account.move'].create({
                'move_type': 'entry',
                'currency_id': contract.leasee_currency_id.id,
                'ref': 'Reassessment Installment Entry',
                'date': self.reassessment_start_Date,
                'journal_id': contract.initial_journal_id.id,
                'leasee_contract_id': contract.id,
                'auto_post': 'at_date',
            })
            move.line_ids =[(0, 0, {
                'name': 'Reassessment Installment Entry',
                'account_id': contract.long_lease_liability_account_id.id or contract.leasee_template_id.long_lease_liability_account_id.id,
                'debit': amount if amount > 0 else 0,
                'credit': -amount if amount < 0 else 0,
                'move_id': move.id,
                'analytic_account_id': contract.analytic_account_id.id,
                'project_site_id': contract.project_site_id.id,
                'analytic_distribution': contract.analytic_distribution,
                'currency_id': contract.leasee_currency_id.id
            }),
                     (0, 0, {
                         'name': 'Reassessment Installment Entry',
                         'account_id': contract.lease_liability_account_id.id,
                         'credit': amount if amount > 0 else 0,
                         'debit': -amount if amount < 0 else 0,
                         'move_id': move.id,
                         'analytic_account_id': contract.analytic_account_id.id,
                         'project_site_id': contract.project_site_id.id,
                         'analytic_distribution':contract.analytic_distribution,
                         'currency_id': contract.leasee_currency_id.id
                     })]
            if contract.leasee_currency_id != contract.company_id.currency_id:
                test_amount_c = move.line_ids.filtered(lambda x: x.credit > 0)
                test_amount_c.amount_currency = test_amount_c.amount_currency * -1

    def get_before_remaining_lease(self, reassessment_installments, days_before_reassessment, days):
        contract = self.leasee_contract_id
        first_installment = reassessment_installments[0]
        if contract.is_contract_not_annual():
            num_installments = contract.get_installments_per_year()
            lease_liability = first_installment.subsequent_amount / days * days_before_reassessment
            for ins in reassessment_installments[:num_installments]:
                lease_liability += ins.amount - ins.subsequent_amount
        else:
            lease_liability = first_installment.amount - first_installment.subsequent_amount + first_installment.subsequent_amount / days * days_before_reassessment
        return lease_liability

    def get_after_remaining_lease(self, reassessment_installments):
        contract = self.leasee_contract_id
        if contract.is_contract_not_annual():
            num_installments = contract.get_installments_per_year()
            lease_liability = 0
            for ins in reassessment_installments[:num_installments]:
                lease_liability += ins.amount - ins.subsequent_amount
        else:
            first_installment = reassessment_installments[0]
            lease_liability = first_installment.amount - first_installment.subsequent_amount
        return lease_liability

