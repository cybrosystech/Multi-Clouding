# -*- coding: utf-8 -*-
from odoo import models, api


class ReportVendor(models.AbstractModel):
    _name = 'report.tasc_journal_report.template_journal_pdf_report'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['account.move'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'account.move',
            'docs': docs,
        }
