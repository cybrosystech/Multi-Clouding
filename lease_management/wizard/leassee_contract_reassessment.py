# -*- coding: utf-8 -*-
""" init object """
from odoo import fields, models, api, _

import logging

LOGGER = logging.getLogger(__name__)


class Reassessment(models.TransientModel):
    _name = 'leasee.contract.reassessment'
    _description = 'Leasee Contract Reassessment'

    reassessment_start_Date = fields.Date(default=lambda self: fields.Date.today(), required=True, )
    leasee_contract_id = fields.Many2one(comodel_name="leasee.contract", string="", required=False,ondelete='cascade' )
    new_installment_amount = fields.Float(string="", default=0.0, required=True, )

    @api.model
    def default_get(self, fields):
        res = super(Reassessment, self).default_get(fields)
        leasee_contract_id = self.env.context.get('active_id')
        leasee_contract = self.env['leasee.contract'].browse(leasee_contract_id)
        res['leasee_contract_id'] = leasee_contract_id
        res['new_installment_amount'] = leasee_contract.installment_amount
        return res

    # @api.constrains('new_installment_amount', 'leasee_contract_id', 'reassessment_start_Date')
    # def check_new_installment(self):
    #     pass

    def action_apply(self):
        contract = self.leasee_contract_id
        old_lease_liability = contract.lease_liability
        old_rou_value = contract.rou_value
        self.env['leasee.reassessment.increase'].create({
            'leasee_contract_id': self.leasee_contract_id.id,
            'installment_amount': self.new_installment_amount,
            'installment_date': self.reassessment_start_Date,
        })

        installments_to_modify = self.env['leasee.installment'].search([
            ('leasee_contract_id', '=', self.leasee_contract_id.id),
            ('date', '>=', self.reassessment_start_Date),
        ])
        old_installments = contract.installment_ids[1:] - installments_to_modify

        diff_installments = []
        installment_amount = self.new_installment_amount
        for i, installment in enumerate(installments_to_modify):
            installment.amount = installment_amount
            diff = installment_amount - installment.amount
            diff_installments.append(diff)
            installment_amount = self.leasee_contract_id.get_future_value(installment_amount, contract.increasement_rate, 1)

        new_rou = contract.rou_value - old_rou_value
        self.create_reassessment_move(contract, new_rou)

        # prev_installment_amount = contract.lease_liability
        remaining_liability = contract.lease_liability
        for i, ins in enumerate(old_installments):
            if i ==0 and contract.payment_method == 'beginning':
                interest_factor = 1
            else:
                interest_factor = (1 + contract.interest_rate/ 100)
            remaining_liability = interest_factor * remaining_liability - ins.amount
            # prev_installment_amount =

        for installment in installments_to_modify:
            # if not prev_installment_amount:
            #     installment.subsequent_amount = installment.subsequent_amount - (diff - new_rou * contract.interest_rate) / 100
            #     # remaining_liability = installment.subsequent_amount / (contract.interest_rate / 100 )
            #     installment.remaining_lease_liability = remaining_liability
            # else:
                # installment.subsequent_amount = remaining_liability * contract.interest_rate / 100
            installment.subsequent_amount = remaining_liability * contract.interest_rate / 100
            remaining_liability = remaining_liability * (1 + contract.interest_rate / 100 ) - installment.amount
            installment.remaining_lease_liability = round(remaining_liability, 2)
            # if not contract.interest_rate:
            #     installment.remaining_lease_liability += diff
            # prev_installment_amount = installment.amount

        self.update_asset_value(contract.rou_value - old_rou_value)
        self.update_related_journal_items(installments_to_modify)

    def create_reassessment_move(self, contract, amount):
        rou_account = contract.asset_model_id.account_asset_id
        lines = [(0, 0, {
            'name': 'Reassessment contract number %s' % contract.name,
            'account_id': rou_account.id,
            'credit': 0,
            'debit': amount,
            'analytic_account_id': contract.analytic_account_id.id,
            'project_site_id': contract.project_site_id.id,
            'type_id': contract.type_id.id,
            'location_id': contract.location_id.id,
        }),(0, 0, {
            'name': 'Reassessment contract number %s' % contract.name,
            'account_id': contract.lease_liability_account_id.id,
            'debit': 0,
            'credit': amount,
            'analytic_account_id': contract.analytic_account_id.id,
            'project_site_id': contract.project_site_id.id,
            'type_id': contract.type_id.id,
            'location_id': contract.location_id.id,
        })]
        move = self.env['account.move'].create({
            'partner_id': contract.vendor_id.id,
            'move_type': 'entry',
            'currency_id': contract.leasee_currency_id.id,
            'ref': contract.name,
            'date': self.reassessment_start_Date,
            'journal_id': contract.asset_model_id.journal_id.id,
            'leasee_contract_id': contract.id,
            'line_ids': lines,
            'auto_post': True,
        })

    def update_asset_value(self, new_value):
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
        delta = contract.payment_frequency * (1 if contract.payment_frequency_type == 'months' else 12)
        for ins in installments_to_modify:
            invoice = ins.installment_invoice_id
            inv_state = invoice.state
            if invoice:
                if inv_state == 'posted':
                    invoice.button_draft()

                invoice_line = invoice.invoice_line_ids
                new_invoice = invoice.new(invoice._convert_to_write(invoice._cache))
                line_values = {
                    'product_id': invoice_line.product_id.id,
                    'account_id': invoice_line.account_id.id,
                    'analytic_account_id': invoice_line.analytic_account_id.id,
                    'project_site_id': invoice_line.project_site_id.id,
                    'type_id': invoice_line.type_id.id,
                    'location_id': invoice_line.location_id.id,
                    'tax_ids': [(4, tax_id) for tax_id in invoice_line.tax_ids.ids],
                }
                new_invoice.invoice_line_ids = [(5,),(0 , 0, line_values)]
                new_invoice.invoice_line_ids.update({'price_unit': ins.amount})
                new_invoice.invoice_line_ids._onchange_price_subtotal()

                new_invoice._compute_invoice_taxes_by_group()
                new_invoice._onchange_invoice_line_ids()
                new_invoice._compute_amount()
                values = new_invoice._convert_to_write(new_invoice._cache)
                invoice.write({'line_ids': values.get('line_ids')})

                if inv_state == 'posted':
                    invoice.action_post()

            for move in ins.interest_move_ids:
                interest_amount = ins.subsequent_amount / delta
                move_state = move.state

                if move_state == 'posted':
                    move.button_draft()

                debit_line = move.line_ids.filtered(lambda l: l.debit > 0)
                credit_line = move.line_ids.filtered(lambda l: l.credit > 0)
                move.write({'line_ids': [(1, debit_line.id, {'debit': interest_amount}), (1, credit_line.id, {'credit': interest_amount})]})

                if move_state == 'posted':
                    move.action_post()

















