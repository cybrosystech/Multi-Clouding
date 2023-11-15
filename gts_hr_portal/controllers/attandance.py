    # -*- coding: utf-8 -*-

from datetime import date,datetime
from odoo import fields, http, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager, get_records_pager
import logging
_logger = logging.getLogger(__name__)


class CustomerPortal(CustomerPortal):


    def _prepare_home_portal_values(self, counters):
        values = super(CustomerPortal, self)._prepare_home_portal_values(counters)
        attendances_count = 0
        Employee = request.env['hr.employee']
        attendance_obj = request.env['hr.attendance']
        employee = Employee.search([('user_id', '=', request.env.user.id)], limit=1)
        if employee:
            attendances = attendance_obj.search([('employee_id', '=', employee.name)])  # ('state', '=', 'validate')
            attendances_count = len(attendances)
        values.update({
            'attendances_count': attendances_count,
        })
        return values

    @http.route(['/my/attandance', '/my/attandance/page/<int:page>'], type='http', auth="public", website=True)
    def portal_attendance_page(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        Employee = request.env['hr.employee']
        attendance_obj = request.env['hr.attendance']
        employee = Employee.search([('user_id', '=', request.env.user.id)], limit=1)
        domain = [('employee_id', '=', employee.id)]
        is_check_in = False
        is_check_out = False
        if not sortby:
            sortby = 'date'
        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]

        # count for pager
        attendance_count = attendance_obj.search_count(domain)
        # pager
        pager = portal_pager(
            url="/my/attandance",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=attendance_count,
            page=page,
            step=self._items_per_page
        )
        # content according to pager and archive selected
        attendances = attendance_obj.search(domain, limit=self._items_per_page, offset=pager['offset'])
        request.session['my_attendance_history'] = attendances.ids[:100]
        for record in attendances:
            if record.check_in:
                if record.check_in.date() == date.today():
                    is_check_in = True
            if record.check_out:
                if record.check_out.date() == date.today():
                    is_check_out = True


        values.update({
            'date': date_begin,
            'attendances': attendances.sudo(),
            'page_name': 'attendance',
            'pager': pager,
            'default_url': '/my/attandance',
            'employee_id':employee.id,
            'is_check_in':is_check_in,
            'is_check_out':is_check_out,
        })
        return request.render("gts_hr_portal.portal_my_attendance", values)