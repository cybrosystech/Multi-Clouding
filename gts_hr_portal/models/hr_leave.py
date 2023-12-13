# -*- coding: utf-8 -*-
import logging

from datetime import datetime, date, timedelta, time
from odoo import api, fields, models, _, SUPERUSER_ID, tools
from odoo.addons.hr_holidays.models.hr_leave import HolidaysRequest
from odoo.exceptions import UserError, AccessError

_logger = logging.getLogger(__name__)


class HolidayRequestMpatch(HolidaysRequest):

    def write(self, values):
        is_officer = self.env.user.has_group(
            'hr_holidays.group_hr_holidays_user') or self.env.is_superuser() or self.employee_id.parent_id or self.employee_id.leave_manager_id

        if not is_officer and values.keys() - {'message_main_attachment_id'}:
            if any(
                    hol.date_from.date() < fields.Date.today() and hol.employee_id.leave_manager_id != self.env.user
                    for hol in self):
                raise UserError(
                    _('You must have manager rights to modify/validate a time off that already begun'))

        employee_id = values.get('employee_id', False)
        if not self.env.context.get('leave_fast_create'):
            if values.get('state'):
                self._check_approval_update(values['state'])
                if any(holiday.validation_type == 'both' for holiday in self):
                    if values.get('employee_id'):
                        employees = self.env['hr.employee'].browse(
                            values.get('employee_id'))
                    else:
                        employees = self.mapped('employee_id')
                    self._check_double_validation_rules(employees,
                                                        values['state'])
            if 'date_from' in values:
                values['request_date_from'] = values['date_from']
            if 'date_to' in values:
                values['request_date_to'] = values['date_to']
        result = super(HolidayRequestMpatch, self).write(values)
        if not self.env.context.get('leave_fast_create'):
            for holiday in self:
                if employee_id:
                    holiday.add_follower(employee_id)
        return result

    def _check_approval_update(self, state):
        """ Check if target state is achievable. """
        if self.env.is_superuser():
            return

        current_employee = self.env.user.employee_id
        is_officer = self.env.user.has_group(
            'hr_holidays.group_hr_holidays_user')
        is_manager = self.env.user.has_group(
            'hr_holidays.group_hr_holidays_manager')

        for holiday in self:
            val_type = holiday.validation_type

            if not is_manager and state != 'confirm':
                if state == 'draft':
                    if holiday.state == 'refuse':
                        raise UserError(
                            _('Only a Time Off Manager can reset a refused leave.'))
                    if holiday.date_from and holiday.date_from.date() <= fields.Date.today():
                        raise UserError(
                            _('Only a Time Off Manager can reset a started leave.'))
                    if holiday.employee_id != current_employee:
                        raise UserError(
                            _('Only a Time Off Manager can reset other people leaves.'))
                else:
                    if val_type == 'no_validation' and current_employee == holiday.employee_id:
                        continue
                    # use ir.rule based first access check: department, members, ... (see security.xml)
                    holiday.check_access_rule('write')

                    # This handles states validate1 validate and refuse
                    if holiday.employee_id == current_employee:
                        raise UserError(
                            _('Only a Time Off Manager can approve/refuse its own requests.'))

                    if (state == 'validate1' and val_type == 'both') or (
                            state == 'validate' and val_type == 'manager') and holiday.holiday_type == 'employee':
                        if (
                                not is_officer and self.env.user != holiday.employee_id.leave_manager_id):
                            print("fghmj",
                                  holiday.employee_id.parent_id.user_id,
                                  self.env.user)
                            if (
                            not self.env.user.id != holiday.employee_id.parent_id.user_id.id):
                                print("ssssssss")
                                pass
                            else:
                                raise UserError(
                                    _('You must be either %s\'s manager or Time off Manager to approve this leave') % (
                                        holiday.employee_id.name))

                    if (not is_officer or not self.employee_id.parent_id) and (
                            state == 'validate' and val_type == 'hr') and holiday.holiday_type == 'employee':
                        raise UserError(
                            _('You must either be a Time off Officer or Time off Manager to approve this leave'))

    def _check_double_validation_rules(self, employees, state):
        print("employees", employees)
        if self.user_has_groups('hr_holidays.group_hr_holidays_manager'):
            return

        is_leave_user = self.user_has_groups(
            'hr_holidays.group_hr_holidays_user')
        if state == 'validate1':
            employees = employees.filtered(
                lambda employee: employee.leave_manager_id != self.env.user)
            if (employees and not is_leave_user):
                if employees.parent_id.user_id.id == self.env.user.id:
                    pass
                else:
                    raise AccessError(
                        _('You cannot first approve a time off for %s, because you are not his time off manager',
                          employees[0].name))
        elif state == 'validate' and not is_leave_user:
            # Is probably handled via ir.rule
            raise AccessError(
                _('You don\'t have the rights to apply second approval on a time off request'))

    HolidaysRequest._check_approval_update = _check_approval_update
    HolidaysRequest._check_double_validation_rules = _check_double_validation_rules

    HolidaysRequest.write = write


