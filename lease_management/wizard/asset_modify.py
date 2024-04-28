# -*- coding: utf-8 -*-

from odoo import models, _


class AssetModify(models.TransientModel):
    _inherit = 'asset.modify'

    def modify(self):
        """ Modifies the duration of asset for calculating depreciation
        and maintains the history of old values, in the chatter.
        """
        if self._context.get('extend_leasee_contract'):
            old_values = {
                'method_number': self.asset_id.method_number,
            }

            asset_vals = {}
            if self.env.context.get('resume_after_pause'):
                asset_vals.update({'state': 'open'})
                self.asset_id.message_post(body=_("Asset unpaused"))
            else:
                self = self.with_context(ignore_prorata=True)

            asset_increase = self.env['account.asset'].create({
                'name': self.asset_id.name + ': ' + self.name,
                'currency_id': self.asset_id.currency_id.id,
                'company_id': self.asset_id.company_id.id,
                'method': self.asset_id.method,
                'prorata_computation_type': self.asset_id.prorata_computation_type,
                'prorata_date': self.date if self.asset_id.prorata_computation_type else None,
                'method_number': self.method_number,
                'method_period': self.method_period,
                'acquisition_date': self.date,
                'value_residual': 0,
                'salvage_value': 0,
                'original_value': self.value_residual,
                'account_asset_id': self.account_asset_id.id,
                'account_depreciation_id': self.account_depreciation_id.id,
                'account_depreciation_expense_id': self.account_depreciation_expense_id.id,
                'journal_id': self.asset_id.journal_id.id,
                'analytic_distribution': self.asset_id.analytic_distribution,
            })
            asset_increase.with_context(ignore_prorata=False).validate()
            asset_increase.write({'parent_id': self.asset_id.id})

            return {'type': 'ir.actions.act_window_close'}
        elif self._context.get('reasset_leasee_contract'):
            old_values = {
                'method_number': self.asset_id.method_number,
            }

            asset_vals = {}
            if self.env.context.get('resume_after_pause'):
                asset_vals.update({'state': 'open'})
                self.asset_id.message_post(body=_("Asset unpaused"))
            else:
                self = self.with_context(ignore_prorata=True)
            remaining_installments = self.asset_id.depreciation_move_ids.filtered(
                lambda m: m.date >= self.date)
            asset_increase = self.env['account.asset'].create({
                'name': self.asset_id.name + ': ' + self.name,
                'currency_id': self.asset_id.currency_id.id,
                'company_id': self.asset_id.company_id.id,
                'method': self.asset_id.method,
                'prorata_computation_type': self.asset_id.prorata_computation_type,
                'prorata_date': self.date if self.asset_id.prorata_computation_type else None,
                'method_number': len(remaining_installments) - 1,
                'method_period': self.asset_id.method_period,
                'acquisition_date': self.date,
                'value_residual': 0,
                'salvage_value': 0,
                'original_value': self.value_residual,
                'account_asset_id': self.account_asset_id.id,
                'account_depreciation_id': self.account_depreciation_id.id,
                'account_depreciation_expense_id': self.account_depreciation_expense_id.id,
                'journal_id': self.asset_id.journal_id.id,
                'analytic_distribution': self.asset_id.analytic_distribution,
            })
            asset_increase.with_context(
                decrease=True if self.value_residual < 0 else False,
                ignore_prorata=False).validate()
            asset_increase.write({'parent_id': self.asset_id.id})

            return {'type': 'ir.actions.act_window_close'}
        else:
            return super(AssetModify, self).modify()
