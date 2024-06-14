# -*- coding: utf-8 -*-
from odoo import models, api


class ReportInvoiceTaxReport(models.AbstractModel):
    _name = 'report.tasc_invoice_tax_report.uk_inv_tax_report'
    _description = 'Invoice UK Tax report'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['account.move'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'account.move',
            'docs': docs,
            'report_type': data.get('report_type') if data else '',
        }
