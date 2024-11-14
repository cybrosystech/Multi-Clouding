from datetime import timedelta
from odoo import fields,models


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def action_send_approval_reminder(self):
        date_threshold = fields.Datetime.now() - timedelta(days=2)
        purchase_orders = self.env['purchase.order'].search([
            ('state', '=', 'to_approve'),  # Assuming "approval" is the state name
            ('write_date', '<=', date_threshold.date()),
        ])
        for po in purchase_orders:
            if po.purchase_approval_cycle_ids:
                min_seq_approval = min(
                    po.purchase_approval_cycle_ids.filtered(
                        lambda x: x.is_approved is not True).mapped(
                        'approval_seq'))
                last_approval = po.purchase_approval_cycle_ids.filtered(
                    lambda x: x.approval_seq == int(min_seq_approval))
                po.send_user_notification(last_approval.user_approve_ids)
