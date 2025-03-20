# -*- coding: utf-8 -*-
""" init object """
import base64
import calendar
import csv
from io import BytesIO,StringIO
from odoo import fields, models, _
from odoo.exceptions import UserError
from datetime import datetime, date
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF



class RouAssetSchedule(models.TransientModel):
    _name = 'rou.asset.schedule.wizard'
    _description = 'rou.asset.schedule.wizard'

    def _get_date_from_now(self):
        today = datetime.now().today()
        first_day_this_month = date(day=1, month=today.month, year=today.year)
        return first_day_this_month

    def _get_date_to(self):
        today = datetime.now().today()
        last_day = calendar.monthrange(today.year, today.month)
        last_day_this_month = date(day=last_day[1], month=today.month,
                                   year=today.year)
        return last_day_this_month

    date_from = fields.Date(string="Date From", default=_get_date_from_now,
                            required=False, )
    date_to = fields.Date(string="Date To", default=_get_date_to,
                          required=False, )
    vendor_ids = fields.Many2many(comodel_name="res.partner", )
    contract_ids = fields.Many2many(comodel_name="leasee.contract",
                                    domain=[('parent_id', '=', False)])
    excel_sheet = fields.Binary('Download Report')
    excel_sheet_name = fields.Char(string='Name', size=64)

    def get_report_data(self):
        data = []
        LeaseeContract = self.env['leasee.contract']
        domain = [('company_id', '=', self.env.company.id),('state', '!=', 'draft')]  # Base domain

        # Append conditions dynamically
        if self.contract_ids:
            domain.append(('id', 'child_of', self.contract_ids.ids))

        if self.vendor_ids:
            domain.append(('vendor_id', 'in', self.vendor_ids.ids))

        contracts = LeaseeContract.search(domain)
        contracts = self.env['leasee.contract'].search(
            [('id', 'child_of', contracts.ids)])
        for contract in contracts.asset_id:
            if self.date_from <= contract.acquisition_date <= self.date_to:
                data.append({
                    'lease_number': contract.name,
                    'period_no': 0,
                    'project_site': contract.leasee_contract_ids.project_site_id.name,
                    'period_start_date': contract.acquisition_date.strftime(DF),
                    'depreciation_term': contract.method_number,
                    'opening_balance': round(contract.original_value, contract.currency_id.decimal_places),
                    'initial_measurement': 0,
                    'impairment': 0,
                    'direct_cost_added': 0,
                    'depreciation': 0,
                    'adjustment_lease_liability': 0,
                    'rou_sub_leased': 0,
                    'rou_increase_decrease': 0,
                    'closing_balance': round(contract.original_value, contract.currency_id.decimal_places),
                    'posted_gl': 'True',
                    'posting_date': 0,
                    'posting_doc_no': contract.name,
                })
                dep_moves = contract.depreciation_move_ids.filtered(
                    lambda m: self.date_from <= m.date <= self.date_to
                ).sorted(key=lambda m: m.date)
                for ins in dep_moves:
                    initial_direct_cost = sum(
                        ins.asset_id.leasee_contract_ids.mapped(
                            'initial_direct_cost'))
                    period_no = self.get_period_no(ins)
                    leasor_contract = self.env['leasor.contract'].search([(
                        'leasee_contract_id',
                        'in',
                        ins.asset_id.leasee_contract_ids.ids)])
                    other_ins = ins.asset_id.children_ids.depreciation_move_ids.filtered(
                        lambda a: a.date == ins.date)
                    rou_increase_decrease = sum(other_ins.mapped('amount_total'))
                    lease_number = ins.asset_id.leasee_contract_ids and \
                                   ins.asset_id.leasee_contract_ids[-1].name or \
                                   ins.asset_id.parent_id.leasee_contract_ids[
                                       -1].name or ''
                    first_lease = ins.asset_id.leasee_contract_ids[:1] if ins.asset_id.leasee_contract_ids else False
                    if  isinstance(ins.ref, str) and 'Disposal' in ins.ref and ins.asset_id.leasee_contract_ids and first_lease.state == 'terminated':
                        prev = ins.search([('id', '!=', ins.id),
                                           ('asset_id', '=', ins.asset_id.id),
                                           ('date', '<=', ins.date)],
                                          order='date desc', limit=1)
                        data.append({
                            'lease_number': lease_number,
                            'period_no': period_no,
                            'project_site': ins.asset_id.project_site_id.name,
                            'period_start_date': ins.date.strftime(DF),
                            'depreciation_term': (
                                                         ins.asset_id.method_number + 1) - period_no,
                            'opening_balance':  round(prev.asset_remaining_value, contract.currency_id.decimal_places),
                            'initial_measurement': 0,
                            'impairment': 0,
                            'direct_cost_added': 0,
                            'depreciation': 0,
                            'adjustment_lease_liability': 0,
                            'rou_sub_leased': leasor_contract.installment_amount,
                            'rou_increase_decrease': 0,
                            'closing_balance': 0,
                            'posted_gl': 'True' if ins.state == 'posted' else 'False',
                            'posting_date': ins.posting_date.strftime(
                                DF) if ins.posting_date else '',
                            'posting_doc_no': ins.name,
                        })
                    else:
                        data.append({
                            'lease_number': lease_number,
                            'period_no': period_no,
                            'project_site': ins.asset_id.project_site_id.name,
                            'period_start_date': ins.date.strftime(DF),
                            'depreciation_term': (
                                                         ins.asset_id.method_number + 1) - period_no,
                            'opening_balance':  round( (
                                    ins.amount_total + ins.asset_remaining_value), contract.currency_id.decimal_places),
                            'initial_measurement': 0,
                            'impairment': 0,
                            'direct_cost_added': initial_direct_cost if period_no == 1 else 0,
                            'depreciation': ins.amount_total,
                            'adjustment_lease_liability': 0,
                            'rou_sub_leased': leasor_contract.installment_amount,
                            'rou_increase_decrease': 0,
                            'closing_balance': round( ins.asset_remaining_value , contract.currency_id.decimal_places),
                            'posted_gl': 'True' if ins.state == 'posted' else 'False',
                            'posting_date': ins.posting_date.strftime(
                                DF) if ins.posting_date else '',
                            'posting_doc_no': ins.name,
                        })
                for children in contract.children_ids:
                    if self.date_from <= children.acquisition_date <= self.date_to:
                        data.append({
                            'lease_number': contract.name,
                            'period_no': str(
                                        0) + ' ' + 'GD' if children.original_value < 0 else str(
                                        0) + ' ' + 'GI',
                            'project_site': contract.project_site_id.name,
                            'period_start_date': children.acquisition_date.strftime(DF),
                            'depreciation_term': children.method_number,
                            'opening_balance': 0,
                            'initial_measurement': 0,
                            'impairment': 0,
                            'direct_cost_added': 0,
                            'depreciation': 0,
                            'adjustment_lease_liability': 0,
                            'rou_sub_leased': 0,
                            'rou_increase_decrease': 0,
                            'closing_balance': round(children.original_value  , children.currency_id.decimal_places),
                            'posted_gl': 'True',
                            'posting_date': 0,
                            'posting_doc_no': children.name,
                        })
                        child_dep_moves = children.depreciation_move_ids.filtered(
                            lambda m: self.date_from <= m.date <= self.date_to
                        ).sorted(key=lambda m: m.date)
                        for ins in child_dep_moves:
                            initial_direct_cost = sum(
                                ins.asset_id.leasee_contract_ids.mapped(
                                    'initial_direct_cost'))
                            period_no = self.get_period_no(ins)
                            leasor_contract = self.env['leasor.contract'].search([(
                                'leasee_contract_id',
                                'in',
                                ins.asset_id.leasee_contract_ids.ids)])
                            other_ins = ins.asset_id.children_ids.depreciation_move_ids.filtered(
                                lambda a: a.date == ins.date)
                            rou_increase_decrease = sum(
                                other_ins.mapped('amount_total'))
                            lease_number = ins.asset_id.leasee_contract_ids and \
                                           ins.asset_id.leasee_contract_ids[-1].name or \
                                           ins.asset_id.parent_id.leasee_contract_ids[
                                               -1].name or ''
                            first_lease = ins.asset_id.leasee_contract_ids[:1] if ins.asset_id.leasee_contract_ids else False
                            if  isinstance(ins.ref, str) and 'Disposal' in ins.ref and ins.asset_id.leasee_contract_ids and first_lease.state == 'terminated':
                                prev = ins.search([('id', '!=', ins.id),
                                                   ('asset_id', '=', ins.asset_id.id),
                                                   ('date', '<=', ins.date)],
                                                  order='date desc', limit=1)
                                data.append({
                                    'lease_number': lease_number,
                                    'period_no': str(
                                        period_no) + ' ' + 'GD' if children.original_value < 0 else str(
                                        period_no) + ' ' + 'GI',
                                    'project_site': ins.asset_id.project_site_id.name,

                                    'period_start_date': ins.date.strftime(DF),
                                    'depreciation_term': (
                                                                 ins.asset_id.method_number + 1) - period_no,
                                    'opening_balance': 0,
                                    'initial_measurement': 0,
                                    'impairment': 0,
                                    'direct_cost_added': 0,
                                    'depreciation': 0,
                                    'adjustment_lease_liability': 0,
                                    'rou_sub_leased': leasor_contract.installment_amount,
                                    'rou_increase_decrease': 0,
                                    'closing_balance':  round(prev.asset_remaining_value , children.currency_id.decimal_places),
                                    'posted_gl': 'True' if ins.state == 'posted' else 'False',
                                    'posting_date': ins.posting_date.strftime(
                                        DF) if ins.posting_date else '',
                                    'posting_doc_no': ins.name,

                                })
                            else:
                                data.append({
                                    'lease_number': lease_number,
                                    'period_no': str(
                                        period_no) + ' ' + 'GD' if children.original_value < 0 else str(
                                        period_no) + ' ' + 'GI',
                                    'project_site': ins.asset_id.project_site_id.name,

                                    'period_start_date': ins.date.strftime(DF),
                                    'depreciation_term': (
                                                                 ins.asset_id.method_number + 1) - period_no,
                                    'opening_balance':   round((ins.amount_total + ins.asset_remaining_value) , children.currency_id.decimal_places),
                                    'initial_measurement': 0,
                                    'impairment': 0,
                                    'direct_cost_added': initial_direct_cost if period_no == 1 else 0,
                                    'depreciation': ins.amount_total,
                                    'adjustment_lease_liability': 0,
                                    'rou_sub_leased': leasor_contract.installment_amount,
                                    'rou_increase_decrease': 0,
                                    'closing_balance':  round(ins.asset_remaining_value , children.currency_id.decimal_places),
                                    'posted_gl': 'True' if ins.state == 'posted' else 'False',
                                    'posting_date': ins.posting_date.strftime(
                                        DF) if ins.posting_date else '',
                                    'posting_doc_no': ins.name,
                                })
        return data

    def get_period_no(self, move):
        asset_moves = move.asset_id.depreciation_move_ids
        i = 0
        for m in asset_moves.sorted(key=lambda m: m.date):
            i += 1
            if m == move:
                return i

    def print_report_xlsx(self):
        report_data = self.get_report_data()
        if not report_data:
            raise UserError(_("No data found for the report."))

        headers = list(report_data[0].keys())


        # Use StringIO for text buffer
        csv_buffer = StringIO()
        writer = csv.DictWriter(csv_buffer, fieldnames=headers)
        writer.writeheader()
        writer.writerows(report_data)

        # Encode the string data to bytes
        csv_data = csv_buffer.getvalue().encode('utf-8')
        csv_buffer.close()

        # Encode the data to base64 for Odoo binary field
        self.excel_sheet = base64.b64encode(csv_data)
        self.excel_sheet_name = 'rou_asset_schedule_report.csv'
        attachment = self.env['ir.attachment'].create({
            'name': self.excel_sheet_name,
            'type': 'binary',
            'datas': base64.b64encode(csv_data),
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'text/csv'
        })

        # Return download action
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % (attachment.id),
            'target': 'new',
        }

        # output = io.BytesIO()
        # workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        #
        # TABLE_HEADER = workbook.add_format({
        #     'bold': 1,
        #     'font_name': 'Tahoma',
        #     'border': 0,
        #     'font_size': 12,
        #     'align': 'center',
        #     'valign': 'vcenter',
        #     'font_color': 'black',
        # })
        #
        # header_format = workbook.add_format({
        #     'bold': 1,
        #     'font_name': 'Aharoni',
        #     'border': 0,
        #     'font_size': 12,
        #     'align': 'center',
        #     'valign': 'vcenter',
        #     'font_color': 'black',
        #     'bg_color': '#c3c6c5',
        # })
        #
        # TABLE_HEADER_Data = TABLE_HEADER
        # TABLE_HEADER_Data.num_format_str = '#,##0.00_);(#,##0.00)'
        # STYLE_LINE = workbook.add_format({
        #     'border': 0,
        #     'align': 'center',
        #     'valign': 'vcenter',
        # })
        #
        # TABLE_data = workbook.add_format({
        #     'bold': 1,
        #     'font_name': 'Aharoni',
        #     'border': 0,
        #     'font_size': 12,
        #     'align': 'center',
        #     'valign': 'vcenter',
        #     'font_color': 'black',
        # })
        # TABLE_data.num_format_str = '#,##0.00'
        # TABLE_data_tolal_line = workbook.add_format({
        #     'bold': 1,
        #     'font_name': 'Aharoni',
        #     'border': 1,
        #     'font_size': 12,
        #     'align': 'center',
        #     'valign': 'vcenter',
        #     'font_color': 'black',
        #     'bg_color': 'yellow',
        # })
        #
        # TABLE_data_tolal_line.num_format_str = '#,##0.00'
        # TABLE_data_o = workbook.add_format({
        #     'bold': 1,
        #     'font_name': 'Aharoni',
        #     'border': 0,
        #     'font_size': 12,
        #     'align': 'center',
        #     'valign': 'vcenter',
        #     'font_color': 'black',
        # })
        # STYLE_LINE_Data = STYLE_LINE
        # STYLE_LINE_Data.num_format_str = '#,##0.00_);(#,##0.00)'
        #
        # if report_data:
        #     self.add_xlsx_sheet(report_data, workbook, STYLE_LINE_Data,
        #                         header_format)
        #
        # self.excel_sheet_name = 'RoU Asset Schedule'
        # workbook.close()
        # output.seek(0)
        # self.excel_sheet = base64.b64encode(output.read())
        # self.excel_sheet_name = str(self.excel_sheet_name) + '.xlsx'
        # return {
        #     'type': 'ir.actions.act_url',
        #     'name': 'RoU Asset Schedule',
        #     'url': '/web/content/%s/%s/excel_sheet/RoU Asset Schedule.xlsx?download=true' % (
        #         self._name, self.id),
        #     'target': 'new'
        # }

    # def add_xlsx_sheet(self, report_data, workbook, STYLE_LINE_Data,
    #                    header_format):
    #     self.ensure_one()
    #     batch_size = 10000
    #     total_records = len(report_data)
    #     num_sheets = (total_records // batch_size) + (1 if total_records % batch_size > 0 else 0)
    #     if num_sheets == 0:
    #         worksheet = workbook.add_worksheet(_('RoU Asset Schedule'))
    #         lang = self.env.user.lang
    #         if lang.startswith('ar_'):
    #             worksheet.right_to_left()
    #
    #         row = 0
    #         col = 0
    #         worksheet.write(row, col, _('Leasee Number'), header_format)
    #         col += 1
    #         worksheet.write(row, col, _('Period No.'), header_format)
    #         col += 1
    #         worksheet.write(row, col, _('Project / Site'), header_format)
    #         col += 1
    #         worksheet.write(row, col, _('Period Date'), header_format)
    #         col += 1
    #         worksheet.write(row, col, _('Depreciation Term (mths)'), header_format)
    #         col += 1
    #         worksheet.write(row, col, _('Opening Balance'), header_format)
    #         col += 1
    #         worksheet.write(row, col, _('Initial Measurement'), header_format)
    #         col += 1
    #         worksheet.write(row, col, _('Impairment (-)'), header_format)
    #         col += 1
    #         worksheet.write(row, col, _('Direct Cost Added (+)'), header_format)
    #         col += 1
    #         worksheet.write(row, col, _('Depreciation (-)'), header_format)
    #         col += 1
    #         worksheet.write(row, col, _('Adjustment of Lease Liability (+)'),
    #                         header_format)
    #         col += 1
    #         worksheet.write(row, col, _('ROU Sub-Leased'), header_format)
    #         col += 1
    #         worksheet.write(row, col, _('ROU increase/decrease'), header_format)
    #         col += 1
    #         worksheet.write(row, col, _('Closing Balance'), header_format)
    #         col += 1
    #         worksheet.write(row, col, _('Posted to G/L'), header_format)
    #         col += 1
    #         worksheet.write(row, col, _('Posting Date'), header_format)
    #         col += 1
    #         worksheet.write(row, col, _('Posting Document No.'), header_format)
    #     else:
    #         for sheet_index in range(num_sheets):
    #             sheet_name = f"RoU Asset Schedule {sheet_index + 1}"
    #             worksheet = workbook.add_worksheet(sheet_name)
    #             lang = self.env.user.lang
    #             if lang.startswith('ar_'):
    #                 worksheet.right_to_left()
    #
    #             row = 0
    #             col = 0
    #             worksheet.write(row, col, _('Leasee Number'), header_format)
    #             col += 1
    #             worksheet.write(row, col, _('Period No.'), header_format)
    #             col += 1
    #             worksheet.write(row, col, _('Project / Site'), header_format)
    #             col += 1
    #             worksheet.write(row, col, _('Period Date'), header_format)
    #             col += 1
    #             worksheet.write(row, col, _('Depreciation Term (mths)'), header_format)
    #             col += 1
    #             worksheet.write(row, col, _('Opening Balance'), header_format)
    #             col += 1
    #             worksheet.write(row, col, _('Initial Measurement'), header_format)
    #             col += 1
    #             worksheet.write(row, col, _('Impairment (-)'), header_format)
    #             col += 1
    #             worksheet.write(row, col, _('Direct Cost Added (+)'), header_format)
    #             col += 1
    #             worksheet.write(row, col, _('Depreciation (-)'), header_format)
    #             col += 1
    #             worksheet.write(row, col, _('Adjustment of Lease Liability (+)'),
    #                             header_format)
    #             col += 1
    #             worksheet.write(row, col, _('ROU Sub-Leased'), header_format)
    #             col += 1
    #             worksheet.write(row, col, _('ROU increase/decrease'), header_format)
    #             col += 1
    #             worksheet.write(row, col, _('Closing Balance'), header_format)
    #             col += 1
    #             worksheet.write(row, col, _('Posted to G/L'), header_format)
    #             col += 1
    #             worksheet.write(row, col, _('Posting Date'), header_format)
    #             col += 1
    #             worksheet.write(row, col, _('Posting Document No.'), header_format)
    #             start_index = sheet_index * batch_size
    #             end_index = min(start_index + batch_size, total_records)
    #             data_chunk = report_data[start_index:end_index]
    #             row = 0
    #             for line in data_chunk:
    #                 col = 0
    #                 row += 1
    #                 worksheet.write(row, col, line['lease_number'], STYLE_LINE_Data)
    #                 col += 1
    #                 worksheet.write(row, col, line['period_no'], STYLE_LINE_Data)
    #                 col += 1
    #                 worksheet.write(row, col, line['project_site'], STYLE_LINE_Data)
    #                 col += 1
    #                 worksheet.write(row, col, line['period_start_date'],
    #                                 STYLE_LINE_Data)
    #                 col += 1
    #                 worksheet.write(row, col, line['depreciation_term'],
    #                                 STYLE_LINE_Data)
    #                 col += 1
    #                 worksheet.write(row, col, line['opening_balance'], STYLE_LINE_Data)
    #                 col += 1
    #                 worksheet.write(row, col, line['initial_measurement'],
    #                                 STYLE_LINE_Data)
    #                 col += 1
    #                 worksheet.write(row, col, line['impairment'], STYLE_LINE_Data)
    #                 col += 1
    #                 worksheet.write(row, col, line['direct_cost_added'],
    #                                 STYLE_LINE_Data)
    #                 col += 1
    #                 worksheet.write(row, col, line['depreciation'], STYLE_LINE_Data)
    #                 col += 1
    #                 worksheet.write(row, col, line['adjustment_lease_liability'],
    #                                 STYLE_LINE_Data)
    #                 col += 1
    #                 worksheet.write(row, col, line['rou_sub_leased'], STYLE_LINE_Data)
    #                 col += 1
    #                 worksheet.write(row, col, line['rou_increase_decrease'],
    #                                 STYLE_LINE_Data)
    #                 col += 1
    #                 worksheet.write(row, col, line['closing_balance'], STYLE_LINE_Data)
    #                 col += 1
    #                 worksheet.write(row, col, line['posted_gl'], STYLE_LINE_Data)
    #                 col += 1
    #                 worksheet.write(row, col, line['posting_date'], STYLE_LINE_Data)
    #                 col += 1
    #                 worksheet.write(row, col, line['posting_doc_no'], STYLE_LINE_Data)
