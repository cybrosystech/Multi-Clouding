import ast
import base64
import datetime
import io
import re
from operator import itemgetter
import xlsxwriter
from odoo import models, fields, _, api
from itertools import zip_longest
from odoo.tools.safe_eval import dateutil


class LeaseManagementReport(models.Model):
    _name = "leasee.management.report"

    name = fields.Char(default="Lease Reports")
    lease_contract_ids = fields.Many2many('leasee.contract',
                                          string="Lease Contract")
    payment_aging_as_of_date = fields.Date(string="Date To",
                                           default=datetime.datetime.now(),
                                           required=True)
    payment_aging_limit = fields.Integer(string="Limit")

    ll_aging_as_of_date = fields.Date(string="Date To",
                                      default=datetime.datetime.now(),
                                      required=True)
    ll_aging_limit = fields.Integer(string="Limit")
    ll_rou_as_of_date = fields.Date(string="Date To",
                                    default=datetime.datetime.now(),
                                    required=True)
    ll_rou_limit = fields.Integer(string="Limit")

    interest_amort_start_date = fields.Date(string="Date From")
    interest_amort_end_date = fields.Date(string="Date To",
                                          default=datetime.datetime.now(),
                                          required=True)
    interest_amort_state = fields.Selection(string="Status",
                                            selection=[('draft', 'Draft'),
                                                       ('posted', 'Posted'),
                                                       ('cancel', 'Cancelled')])
    interest_amort_limit = fields.Integer(string="Limit")

    excel_sheet = fields.Binary('Download Report')
    excel_sheet_name = fields.Char(string='Name', size=64)
    ll_rou_state = fields.Selection(string="Status",
                                    selection=[('draft', 'Draft'),
                                               ('posted', 'Posted'),
                                               ('cancel', 'Cancelled')])
    report_values_payment_aging = fields.Text(string="Report Datas - "
                                                     "Payment Aging")
    report_values_interest_and_amortization = fields.Text(string="Report Datas "
                                                                 "- Interest and Amortization")
    report_values_ll_aging = fields.Text(string="Report Values LL Aging")
    report_values_ll_rou = fields.Text(string="Report Values - LL and ROU ")
    company_id = fields.Many2one('res.company', string="Company")
    end_limit = fields.Integer(string="End Limit", compute='compute_end_limit')

    # @api.depends('lease_contract_ids')
    def compute_end_limit(self):
        for rec in self:
            if rec.lease_contract_ids:
                length = self.env['leasee.contract'].search_count(
                    [('id', 'in',
                      rec.lease_contract_ids.ids),
                     ('parent_id', '=', False)
                     ])
            else:
                length = self.env['leasee.contract'].search_count(
                    [('parent_id', '=', False)])
            rec.end_limit = length

    def action_schedule_ll_rou_report(self):
        date = fields.Datetime.now()
        schedule_action = self.env.ref(
            'tasc_lease_management_report.action_ll_rou_report_cron')
        schedule_action.update({
            'nextcall': date + datetime.timedelta(seconds=1)
        })
        self.update({
            'll_rou_limit': 0,
            'report_values_ll_rou': '',
        })

    def action_schedule_ll_aging_report(self):
        date = fields.Datetime.now()
        schedule_action = self.env.ref(
            'tasc_lease_management_report.action_ll_aging_report_cron')
        schedule_action.update({
            'nextcall': date + datetime.timedelta(seconds=1)
        })
        self.update({
            'll_aging_limit': 0,
            'report_values_ll_aging': '',
        })

    def action_schedule_payment_aging_report(self):
        date = fields.Datetime.now()
        schedule_action = self.env.ref(
            'tasc_lease_management_report.action_payment_aging_report_cron')
        schedule_action.update({
            'nextcall': date + datetime.timedelta(seconds=1)
        })
        self.update({
            'payment_aging_limit': 0,
            'report_values_payment_aging': '',
        })

    def action_schedule_lease_report(self):
        date = fields.Datetime.now()
        schedule_action = self.env.ref('tasc_lease_management_report.action_lease_reports')
        schedule_action.update({
            'nextcall': date + datetime.timedelta(seconds=1)
        })
        self.update({
            'interest_amort_limit': 0,
            'report_values_interest_and_amortization': '',
        })

    def action_print_report_payment_aging(self):
        lease_management_report = self.env['leasee.management.report'].search(
            [], limit=1)
        report_data = lease_management_report.report_values_payment_aging
        substrings = re.findall(r"{[^{}]+}", report_data)
        final_list = []
        for str in substrings:
            ss = ast.literal_eval(str)
            final_list.append(ss)

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
            'align': 'center',
            'valign': 'vcenter',
            'font_color': 'black',
            'bg_color': '#c3c6c5',
        })

        TABLE_HEADER_Data = TABLE_HEADER
        TABLE_HEADER_Data.num_format_str = '#,##0.00_);(#,##0.00)'
        STYLE_LINE = workbook.add_format({
            'border': 0,
            'align': 'center',
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

        TABLE_data_tolal_line.num_format_str = '#,##0.00'
        STYLE_LINE_Data = STYLE_LINE
        STYLE_LINE_Data.num_format_str = '#,##0.00_);(#,##0.00)'

        if final_list:
            report_values_list = list(
                filter(lambda x: x['company_id'] == self.company_id.id,
                       final_list))
            self.add_payment_aging_xlsx_sheet(report_values_list, workbook,
                                              STYLE_LINE_Data,
                                              header_format, STYLE_LINE_HEADER)

        self.excel_sheet_name = 'Payment Aging report'
        workbook.close()
        output.seek(0)
        self.excel_sheet = base64.b64encode(output.read())
        self.excel_sheet_name = self.excel_sheet_name + '.xlsx'
        return {
            'type': 'ir.actions.act_url',
            'name': 'Payment Aging Report',
            'url': '/web/content/%s/%s/excel_sheet/%s?download=true' % (
                self._name, self.id, self.excel_sheet_name),
            'target': 'self'
        }

    def action_print_report_interest_and_amortizations(self):
        lease_management_report = self.env['leasee.management.report'].search(
            [], limit=1)
        report_data = lease_management_report.report_values_interest_and_amortization
        substrings = re.findall(r"{[^{}]+}", report_data)
        final_list = []
        for str in substrings:
            ss = ast.literal_eval(str)
            final_list.append(ss)

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
            'align': 'center',
            'valign': 'vcenter',
            'font_color': 'black',
            'bg_color': '#c3c6c5',
        })

        TABLE_HEADER_Data = TABLE_HEADER
        TABLE_HEADER_Data.num_format_str = '#,##0.00_);(#,##0.00)'
        STYLE_LINE = workbook.add_format({
            'border': 0,
            'align': 'center',
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

        TABLE_data_tolal_line.num_format_str = '#,##0.00'
        STYLE_LINE_Data = STYLE_LINE
        STYLE_LINE_Data.num_format_str = '#,##0.00_);(#,##0.00)'

        if final_list:
            report_values_list = list(
                filter(lambda x: x['company_id'] == self.company_id.id and (x['amortization'] !=0 or x['interest']!=0),
                       final_list))
            self.add_xlsx_sheet(report_values_list, workbook, STYLE_LINE_Data,
                                header_format, STYLE_LINE_HEADER)

        self.excel_sheet_name = 'Lease interest and amortization report'
        workbook.close()
        output.seek(0)
        self.excel_sheet = base64.b64encode(output.read())
        self.excel_sheet_name = self.excel_sheet_name + '.xlsx'
        return {
            'type': 'ir.actions.act_url',
            'name': 'Lease Interest and Amortization Report',
            'url': '/web/content/%s/%s/excel_sheet/%s?download=true' % (
                self._name, self.id, self.excel_sheet_name),
            'target': 'self'
        }

    def action_print_report_ll_aging(self):
        lease_management_report = self.env['leasee.management.report'].search(
            [], limit=1)
        report_data = lease_management_report.report_values_ll_aging
        substrings = re.findall(r"{[^{}]+}", report_data)
        final_list = []
        for str in substrings:
            ss = ast.literal_eval(str)
            final_list.append(ss)

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
            'align': 'center',
            'valign': 'vcenter',
            'font_color': 'black',
            'bg_color': '#c3c6c5',
        })

        TABLE_HEADER_Data = TABLE_HEADER
        TABLE_HEADER_Data.num_format_str = '#,##0.00_);(#,##0.00)'
        STYLE_LINE = workbook.add_format({
            'border': 0,
            'align': 'center',
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

        TABLE_data_tolal_line.num_format_str = '#,##0.00'
        STYLE_LINE_Data = STYLE_LINE
        STYLE_LINE_Data.num_format_str = '#,##0.00_);(#,##0.00)'

        if final_list:
            report_values_list = list(
                filter(lambda x: x['company_id'] == self.company_id.id,
                       final_list))
            self.add_ll_aging_xlsx_sheet(report_values_list, workbook, STYLE_LINE_Data,
                                         header_format, STYLE_LINE_HEADER)

        self.excel_sheet_name = 'LL Aging report'
        workbook.close()
        output.seek(0)
        self.excel_sheet = base64.b64encode(output.read())
        self.excel_sheet_name = self.excel_sheet_name + '.xlsx'
        return {
            'type': 'ir.actions.act_url',
            'name': 'LL Aging Report',
            'url': '/web/content/%s/%s/excel_sheet/%s?download=true' % (
                self._name, self.id, self.excel_sheet_name),
            'target': 'self'
        }

    def action_print_report_ll_rou(self):
        lease_management_report = self.env['leasee.management.report'].search(
            [], limit=1)
        report_data = lease_management_report.report_values_ll_rou
        substrings = re.findall(r"{[^{}]+}", report_data)
        final_list = []
        for str in substrings:
            ss = ast.literal_eval(str)
            final_list.append(ss)

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
            'align': 'center',
            'valign': 'vcenter',
            'font_color': 'black',
            'bg_color': '#c3c6c5',
        })

        TABLE_HEADER_Data = TABLE_HEADER
        TABLE_HEADER_Data.num_format_str = '#,##0.00_);(#,##0.00)'
        STYLE_LINE = workbook.add_format({
            'border': 0,
            'align': 'center',
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

        TABLE_data_tolal_line.num_format_str = '#,##0.00'
        STYLE_LINE_Data = STYLE_LINE
        STYLE_LINE_Data.num_format_str = '#,##0.00_);(#,##0.00)'

        if final_list:
            report_values_list = list(
                filter(lambda x: x['company_id'] == self.company_id.id, final_list))
            self.add_ll_rou_xlsx_sheet(report_values_list, workbook, STYLE_LINE_Data,
                                       header_format, STYLE_LINE_HEADER)

        self.excel_sheet_name = 'LL ROU report'
        workbook.close()
        output.seek(0)
        self.excel_sheet = base64.b64encode(output.read())
        self.excel_sheet_name = self.excel_sheet_name + '.xlsx'
        return {
            'type': 'ir.actions.act_url',
            'name': 'LL ROU Report',
            'url': '/web/content/%s/%s/excel_sheet/%s?download=true' % (
                self._name, self.id, self.excel_sheet_name),
            'target': 'self'
        }

    def lease_reports_cron(self, end_limit):
        lease_management_report = self.env['leasee.management.report'].search(
            [], limit=1)

        limit = lease_management_report.interest_amort_limit
        if lease_management_report.lease_contract_ids:
            lease_contract_ids = self.env['leasee.contract'].search(
                [('id', 'in', lease_management_report.lease_contract_ids.ids),
                 ('parent_id', '=', False),
                 ], order='id ASC',
                offset=lease_management_report.interest_amort_limit,
                limit=end_limit)
        else:
            lease_contract_ids = self.env['leasee.contract'].search(
                [('parent_id', '=', False)],
                order='id ASC',
                offset=lease_management_report.interest_amort_limit,
                limit=end_limit)
        # compute interest and amortization report values
        amortization_datas = self.get_interest_amortization_datas(
            lease_contract_ids, lease_management_report.interest_amort_state,
            lease_management_report.interest_amort_start_date,
            lease_management_report.interest_amort_end_date)
        lease_management_report.report_values_interest_and_amortization += " " + amortization_datas

        if lease_management_report.interest_amort_limit < lease_management_report.end_limit:
            limit += end_limit
            lease_management_report.interest_amort_limit = limit
            # self.lease_reports_cron(end_limit)
            date = fields.Datetime.now()
            schedule = self.env.ref(
                'tasc_lease_management_report.action_lease_reports_update_cron')
            schedule.update({
                'nextcall': date + datetime.timedelta(seconds=10),
            })
        else:
            lease_management_report.interest_amort_limit = lease_management_report.end_limit

    @api.model
    def lease_reports_cron_update(self):
        date = fields.Datetime.now()
        schedule = self.env.ref(
            'tasc_lease_management_report.action_lease_reports')
        schedule.update({
            'nextcall': date + datetime.timedelta(seconds=10),
        })

    @api.model
    def payment_aging_reports_cron_update(self):
        date = fields.Datetime.now()
        schedule = self.env.ref(
            'tasc_lease_management_report.action_payment_aging_report_cron')
        schedule.update({
            'nextcall': date + datetime.timedelta(seconds=10),
        })

    @api.model
    def ll_aging_reports_cron_update(self):
        date = fields.Datetime.now()
        schedule = self.env.ref(
            'tasc_lease_management_report.action_ll_aging_report_cron')
        schedule.update({
            'nextcall': date + datetime.timedelta(seconds=10),
        })

    @api.model
    def ll_rou_reports_cron_update(self):
        date = fields.Datetime.now()
        schedule = self.env.ref(
            'tasc_lease_management_report.action_ll_rou_report_cron')
        schedule.update({
            'nextcall': date + datetime.timedelta(seconds=10),
        })

    def action_ll_rou_reports_cron(self, end_limit):
        lease_management_report = self.env['leasee.management.report'].search(
            [], limit=1)

        ll_rou_limit = lease_management_report.ll_rou_limit
        if lease_management_report.lease_contract_ids:
            lease_contract_ids = self.env['leasee.contract'].search(
                [('id', 'in', lease_management_report.lease_contract_ids.ids),
                 ('parent_id', '=', False)
                 ])
        else:
            lease_contract_ids = self.env['leasee.contract'].search(
                [('parent_id', '=', False)],
                order='id ASC',
                offset=lease_management_report.ll_rou_limit,
                limit=end_limit)
        # compute ll and rou report
        ll_rou_datas = self.get_ll_rou_datas(
            lease_contract_ids, lease_management_report.ll_rou_state,
            lease_management_report.ll_rou_as_of_date)
        lease_management_report.report_values_ll_rou += ll_rou_datas
        if lease_management_report.ll_rou_limit < lease_management_report.end_limit:
            ll_rou_limit += end_limit
            lease_management_report.ll_rou_limit = ll_rou_limit
            # self.action_ll_rou_reports_cron(end_limit)
            date = fields.Datetime.now()
            schedule = self.env.ref(
                'tasc_lease_management_report.action_ll_rou_report_cron_update')
            schedule.update({
                'nextcall': date + datetime.timedelta(seconds=10),
            })
        else:
            lease_management_report.ll_rou_limit = lease_management_report.end_limit

    def action_payment_aging_reports_cron(self, end_limit):
        lease_management_report = self.env['leasee.management.report'].search(
            [], limit=1)

        # payment_aging_limit = lease_management_report.payment_aging_limit
        if lease_management_report.lease_contract_ids:
            lease_contract_ids = self.env['leasee.contract'].search(
                [('id', 'in', lease_management_report.lease_contract_ids.ids),
                 ('parent_id', '=', False)
                 ])
        else:
            lease_contract_ids = self.env['leasee.contract'].search(
                [('parent_id', '=', False)],
                order='id ASC',
                offset=lease_management_report.payment_aging_limit,
                limit=end_limit)

        # compute payment aging report
        payment_aging_datas = self.get_payment_aging_datas(
            lease_contract_ids,
            lease_management_report.payment_aging_as_of_date)
        lease_management_report.report_values_payment_aging += payment_aging_datas

        if lease_management_report.payment_aging_limit < lease_management_report.end_limit:
            rem = lease_management_report.end_limit - lease_management_report.payment_aging_limit
            if rem < end_limit:
                lease_management_report.payment_aging_limit += rem
            else:
                lease_management_report.payment_aging_limit += end_limit
            # self.action_payment_aging_reports_cron(end_limit)
            date = fields.Datetime.now()
            schedule = self.env.ref(
                'tasc_lease_management_report.action_payment_aging_report_cron_update')
            schedule.update({
                'nextcall': date + datetime.timedelta(seconds=10),
            })
        else:
            lease_management_report.payment_aging_limit = lease_management_report.end_limit

    def action_ll_aging_reports_cron(self, end_limit):
        lease_management_report = self.env['leasee.management.report'].search(
            [], limit=1)

        ll_aging_limit = lease_management_report.ll_aging_limit
        if lease_management_report.lease_contract_ids:
            lease_contract_ids = self.env['leasee.contract'].search(
                [('id', 'in', lease_management_report.lease_contract_ids.ids),
                 ('parent_id', '=', False)
                 ])
        else:
            lease_contract_ids = self.env['leasee.contract'].search(
                [('parent_id', '=', False)],
                order='id ASC',
                offset=lease_management_report.ll_aging_limit,
                limit=end_limit)

        # compute ll and rou report
        ll_aging_datas = self.get_ll_aging_datas(
            lease_contract_ids,
            lease_management_report.ll_aging_as_of_date)
        lease_management_report.report_values_ll_aging += ll_aging_datas


        if lease_management_report.ll_aging_limit < lease_management_report.end_limit:
            ll_aging_limit += end_limit
            lease_management_report.ll_aging_limit = ll_aging_limit
            # self.action_ll_aging_reports_cron(end_limit)
            date = fields.Datetime.now()
            schedule = self.env.ref(
                'tasc_lease_management_report.action_ll_aging_report_cron_update')
            schedule.update({
                'nextcall': date + datetime.timedelta(seconds=10),
            })
        else:
            lease_management_report.ll_aging_limit = lease_management_report.end_limit

    def get_ll_rou_datas(self, lease_contract_ids, state,
                         end_date):
        data = []
        stll_move_line_ids_qry = []
        ltll_move_line_ids_qry = []
        if lease_contract_ids:
            if state:
                # computation for STLL
                self._cr.execute(
                    'select coalesce((sum(item.debit) - sum(item.credit)), 0) '
                    'total,leasee.name as lease_name,leasee.company_id,'
                    'leasee.external_reference_number,'
                    'currency.name as currency_name,'
                    'project_site.name from leasee_contract '
                    'as leasee inner join account_move as journal on '
                    'journal.leasee_contract_id=leasee.id inner join '
                    'account_move_line as item on item.move_id = journal.id '
                    'inner join res_currency as currency on '
                    'currency.id=leasee.leasee_currency_id left join '
                    'account_analytic_account as project_site on '
                    'project_site.id=leasee.project_site_id '
                    'where leasee.id in %(contract)s and '
                    'journal.date <= %(end_date)s'
                    ' and journal.state=%(state)s and '
                    'item.account_id=leasee.lease_liability_account_id '
                    'group by lease_name,leasee.external_reference_number,'
                    'currency_name,project_site.name,leasee.company_id', {
                        'contract': tuple(lease_contract_ids.ids),
                        'end_date': end_date,
                        'state': state,
                    })
                stll_move_line_ids_qry = self._cr.dictfetchall()

                # computation for LTLL
                self._cr.execute(
                    'select coalesce((sum(item.debit) - sum(item.credit)), 0) total,'
                    'leasee.name as lease_name,leasee.company_id,'
                    'leasee.external_reference_number,'
                    'currency.name as currency_name,'
                    'project_site.name from leasee_contract as '
                    'leasee inner join account_move'
                    ' as journal on '
                    'journal.leasee_contract_id=leasee.id  inner join '
                    'account_move_line as item on '
                    'item.move_id = journal.id inner join '
                    'res_currency as currency on '
                    'currency.id=leasee.leasee_currency_id left join '
                    'account_analytic_account as project_site on '
                    'project_site.id=leasee.project_site_id where '
                    'leasee.id in %(contract)s and '
                    'journal.date <= %(end_date)s and '
                    'journal.state=%(state)s and '
                    'item.account_id=leasee.long_lease_liability_account_id '
                    'group by lease_name,leasee.external_reference_number,'
                    'currency_name,project_site.name,leasee.company_id', {
                        'contract': tuple(lease_contract_ids.ids),
                        'end_date': end_date,
                        'state': state, })
                ltll_move_line_ids_qry = self._cr.dictfetchall()

                # computation for Net ROU
                for contract in lease_contract_ids:
                    tot_asset_amt = 0
                    tot_depr_amt = 0
                    net_rou = 0
                    tot_1 = 0
                    tot_2 = 0
                    asset_move_ids = contract.account_move_ids.ids
                    dep_move_ids = contract.asset_id.depreciation_move_ids.ids
                    if contract.child_ids:
                        asset_move_ids = asset_move_ids + contract.child_ids.mapped(
                            'account_move_ids').ids

                    if contract.asset_id.children_ids:
                        dep_move_ids = dep_move_ids + contract.asset_id.children_ids.mapped(
                            'depreciation_move_ids').ids

                    move_line_ids = self.env[
                        'account.move.line'].search(
                        ['|', ('move_id', 'in', asset_move_ids),
                         ('move_id', 'in', dep_move_ids),
                         ('move_id.date', '<=', end_date),
                         '|', ('account_id', '=',
                               contract.asset_model_id.account_asset_id.id),
                         ('account_id', '=',
                          contract.asset_model_id.account_depreciation_id.id),
                         ('move_id.state', '=', state)])

                    asset_move_line_ids = move_line_ids.filtered(lambda
                                                                     x: x.account_id.id == contract.asset_model_id.account_asset_id.id)
                    tot_asset_amt = sum(
                        asset_move_line_ids.mapped('debit')) - sum(
                        asset_move_line_ids.mapped('credit'))

                    depids = move_line_ids.filtered(lambda
                                                        x: x.account_id.id == contract.asset_model_id.account_depreciation_id.id)
                    depreciation_move_line_ids = depids.filtered(
                        lambda x: x.move_id.asset_remaining_value >= 0)
                    depreciation_move_line_ids_1 = depids.filtered(
                        lambda x: x.move_id.asset_remaining_value < 0)
                    tot_1 = sum(
                        depreciation_move_line_ids.mapped('debit')) + sum(
                        depreciation_move_line_ids.mapped('credit'))
                    tot_2 = sum(
                        depreciation_move_line_ids_1.mapped('debit')) + sum(
                        depreciation_move_line_ids_1.mapped('credit'))

                    tot_depr_amt = tot_1 - tot_2
                    net_rou = tot_asset_amt - tot_depr_amt
                    stll_amount = list(
                        filter(lambda x: x['lease_name'] == contract.name,
                               stll_move_line_ids_qry))
                    ltll_amount = list(
                        filter(lambda x: x['lease_name'] == contract.name,
                               ltll_move_line_ids_qry))

                    if net_rou:
                        data.append({
                            'leasor_name': contract.name,
                            'external_reference_number': contract.external_reference_number if contract.external_reference_number else '',
                            'project_site': contract.project_site_id.name if contract.project_site_id.name else '',
                            'stll': stll_amount[0]['total'] if len(
                                stll_amount) >= 1 else 0.0,
                            'ltll': ltll_amount[0]['total'] if len(
                                ltll_amount) >= 1 else 0.0,
                            'net_rou': net_rou,
                            'currency': contract.leasee_currency_id.name if contract.leasee_currency_id.name else '',
                            'company_id': contract.company_id.id if contract.company_id else '',
                        })

                    else:
                        data.append({
                            'leasor_name': contract.name,
                            'external_reference_number': contract.external_reference_number if contract.external_reference_number else '',
                            'project_site': contract.project_site_id.name if contract.project_site_id.name else '',
                            'stll': stll_amount[0]['total'] if len(
                                stll_amount) >= 1 else 0.0,
                            'ltll': ltll_amount[0]['total'] if len(
                                ltll_amount) >= 1 else 0.0,
                            'net_rou': 0.0,
                            'currency': contract.leasee_currency_id.name if contract.leasee_currency_id.name else '',
                            'company_id': contract.company_id.id if contract.company_id else '',
                        })

            else:
                # computation for STLL
                self._cr.execute(
                    'select coalesce((sum(item.debit) - sum(item.credit)), 0) '
                    'total,leasee.name as lease_name,leasee.company_id,'
                    'leasee.external_reference_number,'
                    'currency.name as '
                    'currency_name,'
                    'project_site.name from leasee_contract '
                    'as leasee inner join account_move as journal on '
                    'journal.leasee_contract_id=leasee.id inner join '
                    'account_move_line as item on item.move_id = journal.id '
                    ' inner join '
                    'res_currency as currency on '
                    'currency.id=leasee.leasee_currency_id left join '
                    'account_analytic_account as project_site on '
                    'project_site.id=leasee.project_site_id where '
                    'leasee.id in %(contract)s and '
                    'journal.date <= %(end_date)s and '
                    'item.account_id=leasee.lease_liability_account_id '
                    'group by lease_name,leasee.external_reference_number,'
                    'currency_name,project_site.name,leasee.company_id', {
                        'contract': tuple(lease_contract_ids.ids),
                        'end_date': end_date,
                    })
                stll_move_line_ids_qry = self._cr.dictfetchall()

                # computation for LTLL
                self._cr.execute(
                    'select coalesce((sum(item.debit) - sum(item.credit)), 0) total,'
                    'leasee.name as lease_name,leasee.company_id,'
                    'leasee.external_reference_number,'
                    'currency.name as currency_name,'
                    'project_site.name from leasee_contract as '
                    'leasee inner join account_move as journal on '
                    'journal.leasee_contract_id=leasee.id  inner join '
                    'account_move_line as item on item.move_id=journal.id'
                    ' inner join '
                    'res_currency as currency on '
                    'currency.id=leasee.leasee_currency_id left join '
                    'account_analytic_account as project_site on '
                    'project_site.id=leasee.project_site_id where '
                    'leasee.id in %(contract)s and '
                    'journal.date <= %(end_date)s '
                    'and '
                    'item.account_id=leasee.long_lease_liability_account_id '
                    'group by lease_name,leasee.external_reference_number,'
                    'currency_name,project_site.name,leasee.company_id',
                    {
                        'contract': tuple(lease_contract_ids.ids),
                        'end_date': end_date,
                        })
                ltll_move_line_ids_qry = self._cr.dictfetchall()
                # computation for Net ROU

                for contract in lease_contract_ids:
                    tot_asset_amt = 0
                    tot_depr_amt = 0
                    net_rou = 0
                    tot_1 = 0
                    tot_2 = 0
                    asset_move_ids = contract.account_move_ids.ids
                    dep_move_ids = contract.asset_id.depreciation_move_ids.ids
                    if contract.child_ids:
                        asset_move_ids = asset_move_ids + contract.child_ids.mapped(
                            'account_move_ids').ids
                    if contract.asset_id.children_ids:
                        dep_move_ids = dep_move_ids + contract.asset_id.children_ids.mapped(
                            'depreciation_move_ids').ids
                    move_line_ids = self.env[
                        'account.move.line'].search(
                        ['|', ('move_id', 'in', asset_move_ids),
                         ('move_id', 'in', dep_move_ids),
                         ('move_id.date', '<=', end_date),
                         '|', ('account_id', '=',
                               contract.asset_model_id.account_asset_id.id),
                         ('account_id', '=',
                          contract.asset_model_id.account_depreciation_id.id)
                         ])

                    asset_move_line_ids = move_line_ids.filtered(lambda
                                                                     x: x.account_id.id == contract.asset_model_id.account_asset_id.id)
                    tot_asset_amt = sum(
                        asset_move_line_ids.mapped('debit')) - sum(
                        asset_move_line_ids.mapped('credit'))
                    depids = move_line_ids.filtered(lambda
                                                        x: x.account_id.id == contract.asset_model_id.account_depreciation_id.id)
                    depreciation_move_line_ids = depids.filtered(
                        lambda x: x.move_id.asset_remaining_value >= 0)

                    depreciation_move_line_ids_1 = depids.filtered(
                        lambda x: x.move_id.asset_remaining_value < 0)

                    tot_1 = sum(
                        depreciation_move_line_ids.mapped('debit')) + sum(
                        depreciation_move_line_ids.mapped('credit'))
                    tot_2 = sum(
                        depreciation_move_line_ids_1.mapped('debit')) + sum(
                        depreciation_move_line_ids_1.mapped('credit'))

                    tot_depr_amt = tot_1 - tot_2
                    net_rou = tot_asset_amt - tot_depr_amt
                    stll_amount = list(
                        filter(lambda x: x['lease_name'] == contract.name,
                               stll_move_line_ids_qry))
                    ltll_amount = list(
                        filter(lambda x: x['lease_name'] == contract.name,
                               ltll_move_line_ids_qry))
                    if net_rou:
                        data.append({
                            'leasor_name': contract.name,
                            'external_reference_number': contract.external_reference_number if contract.external_reference_number else '',
                            'project_site': contract.project_site_id.name if contract.project_site_id.name else '',
                            'stll': stll_amount[0]['total'] if len(
                                stll_amount) >= 1 else 0.0,
                            'ltll': ltll_amount[0]['total'] if len(
                                ltll_amount) >= 1 else 0.0,
                            'net_rou': net_rou,
                            'currency': contract.leasee_currency_id.name if contract.leasee_currency_id.name else '',
                            'company_id': contract.company_id.id if contract.company_id else '',
                        })

                    else:
                        data.append({
                            'leasor_name': contract.name,
                            'external_reference_number': contract.external_reference_number if contract.external_reference_number else '',
                            'project_site': contract.project_site_id.name if contract.project_site_id.name else '',
                            'stll': stll_amount[0]['total'] if len(
                                stll_amount) >= 1 else 0.0,
                            'ltll': ltll_amount[0]['total'] if len(
                                ltll_amount) >= 1 else 0.0,
                            'net_rou': 0.0,
                            'currency': contract.leasee_currency_id.name if contract.leasee_currency_id.name else '',
                            'company_id': contract.company_id.id if contract.company_id else '',
                        })
        str1 = ' '.join(map(str, data))
        return str1

    def get_payment_aging_datas(self, lease_contracts, end_date):
        data = []
        # Less than 1 year
        next_year_date = end_date + dateutil.relativedelta.relativedelta(
            years=1)
        next_year_date = next_year_date - dateutil.relativedelta.relativedelta(
            days=1)

        # 1.01 -  2years
        next_2year_start_date = end_date + dateutil.relativedelta.relativedelta(
            years=1)
        next_2year_end_date = (
                                      end_date + dateutil.relativedelta.relativedelta(
                                  years=2)) - dateutil.relativedelta.relativedelta(
            days=1)

        # 2.01 - 5 years
        start_date_2nd_year = end_date + dateutil.relativedelta.relativedelta(
            years=2)
        end_date_5th_year = (
                                    end_date + dateutil.relativedelta.relativedelta(
                                years=5)) - dateutil.relativedelta.relativedelta(
            days=1)
        # More than 5 years
        start_date_5th_year = end_date + dateutil.relativedelta.relativedelta(
            years=5)
        if lease_contracts:
            # Less than 1 year

            self._cr.execute(
                'select sum(journal.amount_total) total, leasee.id as lease_id,'
                'leasee.name as lease_name,leasee.company_id,'
                'leasee.external_reference_number,currency.name as currency_name,'
                'project_site.name from leasee_contract as leasee inner'
                ' join account_move  as journal on '
                'journal.leasee_contract_id=leasee.id inner join '
                'res_currency as currency on '
                'currency.id=leasee.leasee_currency_id left join '
                'account_analytic_account as project_site on '
                'project_site.id=leasee.project_site_id where '
                'leasee.id in %(contract)s and '
                'journal.invoice_date_due <= %(end_date)s and ' \
                'journal.invoice_date_due >=  %(start_date)s group by ' \
                'lease_id,leasee.external_reference_number,' \
                'currency_name,project_site.name ',
                {'contract': tuple(lease_contracts.ids),
                 'end_date': next_year_date,
                 'start_date': end_date})

            move_ids_next_year_qry = self._cr.dictfetchall()
            less_than_1_year_lease_names = list(
                map(itemgetter('lease_name'), move_ids_next_year_qry))

            # 1.01 -  2years
            self._cr.execute(
                'select sum(journal.amount_total) total, leasee.id as lease_id,'
                'leasee.name as lease_name,leasee.company_id,'
                'leasee.external_reference_number,currency.name as currency_name,'
                'project_site.name from leasee_contract as leasee inner'
                ' join account_move  as journal on '
                'journal.leasee_contract_id=leasee.id inner join '
                'res_currency as currency on '
                'currency.id=leasee.leasee_currency_id left join '
                'account_analytic_account as project_site on '
                'project_site.id=leasee.project_site_id where '
                'leasee.id in %(contract)s and '
                'journal.invoice_date_due <= %(end_date)s and ' \
                'journal.invoice_date_due >=  %(start_date)s group by ' \
                'lease_id,leasee.external_reference_number,' \
                'currency_name,project_site.name ',
                {'contract': tuple(lease_contracts.ids),
                 'end_date': next_2year_end_date,
                 'start_date': next_2year_start_date})

            move_ids_next_two_years_qry = self._cr.dictfetchall()
            one_to_2_year_lease_names = list(
                map(itemgetter('lease_name'), move_ids_next_two_years_qry))

            # 2.01 - 5 years
            self._cr.execute(
                'select sum(journal.amount_total) total, leasee.id as lease_id,'
                'leasee.name as lease_name,leasee.company_id,'
                'leasee.external_reference_number,currency.name as currency_name,'
                'project_site.name from leasee_contract as leasee inner'
                ' join account_move  as journal on '
                'journal.leasee_contract_id=leasee.id inner join '
                'res_currency as currency on '
                'currency.id=leasee.leasee_currency_id left join '
                'account_analytic_account as project_site on '
                'project_site.id=leasee.project_site_id where '
                'leasee.id in %(contract)s and '
                'journal.invoice_date_due <= %(end_date)s and ' \
                'journal.invoice_date_due >=  %(start_date)s group by ' \
                'lease_id,leasee.external_reference_number,' \
                'currency_name,project_site.name ',
                {
                    'contract': tuple(lease_contracts.ids),
                    'end_date': end_date_5th_year,
                    'start_date': start_date_2nd_year})

            move_ids_next_5_years_qry = self._cr.dictfetchall()
            two_to_5_year_lease_names = list(
                map(itemgetter('lease_name'), move_ids_next_5_years_qry))

            # More than 5 years
            self._cr.execute(
                'select sum(journal.amount_total) total, leasee.id as lease_id,'
                'leasee.name as lease_name,leasee.company_id,'
                'leasee.external_reference_number,currency.name as currency_name,'
                'project_site.name from leasee_contract as leasee inner'
                ' join account_move  as journal on '
                'journal.leasee_contract_id=leasee.id inner join '
                'res_currency as currency on '
                'currency.id=leasee.leasee_currency_id left join '
                'account_analytic_account as project_site on '
                'project_site.id=leasee.project_site_id where '
                'leasee.id in %(contract)s and '
                'journal.invoice_date_due >=  %(start_date)s group by ' \
                'lease_id,leasee.external_reference_number,' \
                'currency_name,project_site.name ',
                {
                    'contract': tuple(lease_contracts.ids),
                    'start_date': start_date_5th_year})
            move_ids_more_than_5_years_qry = self._cr.dictfetchall()
            more_than__5_year_lease_names = list(
                map(itemgetter('lease_name'), move_ids_more_than_5_years_qry))
            lease_names = list(
                set(less_than_1_year_lease_names + one_to_2_year_lease_names + two_to_5_year_lease_names + more_than__5_year_lease_names))
            lease_names.sort()

            amount_lists = []
            for lease in lease_names:
                amount_less_than_1_year = list(
                    filter(lambda x: x['lease_name'] == lease,
                           move_ids_next_year_qry))
                amount_1_to_2_year = list(
                    filter(lambda x: x['lease_name'] == lease,
                           move_ids_next_two_years_qry))
                amount_2_to_5_year = list(
                    filter(lambda x: x['lease_name'] == lease,
                           move_ids_next_5_years_qry))
                amount_more_than_5_years = list(
                    filter(lambda x: x['lease_name'] == lease,
                           move_ids_more_than_5_years_qry))

                amount_lists = amount_less_than_1_year + amount_1_to_2_year + amount_2_to_5_year + amount_more_than_5_years
                if len(amount_less_than_1_year) >= 1 and len(
                        amount_1_to_2_year) >= 1 and len(
                    amount_2_to_5_year) >= 1 and len(
                    amount_more_than_5_years) >= 1:
                    data.append({
                        'leasor_name': lease,
                        'external_reference_number': amount_less_than_1_year[0][
                            "external_reference_number"],
                        'project_site': amount_less_than_1_year[0]["name"],
                        'total_amount_next_year': amount_less_than_1_year[0][
                            "total"],
                        'total_amount_next_2years': amount_1_to_2_year[0][
                            "total"],
                        'total_amount_next_5years': amount_2_to_5_year[0][
                            "total"],
                        'total_amount_more_than_5_years':
                            amount_more_than_5_years[0]["total"],
                        'currency': amount_less_than_1_year[0]["currency_name"],
                        'company_id': amount_less_than_1_year[0]["company_id"],
                    })
                else:
                    data.append({
                        'leasor_name': lease,
                        'external_reference_number': amount_lists[0][
                            "external_reference_number"],
                        'project_site': amount_lists[0]["name"],
                        'total_amount_next_year': amount_less_than_1_year[0][
                            "total"] if len(
                            amount_less_than_1_year) >= 1 else 0.0,
                        'total_amount_next_2years': amount_1_to_2_year[0][
                            "total"] if len(amount_1_to_2_year) >= 1 else 0.0,
                        'total_amount_next_5years': amount_2_to_5_year[0][
                            "total"] if len(amount_2_to_5_year) >= 1 else 0.0,
                        'total_amount_more_than_5_years':
                            amount_more_than_5_years[0]["total"] if len(
                                amount_more_than_5_years) >= 1 else 0.0,
                        'currency': amount_lists[0]["currency_name"],
                        'company_id': amount_lists[0]["company_id"],
                    })
        str4 = ' '.join(map(str, data))
        return str4

    def get_ll_aging_datas(self, lease_contract_ids, end_date):
        """Method to compute LL Aging Report data."""
        data = []
        if lease_contract_ids:
            for contract in lease_contract_ids:
                next_year_date = end_date + dateutil.relativedelta.relativedelta(
                    years=1)
                less_than_1_year_start_date = end_date + dateutil.relativedelta.relativedelta(
                    days=1)

                one_to_2year_start_date = end_date + dateutil.relativedelta.relativedelta(
                    years=1)
                one_to_2year_start_date = one_to_2year_start_date + dateutil.relativedelta.relativedelta(
                    days=1)
                one_to_2year_end_date = (
                        end_date + dateutil.relativedelta.relativedelta(
                    years=2))

                start_date_2_to_5_year = end_date + dateutil.relativedelta.relativedelta(
                    years=2)
                start_date_2_to_5_year = start_date_2_to_5_year + dateutil.relativedelta.relativedelta(
                    days=1)
                end_date_2_to_5_year = (
                        end_date + dateutil.relativedelta.relativedelta(
                    years=5))
                start_date_5th_year = end_date + dateutil.relativedelta.relativedelta(
                    years=5)
                start_date_5th_year = start_date_5th_year + dateutil.relativedelta.relativedelta(
                    days=1)
                dep_move_ids = contract.asset_id.depreciation_move_ids.ids
                if contract.child_ids:
                    for children in contract.asset_id.children_ids:
                        dep_move_ids = dep_move_ids + children.depreciation_move_ids.ids
                    move_ids = self.env['account.move'].search(
                        [('leasee_contract_id', '=', contract.id)])
                    interest_move_lines = self.env['account.move.line'].search(
                        ['|', ('move_id', 'in', dep_move_ids),
                         ('move_id', 'in', move_ids.ids),
                         ('move_id.date', '>=', less_than_1_year_start_date),
                         ('move_id.date', '<=', next_year_date), (
                             'account_id', '=',
                             contract.interest_expense_account_id.id)])
                    interest_move_lines_amount = sum(
                        interest_move_lines.mapped('amount_currency'))

                    journal_items_less_than_1_yr_qry = [
                        {'total': interest_move_lines_amount,
                         'leasee_id': contract.id, 'leasee_name': contract.name,
                         'external_reference_number': contract.external_reference_number,
                         'currency_name': contract.leasee_currency_id.name,
                         'name': contract.project_site_id.name}]

                    # Computation for Less than 1 year

                    self._cr.execute('select sum(installment.amount) as total, '
                                     'leasee.id as leasee_id,'
                                     'leasee.name as leasee_name,leasee.company_id from '
                                     'leasee_contract as'
                                     ' leasee inner join leasee_installment as '
                                     'installment on '
                                     'installment.leasee_contract_id=leasee.id where  '
                                     'leasee.id = %(contract)s and '
                                     'installment.date <= %(end_date)s'
                                     ' and installment.date >= %(start_date)s '
                                     'group by leasee_id',
                                     {
                                         'contract': contract.id,
                                         'end_date': next_year_date,
                                         'start_date': less_than_1_year_start_date,
                                     })
                    installments_less_than_1_year_qry = self._cr.dictfetchall()

                    # Computation for 1.01 -2 years

                    interest_move_lines_1_to_2_year = self.env[
                        'account.move.line'].search(
                        ['|', ('move_id', 'in', dep_move_ids),
                         ('move_id', 'in', move_ids.ids),
                         ('move_id.date', '>=', one_to_2year_start_date),
                         ('move_id.date', '<=', one_to_2year_end_date), (
                             'account_id', '=',
                             contract.interest_expense_account_id.id)])
                    interest_move_lines_1_to_2_year_amount = sum(
                        interest_move_lines_1_to_2_year.mapped(
                            'amount_currency'))

                    journal_items_one_to_2_year_qry = [
                        {'total': interest_move_lines_1_to_2_year_amount,
                         'leasee_id': contract.id, 'leasee_name': contract.name,
                         'external_reference_number': contract.external_reference_number,
                         'currency_name': contract.leasee_currency_id.name,
                         'name': contract.project_site_id.name}]

                    self._cr.execute('select sum(installment.amount) as total, '
                                     'leasee.id as leasee_id,'
                                     'leasee.name as leasee_name,leasee.company_id from leasee_contract as'
                                     ' leasee inner join leasee_installment as '
                                     'installment on '
                                     'installment.leasee_contract_id=leasee.id where  '
                                     'leasee.id = %(contract)s and '
                                     'installment.date <= %(end_date)s'
                                     ' and installment.date >= %(start_date)s '
                                     'group by leasee_id',
                                     {
                                         'contract': contract.id,
                                         'end_date': one_to_2year_end_date,
                                         'start_date': one_to_2year_start_date,
                                     })
                    installments_one_to_2_year_qry = self._cr.dictfetchall()

                    # Computation for 2.01 -5 years
                    interest_move_lines_2_to_5_year = self.env[
                        'account.move.line'].search(
                        ['|', ('move_id', 'in', dep_move_ids),
                         ('move_id', 'in', move_ids.ids),
                         ('move_id.date', '>=', start_date_2_to_5_year),
                         ('move_id.date', '<=', end_date_2_to_5_year), (
                             'account_id', '=',
                             contract.interest_expense_account_id.id)])
                    interest_move_lines_2_to_5_year_amount = sum(
                        interest_move_lines_2_to_5_year.mapped(
                            'amount_currency'))

                    journal_items_2_to_5_year_qry = [
                        {'total': interest_move_lines_2_to_5_year_amount,
                         'leasee_id': contract.id, 'leasee_name': contract.name,
                         'external_reference_number': contract.external_reference_number,
                         'currency_name': contract.leasee_currency_id.name,
                         'name': contract.project_site_id.name}]

                    self._cr.execute('select sum(installment.amount) as total, '
                                     'leasee.id as leasee_id,'
                                     'leasee.name as leasee_name,leasee.company_id from leasee_contract as'
                                     ' leasee inner join leasee_installment as '
                                     'installment on '
                                     'installment.leasee_contract_id=leasee.id where  '
                                     'leasee.id = %(contract)s and '
                                     'installment.date <= %(end_date)s'
                                     ' and installment.date >= %(start_date)s '
                                     'group by leasee_id',
                                     {
                                         'contract': contract.id,
                                         'end_date': end_date_2_to_5_year,
                                         'start_date': start_date_2_to_5_year,
                                     })
                    installments_2_to_5_year_qry = self._cr.dictfetchall()

                    # Computation for more than 5 years

                    interest_move_lines_more_than_5_year = self.env[
                        'account.move.line'].search(
                        ['|', ('move_id', 'in', dep_move_ids),
                         ('move_id', 'in', move_ids.ids),
                         ('move_id.date', '>=', start_date_5th_year),
                         (
                             'account_id', '=',
                             contract.interest_expense_account_id.id)])
                    interest_move_lines_more_than_5_year_amount = sum(
                        interest_move_lines_more_than_5_year.mapped(
                            'amount_currency'))

                    journal_items_more_than_5_year_qry = [
                        {'total': interest_move_lines_more_than_5_year_amount,
                         'leasee_id': contract.id, 'leasee_name': contract.name,
                         'external_reference_number': contract.external_reference_number,
                         'currency_name': contract.leasee_currency_id.name,
                         'name': contract.project_site_id.name}]

                    self._cr.execute('select sum(installment.amount) as total, '
                                     'leasee.id as leasee_id,'
                                     'leasee.name as leasee_name,leasee.company_id from '
                                     'leasee_contract as'
                                     ' leasee inner join leasee_installment as '
                                     'installment on '
                                     'installment.leasee_contract_id=leasee.id where  '
                                     'leasee.id = %(contract)s and '
                                     ' installment.date >= %(start_date)s '
                                     'group by leasee_id',
                                     {
                                         'contract': contract.id,
                                         'start_date': start_date_5th_year,
                                     })
                    installments_more_than_5_year_qry = self._cr.dictfetchall()

                    if len(installments_less_than_1_year_qry) >= 1 and len(
                            journal_items_less_than_1_yr_qry) >= 1:
                        tot_less_than_1_year = \
                            installments_less_than_1_year_qry[0]["total"] - \
                            journal_items_less_than_1_yr_qry[0]["total"]
                    elif len(installments_less_than_1_year_qry) >= 1:
                        tot_less_than_1_year = \
                            installments_less_than_1_year_qry[0]["total"]
                    elif len(journal_items_less_than_1_yr_qry) >= 1:
                        tot_less_than_1_year = 0 - \
                                               journal_items_less_than_1_yr_qry[
                                                   0]["total"]
                    else:
                        tot_less_than_1_year = 0

                    if len(installments_one_to_2_year_qry) >= 1 and len(
                            journal_items_one_to_2_year_qry) >= 1:
                        total_one_to_two_year = \
                            installments_one_to_2_year_qry[0]["total"] - \
                            journal_items_one_to_2_year_qry[0]["total"]
                    elif len(installments_one_to_2_year_qry) >= 1:
                        total_one_to_two_year = \
                            installments_one_to_2_year_qry[0]["total"]
                    elif len(journal_items_one_to_2_year_qry) >= 1:
                        total_one_to_two_year = 0 - \
                                                journal_items_one_to_2_year_qry[
                                                    0]["total"]
                    else:
                        total_one_to_two_year = 0

                    if len(installments_2_to_5_year_qry) >= 1 and len(
                            journal_items_2_to_5_year_qry) >= 1:
                        total_two_to_five_year = \
                            installments_2_to_5_year_qry[0]["total"] - \
                            journal_items_2_to_5_year_qry[0]["total"]
                    elif len(installments_2_to_5_year_qry) >= 1:
                        total_two_to_five_year = \
                            installments_2_to_5_year_qry[0]["total"]
                    elif len(journal_items_2_to_5_year_qry) >= 1:
                        total_two_to_five_year = 0 - \
                                                 journal_items_2_to_5_year_qry[
                                                     0]["total"]
                    else:
                        total_two_to_five_year = 0

                    if len(installments_more_than_5_year_qry) >= 1 and len(
                            journal_items_more_than_5_year_qry) >= 1:
                        total_more_than_five_year = \
                            installments_more_than_5_year_qry[0]["total"] - \
                            journal_items_more_than_5_year_qry[0]["total"]
                    elif len(installments_more_than_5_year_qry) >= 1:
                        total_more_than_five_year = \
                            installments_more_than_5_year_qry[0]["total"]
                    elif len(journal_items_more_than_5_year_qry) >= 1:
                        total_more_than_five_year = 0 - \
                                                    journal_items_more_than_5_year_qry[
                                                        0]["total"]
                    else:
                        total_more_than_five_year = 0

                    if tot_less_than_1_year > 0 or total_one_to_two_year > 0 or total_two_to_five_year > 0 or total_more_than_five_year > 0:
                        data.append({
                            'leasor_name': contract.name,
                            'external_reference_number': contract.external_reference_number,
                            'project_site': contract.project_site_id.name,
                            'less_than_one_year': tot_less_than_1_year,
                            'one_to_two_year': total_one_to_two_year,
                            'two_to_five_year': total_two_to_five_year,
                            'more_than_five_year': total_more_than_five_year,
                            'currency': contract.leasee_currency_id.name,
                            'company_id': contract.company_id.id,

                        })
                else:
                    # Computation for Less than 1 year
                    self._cr.execute(
                        'select sum(item.amount_currency) as total, '
                        'leasee.id as leasee_id,'
                        'leasee.name as leasee_name,leasee.company_id,'
                        'leasee.external_reference_number,'
                        'currency.name as '
                        'currency_name,project_site.name from '
                        'leasee_contract as leasee inner '
                        'join account_move '
                        'as journal on '
                        'journal.leasee_contract_id= leasee.id or '
                        'journal.asset_id = leasee.asset_id inner join '
                        'account_move_line as item on '
                        'item.move_id = journal.id inner join '
                        'res_currency as currency on'
                        ' currency.id=leasee.leasee_currency_id left join '
                        'account_analytic_account as project_site on '
                        'project_site.id=leasee.project_site_id where '
                        'leasee.id = %(contract)s and '
                        'journal.date <= %(end_date)s and '
                        'journal.date >= %(start_date)s and '
                        'item.account_id=leasee.interest_expense_account_id'
                        ' group by leasee_id,'
                        'leasee.external_reference_number,'
                        'currency_name,project_site.name',
                        {
                            'contract': contract.id,
                            'end_date': next_year_date,
                            'start_date': less_than_1_year_start_date,
                        })
                    journal_items_less_than_1_yr_qry = self._cr.dictfetchall()

                    self._cr.execute('select sum(installment.amount) as total, '
                                     'leasee.id as leasee_id,'
                                     'leasee.name as leasee_name,leasee.company_id from '
                                     'leasee_contract as'
                                     ' leasee inner join leasee_installment as '
                                     'installment on '
                                     'installment.leasee_contract_id=leasee.id where  '
                                     'leasee.id = %(contract)s and '
                                     'installment.date <= %(end_date)s'
                                     ' and installment.date >= %(start_date)s '
                                     'group by leasee_id',
                                     {
                                         'contract': contract.id,
                                         'end_date': next_year_date,
                                         'start_date': less_than_1_year_start_date,
                                     })
                    installments_less_than_1_year_qry = self._cr.dictfetchall()

                    # Computation for 1.01 -2 years

                    self._cr.execute(
                        'select sum(item.amount_currency) as total, '
                        'leasee.id as leasee_id,'
                        'leasee.name as leasee_name,leasee.company_id,'
                        'leasee.external_reference_number,'
                        'currency.name as '
                        'currency_name,project_site.name from '
                        'leasee_contract as leasee inner '
                        'join account_move '
                        'as journal on '
                        'journal.leasee_contract_id= leasee.id or '
                        'journal.asset_id = leasee.asset_id inner join '
                        'account_move_line as item on '
                        'item.move_id = journal.id inner join '
                        'res_currency as currency on'
                        ' currency.id=leasee.leasee_currency_id left join '
                        'account_analytic_account as project_site on '
                        'project_site.id=leasee.project_site_id where '
                        'leasee.id = %(contract)s and '
                        'journal.date <= %(end_date)s and '
                        'journal.date >= %(start_date)s and '
                        'item.account_id=leasee.interest_expense_account_id'
                        ' group by leasee_id,'
                        'leasee.external_reference_number,'
                        'currency_name,project_site.name',
                        {
                            'contract': contract.id,
                            'end_date': one_to_2year_end_date,
                            'start_date': one_to_2year_start_date,
                        })
                    journal_items_one_to_2_year_qry = self._cr.dictfetchall()
                    self._cr.execute('select sum(installment.amount) as total, '
                                     'leasee.id as leasee_id,'
                                     'leasee.name as leasee_name,leasee.company_id from leasee_contract as'
                                     ' leasee inner join leasee_installment as '
                                     'installment on '
                                     'installment.leasee_contract_id=leasee.id where  '
                                     'leasee.id = %(contract)s and '
                                     'installment.date <= %(end_date)s'
                                     ' and installment.date >= %(start_date)s '
                                     'group by leasee_id',
                                     {
                                         'contract': contract.id,
                                         'end_date': one_to_2year_end_date,
                                         'start_date': one_to_2year_start_date,
                                     })
                    installments_one_to_2_year_qry = self._cr.dictfetchall()

                    # Computation for 2.01 -5 years

                    self._cr.execute(
                        'select sum(item.amount_currency) as total, '
                        'leasee.id as leasee_id,'
                        'leasee.name as leasee_name,leasee.company_id,'
                        'leasee.external_reference_number,'
                        'currency.name as '
                        'currency_name,project_site.name from '
                        'leasee_contract as leasee inner '
                        'join account_move '
                        'as journal on '
                        'journal.leasee_contract_id= leasee.id or '
                        'journal.asset_id = leasee.asset_id inner join '
                        'account_move_line as item on '
                        'item.move_id = journal.id inner join '
                        'res_currency as currency on'
                        ' currency.id=leasee.leasee_currency_id left join '
                        'account_analytic_account as project_site on '
                        'project_site.id=leasee.project_site_id where '
                        'leasee.id = %(contract)s and '
                        'journal.date <= %(end_date)s and '
                        'journal.date >= %(start_date)s and '
                        'item.account_id=leasee.interest_expense_account_id'
                        ' group by leasee_id,'
                        'leasee.external_reference_number,'
                        'currency_name,project_site.name',
                        {
                            'contract': contract.id,
                            'end_date': end_date_2_to_5_year,
                            'start_date': start_date_2_to_5_year,
                        })
                    journal_items_2_to_5_year_qry = self._cr.dictfetchall()

                    self._cr.execute('select sum(installment.amount) as total, '
                                     'leasee.id as leasee_id,'
                                     'leasee.name as leasee_name,leasee.company_id from leasee_contract as'
                                     ' leasee inner join leasee_installment as '
                                     'installment on '
                                     'installment.leasee_contract_id=leasee.id where  '
                                     'leasee.id = %(contract)s and '
                                     'installment.date <= %(end_date)s'
                                     ' and installment.date >= %(start_date)s '
                                     'group by leasee_id',
                                     {
                                         'contract': contract.id,
                                         'end_date': end_date_2_to_5_year,
                                         'start_date': start_date_2_to_5_year,
                                     })
                    installments_2_to_5_year_qry = self._cr.dictfetchall()

                    # Computation for more than 5 years

                    self._cr.execute(
                        'select sum(item.amount_currency) as total, '
                        'leasee.id as leasee_id,'
                        'leasee.name as leasee_name,leasee.company_id,'
                        'leasee.external_reference_number,'
                        'currency.name as '
                        'currency_name,project_site.name from '
                        'leasee_contract as leasee inner '
                        'join account_move '
                        'as journal on '
                        'journal.leasee_contract_id= leasee.id or '
                        'journal.asset_id = leasee.asset_id inner join '
                        'account_move_line as item on '
                        'item.move_id = journal.id inner join '
                        'res_currency as currency on'
                        ' currency.id=leasee.leasee_currency_id left join '
                        'account_analytic_account as project_site on '
                        'project_site.id=leasee.project_site_id where '
                        'leasee.id = %(contract)s and '
                        'journal.date >= %(start_date)s and '
                        'item.account_id=leasee.interest_expense_account_id'
                        ' group by leasee_id,'
                        'leasee.external_reference_number,'
                        'currency_name,project_site.name',
                        {
                            'contract': contract.id,
                            'start_date': start_date_5th_year,
                        })
                    journal_items_more_than_5_year_qry = self._cr.dictfetchall()

                    self._cr.execute('select sum(installment.amount) as total, '
                                     'leasee.id as leasee_id,'
                                     'leasee.name as leasee_name,leasee.company_id from '
                                     'leasee_contract as'
                                     ' leasee inner join leasee_installment as '
                                     'installment on '
                                     'installment.leasee_contract_id=leasee.id where  '
                                     'leasee.id = %(contract)s and '
                                     ' installment.date >= %(start_date)s '
                                     'group by leasee_id',
                                     {
                                         'contract': contract.id,
                                         'start_date': start_date_5th_year,
                                     })
                    installments_more_than_5_year_qry = self._cr.dictfetchall()

                    if len(installments_less_than_1_year_qry) >= 1 and len(
                            journal_items_less_than_1_yr_qry) >= 1:
                        tot_less_than_1_year = \
                            installments_less_than_1_year_qry[0]["total"] - \
                            journal_items_less_than_1_yr_qry[0]["total"]
                    elif len(installments_less_than_1_year_qry) >= 1:
                        tot_less_than_1_year = \
                            installments_less_than_1_year_qry[0]["total"]
                    elif len(journal_items_less_than_1_yr_qry) >= 1:
                        tot_less_than_1_year = 0 - \
                                               journal_items_less_than_1_yr_qry[
                                                   0]["total"]
                    else:
                        tot_less_than_1_year = 0

                    if len(installments_one_to_2_year_qry) >= 1 and len(
                            journal_items_one_to_2_year_qry) >= 1:
                        total_one_to_two_year = \
                            installments_one_to_2_year_qry[0]["total"] - \
                            journal_items_one_to_2_year_qry[0]["total"]
                    elif len(installments_one_to_2_year_qry) >= 1:
                        total_one_to_two_year = \
                            installments_one_to_2_year_qry[0]["total"]
                    elif len(journal_items_one_to_2_year_qry) >= 1:
                        total_one_to_two_year = 0 - \
                                                journal_items_one_to_2_year_qry[
                                                    0]["total"]
                    else:
                        total_one_to_two_year = 0

                    if len(installments_2_to_5_year_qry) >= 1 and len(
                            journal_items_2_to_5_year_qry) >= 1:
                        total_two_to_five_year = \
                            installments_2_to_5_year_qry[0]["total"] - \
                            journal_items_2_to_5_year_qry[0]["total"]
                    elif len(installments_2_to_5_year_qry) >= 1:
                        total_two_to_five_year = \
                            installments_2_to_5_year_qry[0]["total"]
                    elif len(journal_items_2_to_5_year_qry) >= 1:
                        total_two_to_five_year = 0 - \
                                                 journal_items_2_to_5_year_qry[
                                                     0]["total"]
                    else:
                        total_two_to_five_year = 0

                    if len(installments_more_than_5_year_qry) >= 1 and len(
                            journal_items_more_than_5_year_qry) >= 1:
                        total_more_than_five_year = \
                            installments_more_than_5_year_qry[0]["total"] - \
                            journal_items_more_than_5_year_qry[0]["total"]
                    elif len(installments_more_than_5_year_qry) >= 1:
                        total_more_than_five_year = \
                            installments_more_than_5_year_qry[0]["total"]
                    elif len(journal_items_more_than_5_year_qry) >= 1:
                        total_more_than_five_year = 0 - \
                                                    journal_items_more_than_5_year_qry[
                                                        0]["total"]
                    else:
                        total_more_than_five_year = 0

                    if tot_less_than_1_year > 0 or total_one_to_two_year > 0 or total_two_to_five_year > 0 or total_more_than_five_year > 0:
                        data.append({
                            'leasor_name': contract.name,
                            'external_reference_number': contract.external_reference_number,
                            'project_site': contract.project_site_id.name,
                            'less_than_one_year': tot_less_than_1_year,
                            'one_to_two_year': total_one_to_two_year,
                            'two_to_five_year': total_two_to_five_year,
                            'more_than_five_year': total_more_than_five_year,
                            'currency': contract.leasee_currency_id.name,
                            'company_id': contract.company_id.id,
                        })
        str2 = ' '.join(map(str, data))
        return str2

    def get_interest_amortization_datas(self, lease_contract_ids, state,
                                        start_date, end_date):
        data = []
        # computation for the interest and amortization
        amortization_datas = []
        interest_move_line_ids = []
        lease_names = []
        if lease_contract_ids:
            if state:
                self._cr.execute(
                    'select coalesce((sum(item.debit) + sum(item.credit)), 0) interest_total,'
                    ' leasee.id as lease_id,leasee.external_reference_number,currency.name as currency_name,'
                    'project_site.name ,leasee.name as lease_name '
                    'from leasee_contract as leasee inner join'
                    ' account_move as journal on '
                    'journal.leasee_contract_id=leasee.id inner join '
                    'account_move_line as item on journal.id= item.move_id '
                    'inner join res_currency as currency on '
                    'currency.id=leasee.leasee_currency_id '
                    'left join account_analytic_account as project_site on'
                    ' project_site.id=leasee.project_site_id  '
                    ' where '
                    'leasee.id in %(contract_ids)s and  '
                    'journal.move_type=%(move_type)s and journal.date >= %(start_date)s and'
                    ' journal.date <= %(end_date)s and journal.state=%(state)s and '
                    'item.account_id = leasee.interest_expense_account_id '
                    'group by lease_id,leasee.external_reference_number,'
                    'currency_name,project_site.name',
                    {'contract_ids': tuple(lease_contract_ids.ids),
                     'move_type': 'entry',
                     'start_date': start_date,
                     'end_date': end_date,
                     'state': state,
                     }
                )
                interest_move_line_ids = self._cr.dictfetchall()
                interest_lease_names = list(
                    map(itemgetter('lease_name'), interest_move_line_ids))
                for contract in lease_contract_ids:
                    amortization_amount = 0
                    dep_move_ids = contract.asset_id.depreciation_move_ids.ids
                    if contract.child_ids:
                        for children in contract.asset_id.children_ids:
                            dep_move_ids = dep_move_ids + children.depreciation_move_ids.ids
                    if contract.asset_id.children_ids:
                        for child in contract.asset_id.children_ids:
                            dep_move_ids = dep_move_ids + child.depreciation_move_ids.ids
                    depreciation_move_line_ids = self.env[
                        'account.move.line'].search(
                        [('move_id', 'in', dep_move_ids),
                         ('move_id.date', '>=', start_date),
                         ('move_id.date', '<=', end_date),
                         ('account_id', '=',
                          contract.asset_model_id.account_depreciation_expense_id.id),
                         ('move_id.state', '=', state)])
                    amortization_amount = sum(
                        depreciation_move_line_ids.mapped('debit')) + sum(
                        depreciation_move_line_ids.mapped('credit'))
                    amortization_datas.append({'lease_id': contract.id,
                                               'lease_name': contract.name,
                                               'amortization_total': amortization_amount,
                                               'external_reference_number': contract.external_reference_number,
                                               'name': contract.project_site_id.name,
                                               'currency_name': contract.leasee_currency_id.name,
                                               'company_id': contract.company_id.id})

                amortization_lease_names = list(
                    map(itemgetter('lease_id'), amortization_datas))
                lease_names = interest_lease_names + amortization_lease_names
                lease_names = list(set(lease_names))
            else:
                self._cr.execute(
                    'select coalesce((sum(item.debit) + sum(item.credit)), 0) interest_total,'
                    ' leasee.id as lease_id ,leasee.external_reference_number,currency.name as currency_name,'
                    'project_site.name,leasee.name as lease_name, leasee.company_id'
                    ' from leasee_contract as leasee inner join'
                    ' account_move as journal on '
                    'journal.leasee_contract_id=leasee.id inner join '
                    'account_move_line as item on journal.id= item.move_id '
                    'inner join res_currency as currency on '
                    'currency.id=leasee.leasee_currency_id left join '
                    'account_analytic_account as project_site '
                    'on project_site.id=leasee.project_site_id '
                    'where '
                    'leasee.id in %(contract_ids)s and  '
                    'journal.move_type=%(move_type)s and journal.date >= %(start_date)s and'
                    ' journal.date <= %(end_date)s and '
                    'item.account_id = leasee.interest_expense_account_id '
                    'group by lease_id,leasee.external_reference_number,'
                    'currency_name,project_site.name',
                    {'contract_ids': tuple(lease_contract_ids.ids),
                     'move_type': 'entry',
                     'start_date': start_date,
                     'end_date': end_date,
                     }
                )

                interest_move_line_ids = self._cr.dictfetchall()
                interest_lease_names = list(
                    map(itemgetter('lease_id'), interest_move_line_ids))
                for contract in lease_contract_ids:
                    amortization_amount = 0
                    dep_move_ids = contract.asset_id.depreciation_move_ids.ids
                    if contract.child_ids:
                        for children in contract.asset_id.children_ids:
                            dep_move_ids = dep_move_ids + children.depreciation_move_ids.ids
                    if contract.asset_id.children_ids:
                        for child in contract.asset_id.children_ids:
                            dep_move_ids = dep_move_ids + child.depreciation_move_ids.ids
                    depreciation_move_line_ids = self.env[
                        'account.move.line'].search(
                        [('move_id', 'in', dep_move_ids),
                         ('move_id.date', '>=', start_date),
                         ('move_id.date', '<=', end_date),
                         ('account_id', '=',
                          contract.asset_model_id.account_depreciation_expense_id.id),
                         ])
                    amortization_amount = sum(
                        depreciation_move_line_ids.mapped('debit')) + sum(
                        depreciation_move_line_ids.mapped('credit'))
                    amortization_datas.append({'lease_id': contract.id,
                                               'lease_name': contract.name,
                                               'amortization_total': amortization_amount,
                                               'external_reference_number': contract.external_reference_number,
                                               'name': contract.project_site_id.name,
                                               'currency_name': contract.leasee_currency_id.name,
                                               'company_id': contract.company_id.id})

                amortization_lease_names = list(
                    map(itemgetter('lease_id'), amortization_datas))
                lease_names = interest_lease_names + amortization_lease_names
                lease_names = list(set(lease_names))
        lease_names.sort()
        for lease in lease_names:
            test = list(filter(lambda x: x['lease_id'] == lease,
                               amortization_datas))
            test1 = list(filter(lambda x: x['lease_id'] == lease,
                                interest_move_line_ids))
            if len(test) >= 1 and len(test1) >= 1:
                data.append({
                    'leasor_name': test[0][
                        "lease_name"] if test[0][
                                             "lease_name"] != '/' else '',
                    'external_reference_number': test[0][
                        "external_reference_number"],
                    'project_site': test[0]["name"],
                    'interest': test1[0]["interest_total"] if test1[0] else 0.0,
                    'amortization': test[0]["amortization_total"] if test[
                        0] else 0.0,
                    'currency': test[0]["currency_name"],
                    'company_id': test[0]["company_id"] if test[0]["company_id"] else '',
                })
            elif len(test) >= 1:
                data.append({
                    'leasor_name': test[0][
                        "lease_name"] if test[0][
                                             "lease_name"] != '/' else '',
                    'external_reference_number': test[0][
                        "external_reference_number"],
                    'project_site': test[0]["name"],
                    'interest': 0.0,
                    'amortization': test[0]["amortization_total"],
                    'currency': test[0]["currency_name"],
                    'company_id': test[0]["company_id"] if test[0][
                        "company_id"] else '',
                })
            elif len(test1) >= 1:
                data.append({
                    'leasor_name': test1[0][
                        "lease_name"] if test1[0][
                                             "lease_name"] != '/' else '',
                    'external_reference_number': test1[0][
                        "external_reference_number"],
                    'project_site': test1[0]["name"],
                    'interest': test1[0]["interest_total"] if test1[0] else 0.0,
                    'amortization': 0.0,
                    'currency': test1[0]["currency_name"],
                    'company_id': test1[0]["company_id"] if test[0][
                        "company_id"] else '',
                })
            else:
                pass
        str1 = ' '.join(map(str, data))
        return str1

    def add_payment_aging_xlsx_sheet(self, report_data, workbook,
                                     STYLE_LINE_Data,
                                     header_format, STYLE_LINE_HEADER):
        self.ensure_one()
        worksheet = workbook.add_worksheet(_('Payment Aging Report'))
        lang = self.env.user.lang
        if lang.startswith('ar_'):
            worksheet.right_to_left()

        row = 0
        col = 0
        worksheet.merge_range(row, row, col, col + 7, _('Payment Aging Report'),
                              STYLE_LINE_HEADER)
        row += 1
        col = 0
        worksheet.write(row, col, _('Lease Name'), header_format)
        col += 1
        worksheet.write(row, col, _('External Reference Number'), header_format)
        col += 1
        worksheet.write(row, col, _('Project Site'), header_format)
        col += 1
        worksheet.write(row, col, _('Less than 1 year'), header_format)
        col += 1
        worksheet.write(row, col, _('1.01 - 2 years'), header_format)
        col += 1
        worksheet.write(row, col, _('2.01  - 5 years'), header_format)
        col += 1
        worksheet.write(row, col, _('More than 5 years'), header_format)
        col += 1
        worksheet.write(row, col, _('Currency'), header_format)
        col += 1
        for line in report_data:
            col = 0
            row += 1
            worksheet.write(row, col, line['leasor_name'], STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['external_reference_number'],
                            STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['project_site'], STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['total_amount_next_year'],
                            STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col,
                            line['total_amount_next_2years'],
                            STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col,
                            line['total_amount_next_5years'],
                            STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col,
                            line['total_amount_more_than_5_years'],
                            STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['currency'], STYLE_LINE_Data)

    def add_xlsx_sheet(self, report_data, workbook, STYLE_LINE_Data,
                       header_format, STYLE_LINE_HEADER):
        self.ensure_one()
        worksheet = workbook.add_worksheet(
            _('Lease Interest and Amortization Report'))
        lang = self.env.user.lang
        if lang.startswith('ar_'):
            worksheet.right_to_left()

        row = 0
        col = 0
        worksheet.merge_range(row, row, col, col + 5,
                              _('Lease Interest and Amortization Report'),
                              STYLE_LINE_HEADER)
        row += 1
        col = 0
        worksheet.write(row, col, _('Lease Name'), header_format)
        col += 1
        worksheet.write(row, col, _('External Reference Number'), header_format)
        col += 1
        worksheet.write(row, col, _('Project Site'), header_format)
        col += 1
        worksheet.write(row, col, _('Interest'), header_format)
        col += 1
        worksheet.write(row, col, _('Amortization'), header_format)
        col += 1
        worksheet.write(row, col, _('Currency'), header_format)
        col += 1
        for line in report_data:
            col = 0
            row += 1
            worksheet.write(row, col, line['leasor_name'], STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['external_reference_number'],
                            STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['project_site'], STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['interest'],
                            STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['amortization'],
                            STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['currency'], STYLE_LINE_Data)

    def add_ll_aging_xlsx_sheet(self, report_data, workbook, STYLE_LINE_Data,
                                header_format, STYLE_LINE_HEADER):
        """ Method to add datas to the LL Aging xlsx report"""
        self.ensure_one()
        worksheet = workbook.add_worksheet(_('LL Aging Report'))
        lang = self.env.user.lang
        if lang.startswith('ar_'):
            worksheet.right_to_left()

        row = 0
        col = 0
        worksheet.merge_range(row, row, col, col + 7,
                              _('LL Aging Report'),
                              STYLE_LINE_HEADER)
        row += 1
        col = 0
        worksheet.write(row, col, _('Lease Name'), header_format)
        col += 1
        worksheet.write(row, col, _('External Reference Number'), header_format)
        col += 1
        worksheet.write(row, col, _('Project Site'), header_format)
        col += 1
        worksheet.write(row, col, _('Less Than 1 year'), header_format)
        col += 1
        worksheet.write(row, col, _('1.01 - 2 years'), header_format)
        col += 1
        worksheet.write(row, col, _('2.01 - 5 years'), header_format)
        col += 1
        worksheet.write(row, col, _('More than 5 years'), header_format)
        col += 1
        worksheet.write(row, col, _('Currency'), header_format)
        col += 1
        for line in report_data:
            col = 0
            row += 1
            worksheet.write(row, col, line['leasor_name'], STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['external_reference_number'],
                            STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['project_site'], STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['less_than_one_year'],
                            STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['one_to_two_year'],
                            STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['two_to_five_year'],
                            STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['more_than_five_year'],
                            STYLE_LINE_Data)
            col += 1
            worksheet.write(row, col, line['currency'], STYLE_LINE_Data)

    def add_ll_rou_xlsx_sheet(self, report_data, workbook, STYLE_LINE_Data,
                              header_format, STYLE_LINE_HEADER):
        self.ensure_one()
        worksheet = workbook.add_worksheet(_('Lease LL & ROU Report'))
        lang = self.env.user.lang
        if lang.startswith('ar_'):
            worksheet.right_to_left()

        row = 0
        col = 0
        worksheet.merge_range(row, row, col, col + 6,
                              _('Lease LL & ROU Report'),
                              STYLE_LINE_HEADER)
        row += 1
        col = 0
        worksheet.write(row, col, _('Lease Name'), header_format)
        col += 1
        worksheet.write(row, col, _('External Reference Number'), header_format)
        col += 1
        worksheet.write(row, col, _('Project Site'), header_format)
        col += 1
        worksheet.write(row, col, _('STLL'), header_format)
        col += 1
        worksheet.write(row, col, _('LTLL'), header_format)
        col += 1
        worksheet.write(row, col, _('Net ROU'), header_format)
        col += 1
        worksheet.write(row, col, _('Currency'), header_format)
        col += 1
        for line in report_data:
            if line['stll'] == 0 and line['ltll'] == 0 and line['net_rou'] == 0:
                pass
            else:
                col = 0
                row += 1
                worksheet.write(row, col, line['leasor_name'], STYLE_LINE_Data)
                col += 1
                worksheet.write(row, col, line['external_reference_number'],
                                STYLE_LINE_Data)
                col += 1
                worksheet.write(row, col, line['project_site'], STYLE_LINE_Data)
                col += 1
                worksheet.write(row, col, line['stll'],
                                STYLE_LINE_Data)
                col += 1
                worksheet.write(row, col, line['ltll'],
                                STYLE_LINE_Data)
                col += 1
                worksheet.write(row, col, line['net_rou'],
                                STYLE_LINE_Data)
                col += 1
                worksheet.write(row, col, line['currency'], STYLE_LINE_Data)
