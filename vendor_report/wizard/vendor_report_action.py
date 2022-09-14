from datetime import datetime
import time

from odoo import models, api


class ReportVendor(models.AbstractModel):
    _name = 'report.vendor_report.template_vendor_pdf_report'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env[self.env.context.get('active_model')].browse(
            self.env.context.get('active_id'))
        date_from = ''
        date_to = ''
        if data['date_from']:
            date_from = datetime.strptime(data['date_from'], '%Y-%m-%d')
        if data['date_to']:
            date_to = datetime.strptime(data['date_to'], '%Y-%m-%d')

        journals = self.env['account.move'].search(
            [('move_type', '=', 'in_invoice'),
             ('company_id', '=', int(data['company_id'])),
             ('state', '=', data['state'])])
        if date_from and date_to:
            journals = self.env['account.move'].search(
                [('move_type', '=', 'in_invoice'),
                 ('date', '>=', date_from),
                 ('date', '<=', date_to),
                 ('company_id', '=', int(data['company_id'])),
                 ('state', '=', data['state'])])
        elif date_from:
            journals = self.env['account.move'].search(
                [('move_type', '=', 'in_invoice'),
                 ('date', '>=', date_from),
                 ('company_id', '=', int(data['company_id'])),
                 ('state', '=', data['state'])])
        elif date_to:
            journals = self.env['account.move'].search(
                [('move_type', '=', 'in_invoice'),
                 ('date', '<=', date_to),
                 ('company_id', '=', int(data['company_id'])),
                 ('state', '=', data['state'])])
        data_dict = []
        for rec in journals:
            taxes = rec.mapped(lambda x: x.invoice_line_ids.mapped('tax_ids'))
            for tax in taxes:
                lines = rec.invoice_line_ids.filtered(
                    lambda x: x.tax_ids.id == tax.id)
                sub_total = sum(lines.mapped(lambda x: x.price_subtotal))
                tax_amount = (sub_total * tax.amount) / 100
                data_dict.append({
                    'bill_date': rec.invoice_date,
                    'accounting_date': rec.date,
                    'supplier': rec.partner_id.name,
                    'bill_ref': rec.ref,
                    'journal': rec.name,
                    'label': lines[0].name,
                    'currency': rec.currency_id.name,
                    'pre_vat_amt': sub_total,
                    'vat_amt': tax_amount,
                    'total': sub_total + tax_amount,
                    'taxes': tax.name,
                    'tax_id': rec.partner_id.vat,
                })
            lines_wout_tax = rec.invoice_line_ids.filtered(
                lambda x: x.tax_ids.id is False)
            data_dict.append({
                'bill_date': rec.invoice_date,
                'accounting_date': rec.date,
                'supplier': rec.partner_id.name,
                'bill_ref': rec.ref,
                'journal': rec.name,
                'label': lines_wout_tax[0].name if lines_wout_tax[0].name else '',
                'currency': rec.currency_id.name,
                'pre_vat_amt': sum(lines_wout_tax.mapped(lambda x: x.price_subtotal)),
                'vat_amt': '',
                'total': sum(lines_wout_tax.mapped(lambda x: x.price_subtotal)),
                'taxes': '',
                'tax_id': rec.partner_id.vat,
            })

        return {
            'doc_ids': self.ids,
            'docs': docs,
            'fetched_data': data_dict,
        }
