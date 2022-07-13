from odoo import models, api, fields
from odoo.exceptions import ValidationError


class ReportInvoiceTaxReport(models.AbstractModel):
    _name = 'report.invoice_tax_report.inv_tax_report'
    _description = 'Invoice Tax report'

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
            'exchange_rate': rate
        }

# class ReportInvoiceWithPayment(models.AbstractModel):
#     _name = 'report.account.report_invoice_with_payments'
#     _description = 'Account report with payment lines'
#
#     @api.model
#     def _get_report_values(self, docids, data=None):
#         return {
#             'doc_ids': docids,
#             'doc_model': 'account.move',
#             'docs': self.env['account.move'].browse(docids),
#             'report_type': data.get('report_type') if data else '',
#         }
