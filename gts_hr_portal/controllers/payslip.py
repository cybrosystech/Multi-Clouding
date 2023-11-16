# -*- coding: utf-8 -*-

import binascii
from datetime import date, datetime

from odoo import fields, http, _
from odoo.exceptions import AccessError, MissingError
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, \
    pager as portal_pager, get_records_pager
from odoo.osv import expression
from odoo.exceptions import UserError, AccessError, ValidationError

from odoo.tools import ustr, consteq
import logging

_logger = logging.getLogger(__name__)


class CustomerPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super(CustomerPortal, self)._prepare_home_portal_values(
            counters)
        payslip_count = 0
        Employee = request.env['hr.employee']
        PayslipObj = request.env['hr.payslip']
        employee = Employee.search([('user_id', '=', request.env.user.id)],
                                   limit=1)
        if employee:
            payslip = PayslipObj.search([('employee_id', '=', employee.name)])
            payslip_count = len(payslip)
        values.update({
            'payslip_count': payslip_count,
        })
        return values

    @http.route(['/my/payslip', '/my/payslip/page/<int:page>'], type='http',
                auth="user", website=True)
    def portal_my_payslip(self, page=1, date_begin=None, date_end=None,
                          sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        Employee = request.env['hr.employee']
        PayslipObj = request.env['hr.payslip']
        employee = Employee.search([('user_id', '=', request.env.user.id)],
                                   limit=1)
        domain = [('employee_id', '=', employee.id), ('state', '=', 'done')]

        archive_groups = self._get_archive_groups('hr.payslip',
                                                  domain) if values.get(
            'my_details') else []
        if date_begin and date_end:
            domain += [('create_date', '>', date_begin),
                       ('create_date', '<=', date_end)]

        # count for pager
        payslip_count = PayslipObj.search_count(domain)
        # pager
        pager = portal_pager(
            url="/my/payslip",
            url_args={'date_begin': date_begin, 'date_end': date_end,
                      'sortby': sortby},
            total=payslip_count,
            page=page,
            step=self._items_per_page
        )
        # content according to pager and archive selected
        payslip = PayslipObj.search(domain, limit=self._items_per_page,
                                    offset=pager['offset'])
        request.session['my_payslip_history'] = payslip.ids[:100]
        values.update({
            'date': date_begin,
            'payslip': payslip.sudo(),
            'page_name': 'payslip',
            'pager': pager,
            'archive_groups': archive_groups,
            'default_url': '/my/payslip',
        })
        return request.render("gts_hr_portal.portal_my_payslip", values)

    @http.route('/payslip/pdf', methods=['POST', 'GET'], csrf=False,
                type='http', auth="user", website=True)
    def print_payslip(self, **kw):
        pdf = request.env['hr.payslip'].sudo()._get_pdf_reports()
        pdfhttpheaders = [('Content-Type', 'application/pdf'),
                          ('Content-Length', len(pdf))]
        return request.make_response(pdf, headers=pdfhttpheaders)
