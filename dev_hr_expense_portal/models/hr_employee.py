from odoo import models,fields

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    def _group_hr_expense_user_domain(self):
        # We return the domain only if the group exists for the following reason:
        # When a group is created (at module installation), the `res.users` form view is
        # automatically modifiedto add application accesses. When modifiying the view, it
        # reads the related field `expense_manager_id` of `res.users` and retrieve its domain.
        # This is a problem because the `group_hr_expense_user` record has already been created but
        # not its associated `ir.model.data` which makes `self.env.ref(...)` fail.
        # group = self.env.ref('hr_expense.group_hr_expense_team_approver', raise_if_not_found=False)
        return []

    expense_manager_id = fields.Many2one(
        'res.users', string='Expense',
        domain=_group_hr_expense_user_domain,
        compute='_compute_expense_manager', store=True, readonly=False,
        help='Select the user responsible for approving "Expenses" of this employee.\n'
             'If empty, the approval is done by an Administrator or Approver (determined in settings/users).')