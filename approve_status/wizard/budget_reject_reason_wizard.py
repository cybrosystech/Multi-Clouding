from odoo import fields, models


class BudgetRejectionWizard(models.TransientModel):
    _name = 'budget.rejection.wizard'

    reason = fields.Text(string='Reason')

    def action_rejection_send(self):
        if self.env.context['active_model'] == 'account.move':
            account_ids = self.env['account.move'].browse(
                self.env.context['active_id'])
            message = account_ids.journal_id.name + 'has been rejected <br/>' \
                                                    'Due to ' + self.reason
            template_id = self.env.ref(
                'approve_status.email_template_budget_check_rejection')
            reason = self.reason if self.reason else ''
            if template_id:
                template_id.with_context(reason=reason).send_mail(
                    res_id=self.env.context['active_id'], force_send=True)
            account_ids.sudo().message_post(body=message)
            account_ids.button_draft()
        elif self.env.context['active_model'] == 'purchase.order':
            purchase_id = self.env['purchase.order'].browse(
                self.env.context['active_id'])
            message = purchase_id.name + 'has been rejected <br/>' \
                                         'Due to ' + self.reason
            template_id = self.env.ref(
                'approve_status.email_template_budget_check_rejection_purchase')
            reason = self.reason if self.reason else ''
            if template_id:
                template_id.with_context(reason=reason).send_mail(
                    res_id=self.env.context['active_id'], force_send=True)
            purchase_id.sudo().message_post(body=message)
            purchase_id.show_approve_button = False
            purchase_id.button_draft()
        elif self.env.context['active_model'] == 'sale.order':
            sales_id = self.env['sale.order'].browse(
                self.env.context['active_id'])
            message = sales_id.name + 'has been rejected <br/>' \
                                      'Due to ' + self.reason
            template_id = self.env.ref(
                'approve_status.email_template_budget_check_rejection_sales')
            reason = self.reason if self.reason else ''
            if template_id:
                template_id.with_context(reason=reason).send_mail(
                    res_id=self.env.context['active_id'], force_send=True)
            sales_id.sudo().message_post(body=message)
            sales_id.action_cancel()
            sales_id.action_draft()
        else:
            asset_id = self.env['account.asset'].browse(
                self.env.context['active_id'])
            message = asset_id.name + 'has been rejected <br/>' \
                                      'Due to ' + self.reason
            template_id = self.env.ref(
                'approve_status.email_template_budget_check_rejection_asset')
            reason = self.reason if self.reason else ''
            if template_id:
                template_id.with_context(reason=reason).send_mail(
                    res_id=self.env.context['active_id'], force_send=True)
                asset_id.sudo().message_post(body=message)
                asset_id.set_to_draft()
