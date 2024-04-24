from odoo import _
from odoo.addons.hr_payroll.models.hr_payslip import HrPayslip

from odoo.exceptions import UserError


class HrPayslipMonkeypatch(HrPayslip):
    def action_payslip_cancel(self):
        print("action_payslip_cancel,")
        # if self.filtered(lambda slip: slip.state == 'done'):
        #     raise UserError(_("Cannot cancel a payslip that is done."))
        self.write({'state': 'cancel'})
        self.mapped('payslip_run_id').action_close()

    HrPayslip.action_payslip_cancel = action_payslip_cancel