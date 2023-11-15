# # -*- coding: utf-8 -*-
#
# from odoo import api, fields, models, SUPERUSER_ID, tools
# from odoo.addons.base.models.res_partner import _tz_get
# from odoo.addons.resource.models.resource import float_to_time, HOURS_PER_DAY
# from odoo.exceptions import AccessError, UserError, ValidationError
# from odoo.tools import float_compare
# from odoo.tools.float_utils import float_round
# from odoo.tools.translate import _
# from odoo.osv import expression
#
#
#
# class HrPayslip(models.Model):
#     _inherit = "hr.payslip"
#
#
#     def get_portal_url(self, suffix=None, report_type=None, download=None, query_string=None, anchor=None):
#         """
#             Get a portal url for this model, including access_token.
#             The associated route must handle the flags for them to have any effect.
#             - suffix: string to append to the url, before the query string
#             - report_type: report_type query string, often one of: html, pdf, text
#             - download: set the download query string to true
#             - query_string: additional query string
#             - anchor: string to append after the anchor #
#         """
#         self.ensure_one()
#         url = '/my/payslip/' + str(self.id) + '%s?access_token=%s%s%s%s%s' % (
#             suffix if suffix else '',
#             self._portal_ensure_token(),
#             '&report_type=%s' % report_type if report_type else '',
#             '&download=true' if download else '',
#             query_string if query_string else '',
#             '#%s' % anchor if anchor else ''
#         )
#         return url
#
#    #  def _get_report_url(self):
#    #      print(">>>>>>>>>>>>>>>>>>>>>>get_report",self)
#    #      return '/report/pdf/%s/%d' % ('hr_payroll.report_payslip', self.id)
#
#    #