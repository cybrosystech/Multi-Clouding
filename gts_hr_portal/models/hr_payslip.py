# # -*- coding: utf-8 -*-

from odoo import models


class HrPayslip(models.Model):
    _inherit = "hr.payslip"

    def action_print_payslip(self):
        return {
            'name': 'Payslip',
            'type': 'ir.actions.act_url',
            'url': '/report/pdf/hr_payroll.report_payslip_lang/%(payslip_id)s' % {
                'payslip_id': self.id}
        }