class CalendarEvent(models.Model):
    _inherit = 'calendar.event'


class Attendee(models.Model):
    _inherit = 'calendar.attendee'


class HolidaysRequest(models.Model):
    _name = "hr.leave"
    _inherit = ['hr.leave', 'portal.mixin', 'mail.thread',
                'mail.activity.mixin']

    is_manager_approved = fields.Boolean(string="Is Manager Approved",
                                         help="To show that the manager is "
                                              "approved or not.")

    def get_portal_url(self, suffix=None, report_type=None, download=None,
                       query_string=None, anchor=None):
        """
            Get a portal url for this model, including access_token.
            The associated route must handle the flags for them to have any effect.
            - suffix: string to append to the url, before the query string
            - report_type: report_type query string, often one of: html, pdf, text
            - download: set the download query string to true
            - query_string: additional query string
            - anchor: string to append after the anchor #
        """
        self.ensure_one()
        url = '/my/leaves/' + str(self.id) + '%s?access_token=%s%s%s%s%s' % (
            suffix if suffix else '',
            self._portal_ensure_token(),
            '&report_type=%s' % report_type if report_type else '',
            '&download=true' if download else '',
            query_string if query_string else '',
            '#%s' % anchor if anchor else ''
        )
        return url

    @api.depends_context('uid')
    def _compute_description(self):
        self.check_access_rights('read')
        self.check_access_rule('read')

        is_officer = self.user_has_groups('hr_holidays.group_hr_holidays_user')

        for leave in self:
            if is_officer or leave.user_id == self.env.user or leave.employee_id.leave_manager_id == self.env.user or leave.employee_id.parent_id.user_id == self.env.user:
                leave.name = leave.sudo().private_name
            else:
                leave.name = '*****'


class HrAttendance(models.Model):
    _inherit = "hr.attendance"

    def create_attendance(self, value):
        # for rec in self[0]:
        user_id = self.env['res.users'].search(
            [('id', '=', value['write_uid'])])
        employee_id = self.env['hr.employee'].search(
            [('user_id', '=', user_id.id)])
        attendances = self.env['hr.attendance'].search(
            [('employee_id', '=', employee_id.id)])
        portal_check_in = value['check_in'].replace(',', '')
        print("===========portal_check_in=======", portal_check_in)
        # check_in_date = datetime.strptime(portal_check_in,'%d/%m/%Y %H:%M:%S')
        check_in_date = datetime.strptime(portal_check_in,
                                          '%d/%m/%Y %H:%M:%S %p')

        if attendances:
            for attendance in attendances:
                if attendance.check_in:
                    if check_in_date.date() != attendance.check_in.date() and attendance.check_out:
                        self.create({'employee_id': employee_id.id,
                                     'check_in': check_in_date})

                    elif not attendance.check_out:
                        message = (
                                "Can't  Checked In Because User Didn't checked "
                                "out since %r" % str(
                            attendance.check_in))
                        return message
                    else:
                        message = ("Can't  create duplicate attendance")
                        return message
        else:
            self.create(
                {'employee_id': employee_id.id, 'check_in': check_in_date})
            message = ("Checked In successfully")
            return message

    def write_attendance(self, value):
        # for rec in self[0]:
        user_id = self.env['res.users'].search(
            [('id', '=', value['write_uid'])])
        employee_id = self.env['hr.employee'].search(
            [('user_id', '=', user_id.id)])
        attendances = self.env['hr.attendance'].search(
            [('employee_id', '=', employee_id.id)])
        portal_check_out = value['check_out'].replace(',', '')
        check_out_date = datetime.strptime(portal_check_out,
                                           '%d/%m/%Y %H:%M:%S %p')
        if attendances:
            for attendance in attendances:
                if attendance.check_in:
                    if not attendance.check_out:
                        attendance.check_out = check_out_date
                    elif not attendance.check_in:
                        message = (
                            "Can't  Checked out Because There is  no  check_in"
                            " found for this user")
                        return message
                    elif attendance.check_out.date() == check_out_date.date():
                        message = ("Already Check Out at %r" % str(
                            attendance.check_out))
                        return message
