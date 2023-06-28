from odoo import api, models


class ReportTascInvoiceGeneral(models.AbstractModel):
    """ Generic report for invoices , debit note and credit note. """
    _name = 'report.tasc_invoice_report_general.inv_general_report'
    _description = 'Invoice Report General'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['account.move'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'account.move',
            'docs': docs,
            'report_type': data.get('report_type') if data else '',
        }
