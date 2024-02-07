# -*- coding: utf-8 -*-

from odoo import fields, http, _
from odoo.exceptions import  MissingError
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, \
    pager as portal_pager, get_records_pager
from odoo.exceptions import AccessError
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
            payslip = PayslipObj.search([('employee_id', '=', employee.id),
                                         ('state', 'in', ['done', 'verify'])])
            payslip_count = len(payslip)
        values.update({
            'payslip_count': payslip_count,
        })
        return values

    @http.route(['/my/payslip', '/my/payslip/page/<int:page>'], type='http',
                methods=['GET', 'POST'],
                auth="user", website=True)
    def portal_my_payslip(self, page=1, date_begin=None, date_end=None,
                          sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        Employee = request.env['hr.employee']
        PayslipObj = request.env['hr.payslip']
        employee = Employee.search([('user_id', '=', request.env.user.id)],
                                   limit=1)
        domain = [('employee_id', '=', employee.id),
                  ('state', 'in', ['done', 'verify'])]

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

    @http.route(['/my/payslip/<int:payslip_id>'], type='http', auth="public",
                website=True)
    def portal_payslip_page(self, payslip_id, report_type=None, access_token=None,
                          message=False, download=False, **kw):
        print("8")
        try:
            payslip_sudo = self._document_check_access('hr.payslip', payslip_id,
                                                     access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        if report_type in ('html', 'pdf', 'text'):
            return self._show_report(model=payslip_sudo, report_type=report_type,
                                     report_ref='hr_payroll.action_report_payslip',
                                     download=download)
        if payslip_sudo:
            now = fields.Date.today()
            if payslip_sudo and request.session.get(
                    'view_payslip_%s' % payslip_sudo.id) != now and request.env.user.share and access_token:
                request.session['view_payslip_%s' % payslip_sudo.id] = now
            print("payslip_sudo",payslip_sudo)
            values = {
                'payslip': payslip_sudo,
                'message': message,
                'token': access_token,
                'bootstrap_formatting': True,
                'report_type': 'html',
                'page_name': 'payslip_form',
            }
            if payslip_sudo.company_id:
                values['res_company'] = payslip_sudo.company_id
            if payslip_sudo.name:
                history = request.session.get('my_contact_history', [])
            values.update(get_records_pager(history, payslip_sudo))
            return request.render('gts_hr_portal.payslip_portal_template',
                                  values)
