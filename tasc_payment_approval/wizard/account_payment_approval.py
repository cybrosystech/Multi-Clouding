from odoo import api, models, fields
from odoo.exceptions import UserError


class PaymentApproval(models.Model):
    _name = 'account.payment.approval'
    _rec_name = 'batch_name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    _description = 'Payment Approval'

    from_date = fields.Date(string="Date From", help="Date From")
    to_date = fields.Date(string="Date To", help="Date To")
    batch_name = fields.Char(string="Batch Name", help="Batch Name")
    payment_ids = fields.One2many('account.payment',
                                  'payment_approval_batch_id')
    state = fields.Selection([('not_approved', 'Not Approved'),
                              ('selected', 'Selected'),
                              ('in_approval', 'In Approval'),
                              ('approved', 'Approved')
                              ],
                             required=True, default='not_approved')
    payment_approval_cycle_ids = fields.One2many(
        comodel_name="purchase.approval.cycle", inverse_name="payment_id",
        string="", required=False, )
    request_approve_bool = fields.Boolean(default=False)
    show_request_approve_button = fields.Boolean(string="", copy=False)
    show_approve_button = fields.Boolean(string="",
                                         compute='check_show_approve_button')
    company_id = fields.Many2one('res.company', 'Company',
                                 default=lambda self: self.env.company)

    def button_approve_payment_cycle(self):
        for rec in self:
            min_seq_approval = min(
                rec.payment_approval_cycle_ids.filtered(
                    lambda x: x.is_approved is not True).mapped('approval_seq'))
            last_approval = rec.payment_approval_cycle_ids.filtered(
                lambda x: x.approval_seq == int(min_seq_approval))
            if rec.env.user not in last_approval.user_approve_ids:
                raise UserError(
                    'You cannot approve this record' + ' ' + str(rec.name))
            last_approval.is_approved = True
            rec.send_user_notification(last_approval.user_approve_ids)
            if not rec.payment_approval_cycle_ids.filtered(
                    lambda x: x.is_approved is False):
                rec.state = 'approved'
                for payment in rec.payment_ids:
                    payment.action_post()
            else:
                rec.state = 'in_approval'
            message = 'Level ' + str(
                last_approval.approval_seq) + ' Approved by :' + str(
                rec.env.user.name)
            rec.message_post(body=message)

    @api.depends()
    def check_show_approve_button(self):
        self.show_approve_button = False
        current_approve = self.payment_approval_cycle_ids.filtered(
            lambda x: x.is_approved).mapped('approval_seq')

        last_approval = max(current_approve) if current_approve else 0
        check_last_approval_is_approved = self.payment_approval_cycle_ids.filtered(
            lambda x: x.approval_seq == int(last_approval))
        for rec in self.payment_approval_cycle_ids:
            if check_last_approval_is_approved:
                if not rec.is_approved and self.env.user.id in rec.user_approve_ids.ids and check_last_approval_is_approved.is_approved:
                    self.show_approve_button = True
                    break
            else:
                if not rec.is_approved and self.env.user.id in rec.user_approve_ids.ids:
                    self.show_approve_button = True
                    break
                break

    def action_generate_approval_batch(self):
        print("action_generate_approval_batch")
        payments = self.env['account.payment'].search(
            [('payment_approval_batch_id', '=', False),
             ('date', '>=', self.from_date), ('date', '<=', self.to_date),
             ])
        print("payments", payments)
        self.payment_ids = payments.ids

    def request_approval_button(self):
        if not self.payment_approval_cycle_ids:
            payment_approval_check_list = []
            payment_approval_check = self.env['payment.approval.check'].search(
                [('company_id', '=', self.env.company.id)], limit=1)
            print("payment_approval_check", payment_approval_check)
            tot_amount = sum(self.payment_ids.mapped('amount'))
            print("tot_amount", tot_amount)
            for rec in payment_approval_check.payment_approval_line_ids:
                if tot_amount >= rec.from_amount:
                    payment_approval_check_list.append((0, 0, {
                        'approval_seq': rec.approval_seq,
                        'user_approve_ids': rec.user_ids.ids,
                    }))
            print("payment_approval_check_list", payment_approval_check_list)

            self.write(
                {'payment_approval_cycle_ids': payment_approval_check_list})
            self.request_approve_bool = True
        self.show_request_approve_button = True
        if self.payment_approval_cycle_ids:
            min_seq_approval = min(
                self.payment_approval_cycle_ids.mapped('approval_seq'))
            notification_to_user = self.payment_approval_cycle_ids.filtered(
                lambda x: x.approval_seq == int(min_seq_approval))
            user = notification_to_user.user_approve_ids
            self.state = 'selected'
            self.send_user_notification(user)
            self.request_approve_bool = True
            print("ddddddddddd")

    def send_user_notification(self, user):
        for us in user:
            reseiver = us.partner_id
            if reseiver:
                for move in self:
                    email_template_id = self.env.ref(
                        'analytic_account_types.email_template_send_mail_approval_account')
                    ctx = self._context.copy()
                    ctx.update({'name': us.name})
                    if email_template_id:
                        email_template_id.with_context(ctx).send_mail(self.id,
                                                                      force_send=True,
                                                                      email_values={
                                                                          'email_to': us.email,
                                                                          'model': None,
                                                                          'res_id': None})


class PaymentApprovalCycle(models.Model):
    _inherit = 'purchase.approval.cycle'

    payment_id = fields.Many2one('account.payment.approval')
