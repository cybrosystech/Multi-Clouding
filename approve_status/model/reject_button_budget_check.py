from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def button_reject_purchase_cycle(self):
        print("button_reject_purchase_cycle")
        view_id = self.env.ref('approve_status.view_budget_rejection_form').id
        return {
            'name': 'Rejection Send',
            'type': 'ir.actions.act_window',
            'res_model': 'budget.rejection.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'view_id': view_id,
        }
