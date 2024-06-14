from odoo import _
from odoo.addons.hr_payroll.models.hr_payslip import HrPayslip
from odoo.exceptions import UserError


def action_payslip_cancel(self):
    if not self.env.user._is_system() or not self.env.user.has_group(
            'hr_payroll.group_hr_payroll_manager'):
        raise UserError(_("Cannot cancel a payslip that is done."))
    self.write({'state': 'cancel'})
    self.mapped('payslip_run_id').action_close()


HrPayslip.action_payslip_cancel = action_payslip_cancel
