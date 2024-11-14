import base64
import io
import datetime
from collections import Counter

import xlsxwriter
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class UserActivityReportWizard(models.Model):
    """ Class for User Activity Report xlsx """
    _name = 'user.activity.report.wizard'
    _description = 'TASC User Activity Report'

    start_date = fields.Date(string="From Date",
                             default=datetime.datetime.now(), required=True)
    end_date = fields.Date(string="To Date",
                           default=datetime.datetime.now(), required=True)
    excel_sheet = fields.Binary('Download Report')
    excel_sheet_name = fields.Char(string='Name', size=64)

    @api.constrains('end_date')
    def onsave_end_date(self):
        if self.end_date < self.start_date:
            raise UserError(
                "The end date should be greater than or equal to start date.")

    def print_report_xlsx(self):
        """ Method for print TASC User Activity Report xlsx"""
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

        self.excel_sheet_name = 'TASC User Activity Report'
        workbook.close()
        output.seek(0)
        self.excel_sheet = base64.b64encode(output.read())
        self.excel_sheet_name = str(self.excel_sheet_name) + '.xlsx'
        return {
            'type': 'ir.actions.act_url',
            'name': 'TASC User Activity Report',
            'url': '/web/content/%s/%s/excel_sheet/%s?download=true' % (
                self._name, self.id, self.excel_sheet_name),
            'target': 'new'
        }

    def get_report_data(self):
        """Method to compute TASC User Activity Report."""
        users = self.env['res.users'].search([('id','in',self.env.ref('base.group_user').users.ids)])
        return users

    def add_xlsx_sheet(self, report_data, workbook, STYLE_LINE_Data,
                       header_format, STYLE_LINE_HEADER, date_format):
        """ Method to add datas to the TASC User Activity Report xlsx"""
        self.ensure_one()
        worksheet = workbook.add_worksheet(_('TASC User Activity Report'))
        lang = self.env.user.lang
        if lang.startswith('ar_'):
            worksheet.right_to_left()

        row = 0
        col = 0
        worksheet.merge_range(row, row, col, col + 15,
                              _('TASC User Activity Report'),
                              STYLE_LINE_HEADER)
        row += 1
        col = 0
        worksheet.write(row, col, _('User Name'), header_format)
        col += 1
        worksheet.write(row, col, _('User Login'), header_format)
        col += 1
        worksheet.write(row, col, _('User Status'), header_format)
        col += 1
        worksheet.write(row, col, _('Default Company'), header_format)
        col += 1
        worksheet.write(row, col, _('Vendor Bills'), header_format)
        col += 1
        worksheet.write(row, col, _('Customer Invoices'), header_format)
        col += 1
        worksheet.write(row, col, _('Assets'), header_format)
        col += 1
        worksheet.write(row, col, _('Purchase Order'), header_format)
        col += 1
        worksheet.write(row, col, _('Incoming Receipts'), header_format)
        col += 1
        worksheet.write(row, col, _('Vendor Payments'), header_format)
        col += 1
        worksheet.write(row, col, _('Customer Payments'), header_format)
        col += 1
        worksheet.write(row, col, _('MISC'), header_format)
        col += 1
        worksheet.write(row, col, _('Bank Reconcilation'), header_format)
        col += 1
        worksheet.write(row, col, _('Lease'), header_format)
        col += 1
        worksheet.write(row, col, _('Sale Order'), header_format)
        col += 1
        worksheet.write(row, col, _('Outgoing Receipts'), header_format)
        col += 1
        row += 1
        for user in report_data:
            query = f"""
                    SELECT
                        (SELECT COUNT(*) FROM purchase_order WHERE create_uid = %s AND state != 'cancel' AND create_date >= '{self.start_date}' AND create_date <= '{self.end_date}') AS purchase_order_count,
                        (SELECT COUNT(*) FROM account_move WHERE create_uid = %s AND move_type = 'out_invoice' AND state != 'cancel' AND create_date >= '{self.start_date}' AND create_date <= '{self.end_date}') AS invoice_count,
                        (SELECT COUNT(*) FROM account_move am INNER JOIN account_journal j ON j.id = am.journal_id WHERE am.create_uid = %s AND am.move_type = 'in_invoice' AND am.state != 'cancel' AND j.name ->>'en_US' ILIKE %s AND am.create_date >= '{self.start_date}' AND am.create_date <= '{self.end_date}') AS bill_count,
                        (SELECT COUNT(*) FROM account_move INNER JOIN account_journal ON account_journal.id = account_move.journal_id 
                        WHERE account_move.create_uid = %s AND account_move.state != 'cancel' AND account_journal.code ILIKE 'MISC' AND account_move.create_date >= '{self.start_date}' AND account_move.create_date <= '{self.end_date}') AS misc_count,
                        (SELECT COUNT(*) FROM account_asset WHERE create_uid = %s AND state != 'cancelled' AND create_date >= '{self.start_date}' AND create_date <= '{self.end_date}') AS asset_count,
                        (SELECT COUNT(*) FROM sale_order WHERE create_uid = %s AND state != 'cancel' AND create_date >= '{self.start_date}' AND create_date <= '{self.end_date}') AS sale_order_count,
                        (SELECT COUNT(*) FROM leasee_contract WHERE create_uid = %s AND state != 'cancel' AND create_date >= '{self.start_date}' AND create_date <= '{self.end_date}') AS lease_count,
                        (SELECT COUNT(*) FROM stock_picking sp INNER JOIN stock_picking_type spt ON sp.picking_type_id = spt.id WHERE sp.create_uid = %s AND sp.state != 'cancel' AND spt.code = 'incoming' AND sp.create_date >= '{self.start_date}' AND sp.create_date <= '{self.end_date}') AS incoming_receipts_count,
                        (SELECT COUNT(*) FROM stock_picking sp INNER JOIN stock_picking_type spt ON sp.picking_type_id = spt.id WHERE sp.create_uid = %s AND sp.state != 'cancel' AND spt.code = 'outgoing' AND sp.create_date >= '{self.start_date}' AND sp.create_date <= '{self.end_date}') AS outgoing_receipts_count,
                        (SELECT COUNT(*) FROM account_payment WHERE create_uid = %s AND payment_type = 'outbound' AND create_date >= '{self.start_date}' AND create_date <= '{self.end_date}') AS vendor_payment_count,
                        (SELECT COUNT(*) FROM account_payment WHERE create_uid = %s AND payment_type = 'inbound' AND create_date >= '{self.start_date}' AND create_date <= '{self.end_date}') AS customer_payment_count,
                        (SELECT COUNT(*) FROM account_bank_statement_line WHERE create_uid = %s AND create_date >= '{self.start_date}' AND create_date <= '{self.end_date}') AS reconciliation_count
                """

            self.env.cr.execute(query, (
                user.id, user.id, user.id, '%IFRS%',user.id, user.id,
                user.id, user.id, user.id, user.id, user.id,
                user.id, user.id
            ))
            counts = self.env.cr.fetchone()
            purchase_order_count, invoice_count, bill_count,misc_count,asset_count,sale_order_count,lease_count,incoming_receipts_count,outgoing_receipts_count,vendor_payment_count,customer_payment_count,reconcilation_count  = counts
            col = 0
            worksheet.write(row, col, user.name, STYLE_LINE_Data)
            col+=1
            worksheet.write(row, col, user.login, STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, user.state, STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, user.company_id.name, STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, bill_count, STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, invoice_count, STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, asset_count, STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, purchase_order_count, STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, incoming_receipts_count, STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, vendor_payment_count, STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, customer_payment_count, STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, misc_count, STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, reconcilation_count, STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, lease_count, STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, sale_order_count, STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, outgoing_receipts_count, STYLE_LINE_Data)
            col += 1
            row+=1