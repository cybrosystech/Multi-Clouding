# -*- coding: utf-8 -*-
from odoo import api, models
from odoo.exceptions import ValidationError


class ReportTascInvoiceGeneral(models.AbstractModel):
    """ Generic report for Invoice and credit note. """
    _name = 'report.tasc_invoice_report_general.inv_general_report'
    _description = 'Invoice / Credit Note Report General'

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
