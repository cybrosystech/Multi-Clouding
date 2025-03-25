from datetime import timedelta
from odoo import fields,models


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def button_confirm(self):
        res = super().button_confirm()
        for rec in self:
            email_template_id = self.env.ref(
                'approval_followup.email_template_send_mail_reminder_purchase_receive')
            ctx = self._context.copy()
            ctx.update({'name': rec.user_id.partner_id.name})
            if email_template_id:
                email_from_alias = self.env[
                    'ir.config_parameter'].sudo().get_param(
                    'mail.default.from')
                # Construct the email if alias and domain exist
                if email_from_alias:
                    email_from = f"Odoo ERP <{email_from_alias}>"
                else:
                    # Fallback to the company email if catchall is not set
                    email_from = f"Odoo ERP <{self.env.user.company_id.email}>"
                email_template_id.with_context(ctx).send_mail(rec.id,
                                                              force_send=True,
                                                              email_values={
                                                                  'email_to': rec.user_id.partner_id.email,
                                                                  'email_from': email_from,
                                                                  'model': None,
                                                                  'res_id': None})
        return res

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

    def action_send_purchase_receive_reminder(self):
        date_threshold = fields.Datetime.now() - timedelta(days=2)
        purchase_orders = self.env['purchase.order'].search([
            ('state', 'in', ['purchase','done']),('receipt_status','in',['partial','pending']),
            ('date_approve', '<=', date_threshold.date()),
        ])
        for po in purchase_orders:
            email_template_id = self.env.ref(
                'approval_followup.email_template_send_mail_reminder_purchase_receive')
            ctx = self._context.copy()
            ctx.update({'name': po.user_id.partner_id.name })
            if email_template_id:
                email_from_alias = self.env[
                    'ir.config_parameter'].sudo().get_param(
                    'mail.default.from')
                # Construct the email if alias and domain exist
                if email_from_alias:
                    email_from = f"Odoo ERP <{email_from_alias}>"
                else:
                    # Fallback to the company email if catchall is not set
                    email_from = f"Odoo ERP <{self.env.user.company_id.email}>"
                email_template_id.with_context(ctx).send_mail(po.id,
                                                              force_send=True,
                                                              email_values={
                                                                  'email_to': po.user_id.partner_id.email,
                                                                  'email_from': email_from,
                                                                  'model': None,
                                                                  'res_id': None})
