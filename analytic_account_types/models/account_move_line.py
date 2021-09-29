# -*- coding: utf-8 -*-

import math
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_round
from odoo.tools.misc import formatLang
from dateutil.relativedelta import relativedelta


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _auto_create_asset(self):
        create_list = []
        invoice_list = []
        auto_validate = []
        for move in self:
            if not move.is_invoice():
                continue

            for move_line in move.line_ids.filtered(lambda line: not (move.move_type in (
            'out_invoice', 'out_refund') and line.account_id.user_type_id.internal_group == 'asset')):
                if (
                        move_line.account_id
                        and (move_line.account_id.can_create_asset)
                        and move_line.account_id.create_asset != "no"
                        and not move.reversed_entry_id
                        and not (move_line.currency_id or move.currency_id).is_zero(move_line.price_total)
                        and not move_line.asset_ids
                ):
                    if not move_line.name:
                        raise UserError(
                            _('Journal Items of {account} should have a label in order to generate an asset').format(
                                account=move_line.account_id.display_name))
                    amount_total = amount_left = move_line.debit + move_line.credit
                    unit_uom = self.env.ref('uom.product_uom_unit')
                    if move_line.account_id.multiple_assets_per_line and ((
                                                                                  move_line.product_uom_id and move_line.product_uom_id.category_id.id == unit_uom.category_id.id) or not move_line.product_uom_id):
                        units_quantity = move_line.product_uom_id._compute_quantity(move_line.quantity, unit_uom, False)
                    else:
                        units_quantity = 1
                    while units_quantity > 0:
                        if units_quantity > 1:
                            original_value = float_round(amount_left / units_quantity,
                                                         precision_rounding=move_line.company_currency_id.rounding)
                            amount_left = float_round(amount_left - original_value,
                                                      precision_rounding=move_line.company_currency_id.rounding)
                        else:
                            original_value = amount_left
                        vals = {
                            'name': move_line.name,
                            'company_id': move_line.company_id.id,
                            'currency_id': move_line.company_currency_id.id,
                            'account_analytic_id': move_line.analytic_account_id.id,
                            'project_site_id': move_line.project_site_id.id,
                            'type_id': move_line.type_id.id,
                            'location_id': move_line.location_id.id,
                            'analytic_tag_ids': [(6, False, move_line.analytic_tag_ids.ids)],
                            'original_move_line_ids': [(6, False, move_line.ids)],
                            'state': 'draft',
                            'original_value': original_value,
                        }
                        model_id = move_line.account_id.asset_model
                        if model_id:
                            vals.update({
                                'model_id': model_id.id,
                            })
                        auto_validate.append(move_line.account_id.create_asset == 'validate')
                        invoice_list.append(move)
                        create_list.append(vals)
                        units_quantity -= 1

        assets = self.env['account.asset'].create(create_list)
        for asset, vals, invoice, validate in zip(assets, create_list, invoice_list, auto_validate):
            if 'model_id' in vals:
                asset._onchange_model_id()
                if validate:
                    asset.validate()
            if invoice:
                asset_name = {
                    'purchase': _('Asset'),
                    'sale': _('Deferred revenue'),
                    'expense': _('Deferred expense'),
                }[asset.asset_type]
                msg = _('%s created from invoice') % (asset_name)
                msg += ': <a href=# data-oe-model=account.move data-oe-id=%d>%s</a>' % (invoice.id, invoice.name)
                asset.message_post(body=msg)
        return assets

    @api.model
    def _prepare_move_for_asset_depreciation(self, vals):
        missing_fields = set(['asset_id', 'move_ref', 'amount', 'asset_remaining_value', 'asset_depreciated_value']) - set(vals)
        if missing_fields:
            raise UserError(_('Some fields are missing {}').format(', '.join(missing_fields)))
        asset = vals['asset_id']
        account_analytic_id = asset.account_analytic_id
        project_site_id = asset.project_site_id
        type_id = asset.type_id
        location_id = asset.location_id
        analytic_tag_ids = asset.analytic_tag_ids
        depreciation_date = vals.get('date', fields.Date.context_today(self))
        company_currency = asset.company_id.currency_id
        current_currency = asset.currency_id
        prec = company_currency.decimal_places
        amount = current_currency._convert(vals['amount'], company_currency, asset.company_id, depreciation_date)
        # Keep the partner on the original invoice if there is only one
        partner = asset.original_move_line_ids.mapped('partner_id')
        partner = partner[:1] if len(partner) <= 1 else self.env['res.partner']
        move_line_1 = {
            'name': asset.name,
            'partner_id': partner.id,
            'account_id': asset.account_depreciation_id.id,
            'debit': 0.0 if float_compare(amount, 0.0, precision_digits=prec) > 0 else -amount,
            'credit': amount if float_compare(amount, 0.0, precision_digits=prec) > 0 else 0.0,
            'analytic_account_id': account_analytic_id.id if asset.asset_type == 'sale' else False,
            'project_site_id': project_site_id.id if asset.asset_type == 'sale' else False,
            'type_id': type_id.id if asset.asset_type == 'sale' else False,
            'location_id': location_id.id if asset.asset_type == 'sale' else False,
            'analytic_tag_ids': [(6, 0, analytic_tag_ids.ids)] if asset.asset_type == 'sale' else False,
            'currency_id': current_currency.id,
            'amount_currency': -vals['amount'],
        }
        move_line_2 = {
            'name': asset.name,
            'partner_id': partner.id,
            'account_id': asset.account_depreciation_expense_id.id,
            'credit': 0.0 if float_compare(amount, 0.0, precision_digits=prec) > 0 else -amount,
            'debit': amount if float_compare(amount, 0.0, precision_digits=prec) > 0 else 0.0,
            'analytic_account_id': account_analytic_id.id if asset.asset_type in ('purchase', 'expense') else False,
            'project_site_id': project_site_id.id if asset.asset_type in ('purchase', 'expense') else False,
            'type_id': type_id.id if asset.asset_type in ('purchase', 'expense') else False,
            'location_id': location_id.id if asset.asset_type in ('purchase', 'expense') else False,
            'analytic_tag_ids': [(6, 0, analytic_tag_ids.ids)] if asset.asset_type in (
            'purchase', 'expense') else False,
            'currency_id': current_currency.id,
            'amount_currency': vals['amount'],
        }
        move_vals = {
            'ref': vals['move_ref'],
            'partner_id': partner.id,
            'date': depreciation_date,
            'journal_id': asset.journal_id.id,
            'line_ids': [(0, 0, move_line_1), (0, 0, move_line_2)],
            'asset_id': asset.id,
            'asset_remaining_value': vals['asset_remaining_value'],
            'asset_depreciated_value': vals['asset_depreciated_value'],
            'amount_total': amount,
            'name': '/',
            'asset_value_change': vals.get('asset_value_change', False),
            'move_type': 'entry',
            'currency_id': current_currency.id,
        }
        return move_vals


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    project_site_id = fields.Many2one(comodel_name="account.analytic.account", string="Project/Site",domain=[('analytic_account_type','=','project_site')], required=False, )
    type_id = fields.Many2one(comodel_name="account.analytic.account", string="Type",domain=[('analytic_account_type','=','type')], required=False, )
    location_id = fields.Many2one(comodel_name="account.analytic.account", string="Location",domain=[('analytic_account_type','=','location')], required=False, )
    analytic_account_id = fields.Many2one(string='Cost Center')

    @api.onchange('project_site_id')
    def get_location_and_types(self):
        for rec in self:
            rec.type_id = rec.project_site_id.analytic_type_filter_id.id
            rec.location_id = rec.project_site_id.analytic_location_id.id

    def open_account_analytic_types(self):
        return {
            'name': 'Analytic Account Types',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'wizard.analytic.account.types',
            'context': {'default_move_line': self.id},
            'target': 'new',
        }

