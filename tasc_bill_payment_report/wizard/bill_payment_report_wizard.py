import base64
import io
import datetime
import xlsxwriter
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class CashBurnReportWizard(models.Model):
    """ Class for Cash Burn Report xlsx """
    _name = 'bill.payment.report.wizard'
    _description = 'TASC Bill Payment Report'

    start_date = fields.Date(string="From Date",
                             default=datetime.datetime.now(), required=True)
    end_date = fields.Date(string="To Date",
                           default=datetime.datetime.now(), required=True)
    company_id = fields.Many2one('res.company', 'Company',
                                 default=lambda self: self.env.company,
                                 required=True)
    excel_sheet = fields.Binary('Download Report')
    excel_sheet_name = fields.Char(string='Name', size=64)

    @api.constrains('end_date')
    def onsave_end_date(self):
        if self.end_date < self.start_date:
            raise UserError(
                "The end date should be greater than or equal to start date.")

    def print_report_xlsx(self):
        """ Method for print Cash Burn xlsx report"""
        report_data = self.get_report_data()
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})

        TABLE_HEADER = workbook.add_format({
            'bold': 1,
            'font_name': 'Tahoma',
            'border': 0,
            'font_size': 12,
            'align': 'center',
            'valign': 'vcenter',
            'font_color': 'black',
        })

        header_format = workbook.add_format({
            'bold': 1,
            'font_name': 'Aharoni',
            'border': 0,
            'font_size': 13,
            'align': 'left',
            'valign': 'vcenter',
            'font_color': 'black',
            'bg_color': '#c3c6c5',
        })

        TABLE_HEADER_Data = TABLE_HEADER
        TABLE_HEADER_Data.num_format_str = '#,##0.00_);(#,##0.00)'
        STYLE_LINE = workbook.add_format({
            'border': 0,
            'align': 'left',
            'valign': 'vcenter',
        })
        STYLE_LINE_HEADER = workbook.add_format({
            'bold': 1,
            'font_name': 'Aharoni',
            'font_size': 14,
            'border': 0,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#7f8eb8',
        })

        TABLE_data = workbook.add_format({
            'bold': 1,
            'font_name': 'Aharoni',
            'border': 0,
            'font_size': 12,
            'align': 'center',
            'valign': 'vcenter',
            'font_color': 'black',
        })
        TABLE_data.num_format_str = '#,##0.00'
        TABLE_data_tolal_line = workbook.add_format({
            'bold': 1,
            'font_name': 'Aharoni',
            'border': 1,
            'font_size': 12,
            'align': 'center',
            'valign': 'vcenter',
            'font_color': 'black',
            'bg_color': 'yellow',
        })
        date_format = workbook.add_format({
            'border': 0,
            'align': 'left',
            'valign': 'vcenter',
            'num_format': 'dd/mm/yyyy'})

        TABLE_data_tolal_line.num_format_str = '#,##0.00'
        STYLE_LINE_Data = STYLE_LINE
        STYLE_LINE_Data.num_format_str = '#,##0.00_);(#,##0.00)'

        if report_data:
            self.add_xlsx_sheet(report_data, workbook, STYLE_LINE_Data,
                                header_format, STYLE_LINE_HEADER, date_format)

        self.excel_sheet_name = 'Tasc Bill Payment Report'
        workbook.close()
        output.seek(0)
        self.excel_sheet = base64.b64encode(output.read())
        self.excel_sheet_name = str(self.excel_sheet_name) + '.xlsx'
        return {
            'type': 'ir.actions.act_url',
            'name': 'Tasc Bill Payment Report',
            'url': '/web/content/%s/%s/excel_sheet/%s?download=true' % (
                self._name, self.id, self.excel_sheet_name),
            'target': 'new'
        }

    def get_report_data(self):
        """Method to compute Tasc Bill Payment Report."""
        move_ids = self.env['account.move'].search(
            [('state', '=', 'posted'),
             ('move_type', 'in', ['in_invoice', 'in_refund']),
             ('company_id', '=', self.env.company.id),
             ('date', '>=', self.start_date), ('date', '<=', self.end_date)],
            order="id ASC")
        return move_ids

    def add_xlsx_sheet(self, report_data, workbook, STYLE_LINE_Data,
                       header_format, STYLE_LINE_HEADER, date_format):
        """ Method to add datas to the Tasc BIll Payment xlsx report"""
        self.ensure_one()
        worksheet = workbook.add_worksheet(_('Tasc Bill Payment Report'))
        lang = self.env.user.lang
        if lang.startswith('ar_'):
            worksheet.right_to_left()

        row = 0
        col = 0
        worksheet.merge_range(row, row, col, col + 14,
                              _('Tasc Bill Payment Report'),
                              STYLE_LINE_HEADER)
        row += 1
        col = 0
        worksheet.write(row, col, _('Date'), header_format)
        col += 1
        worksheet.write(row, col, _('Accounting Date'), header_format)
        col += 1
        worksheet.write(row, col, _('Project Site'), header_format)
        col += 1
        worksheet.write(row, col, _('Name'), header_format)
        col += 1
        worksheet.write(row, col, _('Amount'), header_format)
        col += 1
        worksheet.write(row, col, _('Bill Reference'), header_format)
        col += 1
        worksheet.write(row, col, _('Label'), header_format)
        col += 1
        worksheet.write(row, col, _('Lease Number'), header_format)
        col += 1
        worksheet.write(row, col, _('Commencement Date'), header_format)
        col += 1
        worksheet.write(row, col, _('Contract Period'), header_format)
        col += 1
        worksheet.write(row, col, _('Status'), header_format)
        col += 1
        worksheet.write(row, col, _('Payment Journal'), header_format)
        col += 1
        worksheet.write(row, col, _('Payment Number'), header_format)
        col += 1
        worksheet.write(row, col, _('Payment Date'), header_format)
        col += 1
        worksheet.write(row, col, _('Tasc Reference'), header_format)
        col += 1
        row += 1
        for line in report_data:
            move_line = line.invoice_line_ids[0]
            payment_ids = self.env['account.payment'].search([]).filtered(
                lambda x: line.id in x.reconciled_bill_ids.ids)
            payment_name = ''
            journal_name = ''
            payment_date = ''
            payment_state = ''

            if len(payment_ids) > 1:
                # Collect and join payment names, journal names, and dates
                payment_name = ', '.join(
                    payment.name for payment in payment_ids)
                payment_state = ', '.join(
                    payment.state for payment in payment_ids)
                journal_name = ', '.join(
                    payment.journal_id.name for payment in payment_ids)
                payment_date = ', '.join(
                    payment.date.strftime('%Y-%m-%d') for payment in
                    payment_ids)
            else:
                # Use the single payment details if only one payment
                if payment_ids:
                    single_payment = payment_ids[0]
                    payment_name = single_payment.name
                    journal_name = single_payment.journal_id.name
                    payment_date = single_payment.date.strftime('%Y-%m-%d')
                    payment_state = single_payment.state

            if payment_ids:
                col = 0
                if line.invoice_date:
                    worksheet.write(row, col, line.invoice_date,
                                    date_format)
                else:
                    worksheet.write(row, col, '', date_format)
                col += 1
                if line.date:
                    worksheet.write(row, col, line.date,
                                    date_format)
                else:
                    worksheet.write(row, col, '', date_format)
                col += 1

                if line.leasee_contract_id.project_site_id:
                    if line.leasee_contract_id.project_site_id and line.leasee_contract_id.project_site_id.code:
                        worksheet.write(row, col,
                                        line.leasee_contract_id.project_site_id.name + "-" + line.leasee_contract_id.project_site_id.code,
                                        STYLE_LINE_Data)
                    else:
                        worksheet.write(row, col,
                                        line.leasee_contract_id.project_site_id.name,
                                        STYLE_LINE_Data)
                else:
                    if line.lease_security_advance_id and line.lease_security_advance_id.leasee_contract_id.project_site_id:
                        if line.lease_security_advance_id.leasee_contract_id.project_site_id and line.lease_security_advance_id.leasee_contract_id.project_site_id.code:
                            worksheet.write(row, col,
                                            line.lease_security_advance_id.leasee_contract_id.project_site_id.name + "-" + line.lease_security_advance_id.leasee_contract_id.project_site_id.code,
                                            STYLE_LINE_Data)
                        else:
                            worksheet.write(row, col,
                                            line.lease_security_advance_id.leasee_contract_id.project_site_id.name,
                                            STYLE_LINE_Data)
                    else:
                        worksheet.write(row, col, '', STYLE_LINE_Data)
                col += 1

                if line.name:
                    worksheet.write(row, col, line.name,
                                    STYLE_LINE_Data)
                else:
                    worksheet.write(row, col, '', STYLE_LINE_Data)
                col += 1

                if line.amount_total:
                    worksheet.write(row, col, line.amount_total,
                                    STYLE_LINE_Data)
                else:
                    worksheet.write(row, col, '', STYLE_LINE_Data)
                col += 1

                if line.ref:
                    worksheet.write(row, col, line.ref,
                                    STYLE_LINE_Data)
                else:
                    worksheet.write(row, col, '', STYLE_LINE_Data)
                col += 1
                if move_line and move_line.name:
                    worksheet.write(row, col, move_line.name,
                                    STYLE_LINE_Data)
                else:
                    worksheet.write(row, col, '', STYLE_LINE_Data)
                col += 1

                if line.leasee_contract_id:
                    worksheet.write(row, col, line.leasee_contract_id.name,
                                    STYLE_LINE_Data)
                else:
                    if line.lease_security_advance_id.leasee_contract_id:
                        worksheet.write(row, col, line.lease_security_advance_id.leasee_contract_id.name,
                                        STYLE_LINE_Data)
                    else:
                        worksheet.write(row, col, '', STYLE_LINE_Data)
                col += 1

                if line.leasee_contract_id.commencement_date:
                    worksheet.write(row, col,
                                    line.leasee_contract_id.commencement_date,
                                    date_format)
                else:
                    if line.lease_security_advance_id.leasee_contract_id.commencement_date:
                        worksheet.write(row, col,
                                        line.lease_security_advance_id.leasee_contract_id.commencement_date,
                                        date_format)
                    else:
                        worksheet.write(row, col, '', date_format)
                col += 1

                if line.leasee_contract_id.lease_contract_period:
                    worksheet.write(row, col,
                                    line.leasee_contract_id.lease_contract_period,
                                    STYLE_LINE_Data)
                else:
                    if line.lease_security_advance_id.leasee_contract_id.lease_contract_period:
                        worksheet.write(row, col,
                                        line.lease_security_advance_id.leasee_contract_id.lease_contract_period,
                                        STYLE_LINE_Data)
                    else:
                        worksheet.write(row, col, '', STYLE_LINE_Data)
                col += 1

                if payment_state:
                    worksheet.write(row, col, payment_state,
                                    STYLE_LINE_Data)
                else:
                    worksheet.write(row, col, '', STYLE_LINE_Data)
                col += 1

                if journal_name:
                    worksheet.write(row, col, journal_name,
                                    STYLE_LINE_Data)
                else:
                    worksheet.write(row, col, '', STYLE_LINE_Data)
                col += 1

                if payment_name:
                    worksheet.write(row, col, payment_name,
                                    STYLE_LINE_Data)
                else:
                    worksheet.write(row, col, '', STYLE_LINE_Data)
                col += 1

                if payment_date:
                    worksheet.write(row, col, payment_date,
                                    date_format)
                else:
                    worksheet.write(row, col, '', date_format)
                col += 1
                if line.reference:
                    worksheet.write(row, col, line.reference,
                                    STYLE_LINE_Data)
                else:
                    worksheet.write(row, col, '', STYLE_LINE_Data)
                col += 1
                row += 1
