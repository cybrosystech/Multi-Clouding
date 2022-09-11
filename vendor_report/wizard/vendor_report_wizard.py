from odoo import models, fields
from odoo.exceptions import UserError
from odoo.tools import date_utils, io, xlsxwriter
from odoo.tools.safe_eval import json
from datetime import datetime


class VendorReportWizard(models.TransientModel):
    _name = 'vendor.report.wizard'

    date_from = fields.Date(string="Date From")
    date_to = fields.Date(string="Date To")
    state = fields.Selection(selection=[
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        ('cancel', 'Cancelled'), ('to_approve', 'To Approve'),
    ], string='Status', required=True, copy=False, tracking=True,
        default='posted')

    def generate_pdf_report(self):
        self.ensure_one()
        logged_users = self.env['res.company']._company_default_get(
            'rent.request')
        if self.date_from and self.date_to:
            if self.date_from > self.date_to:
                raise UserError("Start date should be less than end date")

        data = {
            'ids': self.ids,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'state': self.state,
            'company_id': self.env.company.id
        }
        return self.env.ref(
            'vendor_report.action_vendor_pdf_report').report_action(
            self, data)

    def generate_xlsx_report(self):
        if self.date_from and self.date_to:
            if self.date_from > self.date_to:
                raise UserError("Start date should be less than end date")
        data = {
            'ids': self.ids,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'state': self.state,
            'company_id': self.env.company.id
        }
        return {
            'type': 'ir.actions.report',
            'data': {'model': 'vendor.report.wizard',
                     'options': json.dumps(data,
                                           default=date_utils.json_default),
                     'output_format': 'xlsx',
                     'report_name': 'Vendor Report',
                     },
            'report_type': 'xlsx'
        }

    def get_xlsx_report(self, data, response):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
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
                 ('invoice_date', '>=', date_from),
                 ('invoice_date', '<=', date_to),
                 ('company_id', '=', self.env.company.id),
                 ('state', '=', data['state'])])
        elif date_from:
            journals = self.env['account.move'].search(
                [('move_type', '=', 'in_invoice'),
                 ('invoice_date', '>=', date_from),
                 ('company_id', '=', int(data['company_id'])),
                 ('state', '=', data['state'])])
        elif date_to:
            journals = self.env['account.move'].search(
                [('move_type', '=', 'in_invoice'),
                 ('invoice_date', '<=', date_to),
                 ('company_id', '=', int(data['company_id'])),
                 ('state', '=', data['state'])])
        sheet = workbook.add_worksheet()
        head = workbook.add_format(
            {'font_size': 13, 'align': 'center', 'valign': 'vcenter',
             'bg_color': '#1a1c99',
             'font_color': '#f2f7f4', 'border': 2})
        date_format = workbook.add_format(
            {'num_format': 'yyyy/mm/dd', 'align': 'center'})
        num = workbook.add_format({'align': 'center'})

        sheet.set_row(2, 25)
        sheet.set_column('A2:L2', 20)

        sheet.write('A3', 'Bill Date', head)
        sheet.write('B3', 'Accounting Date', head)
        sheet.write('C3', 'Supplier', head)
        sheet.write('D3', 'Bill Reference', head)
        sheet.write('E3', 'Bill Number', head)
        sheet.write('F3', 'Label', head)
        sheet.write('G3', 'Currency', head)
        sheet.write('H3', 'Pre Vat Amount', head)
        sheet.write('I3', 'VAT Amount', head)
        sheet.write('J3', 'Total', head)
        sheet.write('K3', 'Taxes', head)
        sheet.write('L3', 'Tax ID', head)

        row_num = 2
        col_num = 0
        for rec in journals:
            taxes = rec.mapped(lambda x: x.invoice_line_ids.mapped('tax_ids'))
            for tax in taxes:
                lines = rec.invoice_line_ids.filtered(
                    lambda x: x.tax_ids.id == tax.id)
                sub_total = sum(lines.mapped(lambda x: x.price_subtotal))
                tax_amount = (sub_total * tax.amount) / 100
                sheet.write(row_num + 1, col_num, rec.invoice_date,
                            date_format)
                sheet.write(row_num + 1, col_num + 1, rec.date,
                            date_format)
                sheet.write(row_num + 1, col_num + 2,
                            rec.partner_id.name,
                            date_format)
                sheet.write(row_num + 1, col_num + 3, rec.ref,
                            date_format)
                sheet.write(row_num + 1, col_num + 4, rec.name,
                            date_format)
                sheet.write(row_num + 1, col_num + 5, lines[0].name,
                            date_format)
                sheet.write(row_num + 1, col_num + 6,
                            rec.currency_id.name,
                            date_format)
                sheet.write(row_num + 1, col_num + 7, sub_total, num)
                sheet.write(row_num + 1, col_num + 8, tax_amount, num)
                sheet.write(row_num + 1, col_num + 9, sub_total +
                            tax_amount, num)
                sheet.write(row_num + 1, col_num + 10, tax.name, date_format)
                sheet.write(row_num + 1, col_num + 11,
                            rec.partner_id.vat if rec.partner_id.vat else '',
                            num)
                row_num = row_num + 1

            lines_wout_tax = rec.invoice_line_ids.filtered(
                lambda x: x.tax_ids.id is False)
            if lines_wout_tax:
                sheet.write(row_num + 1, col_num, rec.invoice_date,
                            date_format)
                sheet.write(row_num + 1, col_num + 1, rec.date,
                            date_format)
                sheet.write(row_num + 1, col_num + 2,
                            rec.partner_id.name,
                            date_format)
                sheet.write(row_num + 1, col_num + 3, rec.ref,
                            date_format)
                sheet.write(row_num + 1, col_num + 4, rec.name,
                            date_format)
                sheet.write(row_num + 1, col_num + 5,
                            lines_wout_tax[0].name if lines_wout_tax[
                                0].name else '',
                            date_format)
                sheet.write(row_num + 1, col_num + 6,
                            rec.currency_id.name,
                            date_format)
                sheet.write(row_num + 1, col_num + 7,
                            sum(lines_wout_tax.mapped(lambda x: x.price_subtotal)),
                            num)
                sheet.write(row_num + 1, col_num + 8, '', num)
                sheet.write(row_num + 1, col_num + 9,
                            sum(lines_wout_tax.mapped(lambda x: x.price_subtotal)),
                            num)
                sheet.write(row_num + 1, col_num + 10, '', date_format)
                sheet.write(row_num + 1, col_num + 11,
                            rec.partner_id.vat if rec.partner_id.vat else '',
                            num)
                row_num = row_num + 1

        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()
