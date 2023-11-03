from num2words import num2words
from odoo import models


class HrPaySlip(models.Model):
    _name = "hr.payslip"
    _inherit = ['hr.payslip', 'portal.mixin']

    def qty_to_text(self, total):
        qty_txt = num2words(total)
        return qty_txt

    def _get_portal_return_action(self):
        """ Return the action used to display payslip when returning from
        customer portal. """
        self.ensure_one()
        return self.env.ref('hr_payroll.action_view_hr_payslip_month_form')

    def _get_report_base_filename(self):
        self.ensure_one()
        return '%s' % (self.name)
