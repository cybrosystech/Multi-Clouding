# -*- coding: utf-8 -*-
import logging
from datetime import datetime

from pytz import timezone, UTC
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


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

    def activity_update(self):
        to_clean, to_do = self.env['hr.leave'], self.env['hr.leave']
        for holiday in self:
            start = UTC.localize(holiday.date_from).astimezone(
                timezone(holiday.employee_id.tz or 'UTC'))
            end = UTC.localize(holiday.date_to).astimezone(
                timezone(holiday.employee_id.tz or 'UTC'))
            note = _(
                'New %(leave_type)s Request created by %(user)s from %(start)s to %(end)s',
                leave_type=holiday.holiday_status_id.name,
                user=holiday.create_uid.name,
                start=start,
                end=end
            )
            if holiday.state == 'draft':
                to_clean |= holiday
            elif holiday.state == 'confirm':
                holiday.activity_schedule(
                    'hr_holidays.mail_act_leave_approval',
                    note=note,
                    user_id=holiday.sudo()._get_responsible_for_approval().id or self.env.user.id)
                holiday.activity_schedule(
                    'hr_holidays.mail_act_leave_approval',
                    note=note,
                    user_id=holiday.sudo().employee_id.parent_id.user_id.id or self.env.user.id)
            elif holiday.state == 'validate1':
                holiday.activity_feedback(
                    ['hr_holidays.mail_act_leave_approval'])
                holiday.activity_schedule(
                    'hr_holidays.mail_act_leave_second_approval',
                    note=note,
                    user_id=holiday.sudo()._get_responsible_for_approval().id or self.env.user.id)
                holiday.activity_schedule(
                    'hr_holidays.mail_act_leave_second_approval',
                    note=note,
                    user_id=holiday.sudo().employee_id.parent_id.user_id.id or self.env.user.id)
            elif holiday.state == 'validate':
                to_do |= holiday
            elif holiday.state == 'refuse':
                to_clean |= holiday
        if to_clean:
            to_clean.activity_unlink(['hr_holidays.mail_act_leave_approval',
                                      'hr_holidays.mail_act_leave_second_approval'])
        if to_do:
            to_do.activity_feedback(['hr_holidays.mail_act_leave_approval',
                                     'hr_holidays.mail_act_leave_second_approval'])
