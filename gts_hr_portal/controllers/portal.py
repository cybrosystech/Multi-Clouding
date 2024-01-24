# -*- coding: utf-8 -*-

from datetime import datetime
from odoo import fields, http, _
from odoo.exceptions import MissingError
from odoo.http import request
from odoo.tools import groupby as groupbyelem
from operator import itemgetter
from odoo.addons.portal.controllers.portal import CustomerPortal, \
    pager as portal_pager, get_records_pager
from odoo.exceptions import UserError, AccessError, ValidationError
import logging

_logger = logging.getLogger(__name__)


class CustomerPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super(CustomerPortal, self)._prepare_home_portal_values(
            counters)
        leaves_count = 0
        Employee = request.env['hr.employee']
        LeaveObj = request.env['hr.leave']
        employee = Employee.search([('user_id', '=', request.env.user.id)],
                                   limit=1)
        if employee:
            leaves = LeaveObj.search(
                ['|', '|', ('employee_id', '=', employee.id),
                 ('employee_id.parent_id', '=', employee.id),
                 ('employee_id.leave_manager_id', '=', employee.user_id.id)])
            leaves_count = len(leaves)
        values.update({
            'leaves_count': leaves_count,
        })
        return values

    @http.route(['/approve/leave/<int:leave_id>'], type='http',
                auth="user", website=True)
    def approve_leave(self, leave_id, page=1, **kw):
        leave = request.env['hr.leave'].browse(leave_id)
        leave.state = 'validate1'
        leave.is_manager_approved = True
        request.render("gts_hr_portal.portal_my_leaves")
        employee = leave.employee_id.id
        return request.render("gts_hr_portal.leave_approve",
                              {'employee': employee,
                               'leave': leave.sudo()})

    @http.route(['/approve/leave/manager/<int:leave_id>'], type='http',
                auth="user", website=True)
    def approve_leave_timeoff_approver(self, leave_id, page=1, **kw):
        leave = request.env['hr.leave'].browse(leave_id)
        leave.sudo().state = 'validate'
        employee = leave.employee_id.id
        return request.render("gts_hr_portal.leave_approve",
                              {'employee': employee,
                               'leave': leave.sudo()})

    @http.route(['/refuse/leave/<int:leave_id>'], type='http',
                auth="user", website=True)
    def refuse_leave(self, leave_id, page=1, **kw):
        leave = request.env['hr.leave'].browse(leave_id)
        leave.state = 'refuse'
        leave.is_manager_approved = False
        employee = leave.employee_id.id
        return request.render("gts_hr_portal.leave_refuse",
                              {'employee': employee,
                               'leave': leave.sudo()})

    @http.route(['/refuse_leave_manager/<int:leave_id>'], type='http',
                auth="user", website=True)
    def refuse_leave_timeoff_approver(self, leave_id, page=1, **kw):
        leave = request.env['hr.leave'].browse(leave_id)
        leave.state = 'refuse'
        leave.is_manager_approved = False
        employee = leave.employee_id.id
        return request.render("gts_hr_portal.leave_refuse",
                              {'employee': employee,
                               'leave': leave.sudo()})

    @http.route(['/my/leaves', '/my/leaves/page/<int:page>'], type='http',
                auth="user", website=True)
    def portal_my_leaves(self, page=1, date_begin=None, date_end=None,
                         sortby=None, groupby='none', filterby=None, **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        Employee = request.env['hr.employee']
        LeaveObj = request.env['hr.leave']
        employee = Employee.search([('user_id', '=', request.env.user.id)],
                                   limit=1)
        if not employee:
            return request.render("gts_hr_portal.leave_employee_not_found",
                                  values)
        domain = ['|', '|', ('employee_id', '=', employee.id),
                  ('employee_id.parent_id', '=', employee.id),
                  ('employee_id.leave_manager_id', '=', employee.user_id.id),
                  ]
        # if not filterby:
        #     filterby = 'all'

        searchbar_sortings = {
            'date': {'label': _('Leave Date'),
                     'order': 'request_date_from desc'},
            'name': {'label': _('Leave Type'), 'order': 'holiday_status_id'},
            'stage': {'label': _('Stage'), 'order': 'state'},
        }
        if not sortby:
            sortby = 'date'
        sort_order = searchbar_sortings[sortby]['order']

        archive_groups = self._get_archive_groups('hr.leave',
                                                  domain) if values.get(
            'my_details') else []
        if date_begin and date_end:
            domain += [('create_date', '>', date_begin),
                       ('create_date', '<=', date_end)]

        # count for pager
        leaves_count = LeaveObj.search_count(domain)
        # pager
        pager = portal_pager(
            url="/my/leaves",
            url_args={'date_begin': date_begin, 'date_end': date_end,
                      'sortby': sortby},
            total=leaves_count,
            page=page,
            step=self._items_per_page
        )
        # content according to pager and archive selected
        leaves = LeaveObj.search(domain, order=sort_order,
                                 limit=self._items_per_page,
                                 offset=pager['offset'])
        request.session['my_leaves_history'] = leaves.ids[:100]
        total_leaves = request.env['hr.leave.report'].search(
            [('employee_id.user_id', '=', request.env.user.id),
             ('leave_type', '=', 'allocation'),
             ('state', '=', 'validate')]).mapped('number_of_days')
        tot_allocated_leaves = sum(total_leaves)
        leave_taken = request.env['hr.leave.report'].search(
            [('employee_id.user_id', '=', request.env.user.id),
             ('leave_type', '!=', 'allocation'),
             ('state', '=', 'validate')]).mapped('number_of_days')
        tot_leave_taken = round(sum(leave_taken), 2)
        balance_leave = tot_allocated_leaves - abs(tot_leave_taken)

        searchbar_groupby = {
            'none': {'input': 'none', 'label': _('All')},
            'state': {'input': 'state', 'label': _('State')},

        }
        if groupby == 'state':
            grouped_leave = [request.env['hr.leave'].concat(*g) for k, g in
                               groupbyelem(leaves, itemgetter('state'))]
        else:
            grouped_leave = [leaves]
        values.update({
            'date': date_begin,
            'leaves': leaves.sudo(),
            'grouped_leave':grouped_leave,
            'page_name': 'leave',
            'pager': pager,
            'archive_groups': archive_groups,
            'default_url': '/my/leaves',
            'searchbar_sortings': searchbar_sortings,
            'searchbar_groupby': searchbar_groupby,
            'sortby': sortby,
            'groupby': groupby,
            'tot_allocated_leaves': tot_allocated_leaves,
            'tot_leave_taken': tot_leave_taken,
            'balance_leave': balance_leave,
        })
        return request.render("gts_hr_portal.portal_my_leaves", values)

    @http.route(['/my/leaves/<int:leave_id>'], type='http', auth="public",
                website=True)
    def portal_leave_page(self, leave_id, report_type=None, access_token=None,
                          message=False, download=False, **kw):
        try:
            leave_sudo = self._document_check_access('hr.leave', leave_id,
                                                     access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my/leaves')

        values = {
            'leave': leave_sudo,
            'message': message,
            'token': access_token,
            'return_url': '/my/leaves',
            'bootstrap_formatting': True,
            'employee_id': leave_sudo.employee_id.id,
            'report_type': 'html',
        }

        history = request.session.get('my_leaves_history', [])
        values.update(get_records_pager(history, leave_sudo))

        return request.render('gts_hr_portal.view_my_hr_leave', values)

    @http.route(['/leave/apply'], type='http', auth="user", website=True)
    def leaves_apply(self, **kwargs):
        # if not job.can_access_from_current_website():
        #     raise NotFound()
        leave_types = request.env['hr.leave.type'].search([])
        employee = request.env['hr.employee'].search(
            [('user_id', '=', request.env.user.id)], limit=1)
        if not employee:
            return request.render("gts_hr_portal.leave_employee_not_found", {})
        error = {}
        default = {}
        if 'website_hr_recruitment_error' in request.session:
            error = request.session.pop('website_hr_recruitment_error')
            default = request.session.pop('website_hr_recruitment_default')
        values = {
            'employee': employee,
            'employee_name': employee.name,
            'leave_types': leave_types,
            'error': error,
            'default': default,
            # 'token': access_token,
            'return_url': '/my/leaves',
            'bootstrap_formatting': True,
        }
        return request.render("gts_hr_portal.leave_apply", values)

    @http.route(["/leave/new/data"], type='http', auth="user",
                methods=['GET', 'POST'], website=True)
    def leave_create_new(self, **kwargs):
        values = kwargs
        today = fields.Date.today()
        _logger.info("today : %s" % today)
        Employee = request.env['hr.employee']
        LeaveObj = request.env['hr.leave']
        employee = Employee.search([('user_id', '=', request.env.user.id)],
                                   limit=1)
        values['validation_errors'] = {}
        leave_data = self._leave_cleanup_data(values)
        leave_data_copy = leave_data.copy()
        validation_errors = self._leave_new_validate_data(values)
        leave = False
        if not validation_errors and request.httprequest.method == 'POST':
            try:
                request_date_from = datetime.strptime(
                    leave_data_copy.get('request_date_from'), '%Y-%m-%d')
                request_date_to = datetime.strptime(
                    leave_data_copy.get('request_date_to'), '%Y-%m-%d')
                leave_data_copy['number_of_days'] = \
                    LeaveObj._get_number_of_days(request_date_from,
                                                 request_date_to,
                                                 leave_data_copy.get(
                                                     'employee_id'))['days'] + 1
                leave = LeaveObj.create(leave_data_copy)
                template = request.env.ref(
                    'gts_hr_portal.email_template_leave_request')
                template.with_context(date_from=leave.date_from.date(),date_to=leave.date_to.date(), state=leave.state).send_mail(leave.id,
                                   force_send=True)
            except (UserError, AccessError, ValidationError) as exc:
                _logger.error(_("Error 1 while creating leave: %s ") % exc)
                validation_errors.update({'error': {'error_text': exc}})
                values['validation_errors'] = validation_errors
                values = self._leave_get_default_data(employee, values)
                _logger.error(_("Error 1 while creating leave: %s ") % exc)
            except Exception as e:
                _logger.error(_("Error 2 while creating leave: %s ") % e)
                validation_errors.update({'error': {
                    'error_text': _("Unknown server error: %s ") % e}})
                values['validation_errors'] = validation_errors
                values = self._leave_get_default_data(employee, values)
            else:
                return request.render("gts_hr_portal.leave_thankyou",
                                      {'employee': employee,
                                       'leave': leave.sudo()})
        else:
            values['validation_errors'] = validation_errors
            values.update(leave_data)
            values = self._leave_get_default_data(employee, values)



        return request.render("gts_hr_portal.leave_apply", values)

    def _leave_get_default_data(self, employee, values):
        leave_types = request.env['hr.leave.type'].search([])
        values.update({
            'employee': employee,
            'employee_name': employee.name,
            'leave_types': leave_types,
        })
        return values

    def _leave_new_validate_data(self, post):
        errors = {}
        today = fields.Date.today()
        if post.get('request_date_from', False) and post.get('request_date_to',
                                                             False):
            if post.get('request_date_from', False) > post.get(
                    'request_date_to', False):
                errors.update({'request_date_from': {
                    'error_text': _("Date From must be less than Date To!")}})
        return errors

    def _leave_cleanup_data(self, values):
        cleanup_columns = ['employee_name', 'validation_errors']
        for column_name in cleanup_columns:
            if column_name in values:
                values.pop(column_name)
        if values.get('employee_id'):
            values['employee_id'] = int(values.get('employee_id'))
        if values.get('holiday_status_id'):
            values['holiday_status_id'] = int(values.get('holiday_status_id'))
        if values.get('request_date_from'):
            values['date_from'] = values.get('request_date_from')
            values['date_to'] = values.get('request_date_to')
        return values

    @http.route([
        '/get/employee/leaves/count/<int:employee_id>/<int:holiday_status_id>'],
        type='json', auth="public", methods=['POST'], website=True)
    def get_leaves_count(self, employee_id, holiday_status_id, **kw):
        remaining_leaves = 0
        leave_type = request.env['hr.leave.type'].search(
            [('id', '=', int(holiday_status_id))])
        if leave_type:
            employee = request.env['hr.leave.type'].search(
                [('id', '=', int(employee_id))])
            if employee:
                remaining_leaves = leave_type.with_context(
                    employee_id=employee_id)._compute_leaves()
        return remaining_leaves
