# -*- coding: utf-8 -*-
from odoo import api, models
from odoo.exceptions import ValidationError


class DebitNote(models.AbstractModel):
    """ Report Debit Note. """
    _name = 'debit.note'
    _description = 'Debit Note'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['account.move'].browse(docids)
        to_currency = self.env['res.currency'].search(
            [('name', '=', 'AED')])
        if not to_currency:
            raise ValidationError('For conversion enable Multi Currency and '
                                  'Currency. AED')
        rate = docs.company_currency_id._get_conversion_rate(
            docs.currency_id, to_currency, docs.company_id,
            docs.date)
        return {
            'doc_ids': docids,
            'doc_model': 'account.move',
            'docs': docs,
            'report_type': data.get('report_type') if data else '',
            'exchange_rate': rate,
            'exchange_currency_id': to_currency
        }
