# -*- coding: utf-8 -*-

import binascii
from datetime import date,datetime

from odoo import fields, http, _
from odoo.exceptions import AccessError, MissingError
from odoo.http import request
# from odoo.addons.payment.controllers.portal import PaymentProcessing
# from odoo.addons.portal.controllers.mail import _message_post_helper
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager, get_records_pager
from odoo.osv import expression
from odoo.exceptions import UserError, AccessError, ValidationError

from odoo.tools import ustr, consteq
import logging
_logger = logging.getLogger(__name__)


class CustomerPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super(CustomerPortal, self)._prepare_home_portal_values(counters)
        leaves_count = 0
        Employee = request.env['hr.employee']
        LeaveObj = request.env['hr.leave']
        employee = Employee.search([('user_id', '=', request.env.user.id)], limit=1)
        if employee:
            leaves = LeaveObj.search([('employee_id', '=', employee.name)])  # ('state', '=', 'validate')
            leaves_count = len(leaves)
        values.update({
            'leaves_count': leaves_count,
        })
        return values


    @http.route(['/my/leaves', '/my/leaves/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_leaves(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        Employee = request.env['hr.employee']
        LeaveObj = request.env['hr.leave']
        employee = Employee.search([('user_id', '=', request.env.user.id)], limit=1)
        if not employee:
            return request.render("gts_hr_portal.leave_employee_not_found", values)
        domain = [('employee_id', '=', employee.id)]
        searchbar_sortings = {
            'date': {'label': _('Leave Date'), 'order': 'request_date_from desc'},
            'name': {'label': _('Leave Type'), 'order': 'holiday_status_id'},
            'stage': {'label': _('Stage'), 'order': 'state'},
        }
        if not sortby:
            sortby = 'date'
        sort_order = searchbar_sortings[sortby]['order']

        archive_groups = self._get_archive_groups('hr.leave', domain) if values.get('my_details') else []
        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]

        # count for pager
        leaves_count = LeaveObj.search_count(domain)
        # pager
        pager = portal_pager(
            url="/my/leaves",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=leaves_count,
            page=page,
            step=self._items_per_page
        )
        # content according to pager and archive selected
        leaves = LeaveObj.search(domain, order=sort_order, limit=self._items_per_page, offset=pager['offset'])
        request.session['my_leaves_history'] = leaves.ids[:100]

        values.update({
            'date': date_begin,
            'leaves': leaves.sudo(),
            'page_name': 'leave',
            'pager': pager,
            'archive_groups': archive_groups,
            'default_url': '/my/leaves',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
        })
        return request.render("gts_hr_portal.portal_my_leaves", values)

    @http.route(['/my/leaves/<int:leave_id>'], type='http', auth="public", website=True)
    def portal_leave_page(self, leave_id, report_type=None, access_token=None, message=False, download=False, **kw):
        try:
            leave_sudo = self._document_check_access('hr.leave', leave_id, access_token=access_token)
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
        employee = request.env['hr.employee'].search([('user_id', '=', request.env.user.id)], limit=1)
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
        employee = Employee.search([('user_id', '=', request.env.user.id)], limit=1)
        values['validation_errors'] = {}
        leave_data = self._leave_cleanup_data(values)
        leave_data_copy = leave_data.copy()
        validation_errors = self._leave_new_validate_data(values)
        leave = False
        if not validation_errors and request.httprequest.method == 'POST':
            try:
                request_date_from = datetime.strptime(leave_data_copy.get('request_date_from'), '%Y-%m-%d')
                request_date_to = datetime.strptime(leave_data_copy.get('request_date_to'), '%Y-%m-%d')
                leave_data_copy['number_of_days'] = LeaveObj._get_number_of_days (request_date_from ,request_date_to,leave_data_copy.get('employee_id'))['days']+1
                # print("hhhhhhhhh",leave_data_copy)
                leave = LeaveObj.create(leave_data_copy)
            except (UserError, AccessError, ValidationError) as exc:
                _logger.error(_("Error 1 while creating leave: %s ") % exc)
                validation_errors.update({'error': {'error_text': exc}})
                values['validation_errors'] = validation_errors
                values = self._leave_get_default_data(employee, values)
                _logger.error(_("Error 1 while creating leave: %s ") % exc)
            except Exception as e:
                _logger.error(_("Error 2 while creating leave: %s ") % e)
                validation_errors.update({'error': {'error_text': _("Unknown server error: %s ") % e}})
                values['validation_errors'] = validation_errors
                values = self._leave_get_default_data(employee, values)
            else:
                return request.render("gts_hr_portal.leave_thankyou", {'employee': employee, 'leave': leave.sudo()})
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
        # if post.get('request_date_from', False):
        #     if post.get('request_date_from', False) < str(today):
        #         errors.update({'request_date_from': {'error_text': _("Date from is less than today!")}})
        # if post.get('request_date_to', False):
        #     if post.get('request_date_to', False) < str(today):
        #         errors.update({'request_date_from': {'error_text': _("Date to is less than today!")}})
        if post.get('request_date_from', False) and post.get('request_date_to', False):
            if post.get('request_date_from', False) > post.get('request_date_to', False):
                errors.update({'request_date_from': {'error_text': _("Date From must be less than Date To!")}})
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

    @http.route(['/get/employee/leaves/count/<int:employee_id>/<int:holiday_status_id>'],
                type='json', auth="public", methods=['POST'], website=True)
    def get_leaves_count(self, employee_id, holiday_status_id, **kw):
        print('employee_id, holiday_status_id....', employee_id, holiday_status_id)
        remaining_leaves = 0
        leave_type = request.env['hr.leave.type'].search([('id', '=', int(holiday_status_id))])
        if leave_type:
            employee = request.env['hr.leave.type'].search([('id', '=', int(employee_id))])
            if employee:
                # remaining_leaves = leave_type.with_context(employee_id=employee_id).remaining_leaves
                remaining_leaves = leave_type.with_context(employee_id=employee_id)._compute_leaves()
        print('remaining_leaves....', remaining_leaves)
        return remaining_leaves

    # @http.route(['/my/orders/<int:leave_id>/accept'], type='json', auth="public", website=True)
    # def portal_quote_accept(self, leave_id, access_token=None, name=None, signature=None):
    #     # get from query string if not on json param
    #     access_token = access_token or request.httprequest.args.get('access_token')
    #     try:
    #         leave_sudo = self._document_check_access('hr.leave', leave_id, access_token=access_token)
    #     except (AccessError, MissingError):
    #         return {'error': _('Invalid order.')}
    #
    #     if not leave_sudo.has_to_be_signed():
    #         return {'error': _('The order is not in a state requiring customer signature.')}
    #     if not signature:
    #         return {'error': _('Signature is missing.')}
    #
    #     try:
    #         leave_sudo.write({
    #             'signed_by': name,
    #             'signed_on': fields.Datetime.now(),
    #             'signature': signature,
    #         })
    #         request.env.cr.commit()
    #     except (TypeError, binascii.Error) as e:
    #         return {'error': _('Invalid signature data.')}
    #
    #     if not leave_sudo.has_to_be_paid():
    #         leave_sudo.action_confirm()
    #         leave_sudo._send_order_confirmation_mail()
    #
    #     pdf = request.env.ref('sale.action_report_saleorder').sudo().render_qweb_pdf([leave_sudo.id])[0]
    #
    #     _message_post_helper(
    #         'hr.leave', leave_sudo.id, _('Order signed by %s') % (name,),
    #         attachments=[('%s.pdf' % leave_sudo.name, pdf)],
    #         **({'token': access_token} if access_token else {}))
    #
    #     query_string = '&message=sign_ok'
    #     if leave_sudo.has_to_be_paid(True):
    #         query_string += '#allow_payment=yes'
    #     return {
    #         'force_refresh': True,
    #         'redirect_url': leave_sudo.get_portal_url(query_string=query_string),
    #     }
    #
    # @http.route(['/my/orders/<int:leave_id>/decline'], type='http', auth="public", methods=['POST'], website=True)
    # def decline(self, leave_id, access_token=None, **post):
    #     try:
    #         leave_sudo = self._document_check_access('hr.leave', leave_id, access_token=access_token)
    #     except (AccessError, MissingError):
    #         return request.redirect('/my')
    #
    #     message = post.get('decline_message')
    #
    #     query_string = False
    #     if leave_sudo.has_to_be_signed() and message:
    #         leave_sudo.action_cancel()
    #         _message_post_helper('hr.leave', leave_id, message, **{'token': access_token} if access_token else {})
    #     else:
    #         query_string = "&message=cant_reject"
    #
    #     return request.redirect(leave_sudo.get_portal_url(query_string=query_string))
