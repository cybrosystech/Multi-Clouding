from odoo import api, models, fields,_
from odoo.exceptions import UserError

PURCHASE_REQUISITION_STATES = [
    ('draft', 'Draft'),
    ('to_approve','To Approve'),
    ('ongoing', 'Ongoing'),
    ('in_progress', 'Confirmed'),
    ('open', 'Bid Selection'),
    ('done', 'Closed'),
    ('cancel', 'Cancelled')
]

class PurchaseRequisition(models.Model):
    _inherit='purchase.requisition'

    state = fields.Selection(selection=[('to_approve', 'To Approve')], tracking=True, required=True,
                              copy=False, default='draft',ondelete='set default')
    purchase_requisition_approval_cycle_ids = fields.One2many(
        comodel_name="purchase.approval.cycle", inverse_name="purchase_requisition_id",
        string="", required=False, )
    show_button_confirm = fields.Boolean(string="", copy=False, default=False)

    request_approve_bool = fields.Boolean(default=False, copy=False)
    show_request_approve_button = fields.Boolean(string="", copy=False)
    show_approve_button = fields.Boolean(string="",
                                         compute='check_show_approve_button')
    state = fields.Selection(PURCHASE_REQUISITION_STATES,
                              'Status', tracking=True, required=True,
                              copy=False, default='draft')
    state_blanket_order = fields.Selection(PURCHASE_REQUISITION_STATES, compute='_set_state')

    @api.depends('purchase_requisition_approval_cycle_ids','purchase_requisition_approval_cycle_ids.is_approved')
    def check_show_approve_button(self):
        self.show_approve_button = False
        current_approve = self.purchase_requisition_approval_cycle_ids.filtered(
            lambda x: x.is_approved).mapped('approval_seq')
        last_approval = max(current_approve) if current_approve else 0
        check_last_approval_is_approved = self.purchase_requisition_approval_cycle_ids.filtered(
            lambda x: x.approval_seq == int(last_approval))
        for rec in self.purchase_requisition_approval_cycle_ids:
            if check_last_approval_is_approved:
                if not rec.is_approved and self.env.user.id in rec.user_approve_ids.ids and check_last_approval_is_approved.is_approved:
                    self.show_approve_button = True
                    break
            else:
                if not rec.is_approved and self.env.user.id in rec.user_approve_ids.ids:
                    self.show_approve_button = True
                    break

                break


    def request_approval_button(self):
        if not self.purchase_requisition_approval_cycle_ids:
            purchase_requisition_approval_check_list = []
            purchase_requisition_approval_check = self.env[
                'purchase.requisition.approval.check'].search(
                [('company_id', '=', self.env.company.id)], limit=1)
            tot_amount = sum(self.line_ids.mapped('price_unit'))
            for rec in purchase_requisition_approval_check.purchase_requisition_approval_line_ids:
                if tot_amount >= rec.from_amount:
                    purchase_requisition_approval_check_list.append((0, 0, {
                        'approval_seq': rec.approval_seq,
                        'user_approve_ids': rec.user_ids.ids,
                    }))
            self.write(
                {'purchase_requisition_approval_cycle_ids': purchase_requisition_approval_check_list})
            self.request_approve_bool = True
        self.show_request_approve_button = True
        if self.purchase_requisition_approval_cycle_ids:
            min_seq_approval = min(
                self.purchase_requisition_approval_cycle_ids.mapped('approval_seq'))
            notification_to_user = self.purchase_requisition_approval_cycle_ids.filtered(
                lambda x: x.approval_seq == int(min_seq_approval))
            user = notification_to_user.user_approve_ids
            self.state = 'to_approve'
            self.send_user_notification(user)
            self.request_approve_bool = True
        else:
            self.show_button_confirm = True

    def button_approve_purchase_requisition_cycle(self):
        for rec in self:
            min_seq_approval = min(
                rec.purchase_requisition_approval_cycle_ids.filtered(
                    lambda x: x.is_approved is not True).mapped('approval_seq'))
            last_approval = rec.purchase_requisition_approval_cycle_ids.filtered(
                lambda x: x.approval_seq == int(min_seq_approval))
            if rec.env.user not in last_approval.user_approve_ids:
                raise UserError(
                    'You cannot approve this record' + ' ' + str(rec.name))
            last_approval.is_approved = True
            if not rec.purchase_requisition_approval_cycle_ids.filtered(
                    lambda x: x.is_approved is False):
                rec.action_in_progress()
            else:
                new_min_seq = min(rec.purchase_requisition_approval_cycle_ids.filtered(
                    lambda x: x.is_approved is False).mapped('approval_seq'))
                next_approvers = rec.purchase_requisition_approval_cycle_ids.filtered(
                    lambda x: x.approval_seq == int(new_min_seq)).mapped(
                    'user_approve_ids')
                rec.send_user_notification(next_approvers)

            message = 'Level ' + str(
                last_approval.approval_seq) + ' Approved by :' + str(
                rec.env.user.name)
            rec.message_post(body=message)

    def button_reject_purchase_requisition_cycle(self):
        self.state = 'draft'
        self.show_approve_button = False
        self.request_approve_bool = False
        self.show_request_approve_button = False
        self.purchase_requisition_approval_cycle_ids = False
        message = 'Rejected by :' + str(
            self.env.user.name)
        self.message_post(body=message)

    def send_user_notification(self, user):
        for us in user:
            reseiver = us.partner_id
            if reseiver:
                for purchase in self:
                    email_template_id = self.env.ref(
                        'tasc_blanket_order_approval.email_template_send_mail_approval_blanket_order')
                    ctx = self._context.copy()
                    tot_amount = sum(
                        purchase.line_ids.mapped('price_unit'))
                    ctx.update({'name': us.name,
                                'tot_amount': round(tot_amount,
                                                            2), })
                    if email_template_id:
                        email_template_id.with_context(ctx).send_mail(purchase.id,
                                                                      force_send=True,
                                                                      email_values={
                                                                          'email_to': us.email,
                                                                          'model': None,
                                                                          'res_id': None})



class BlanketOrderApprovalCycle(models.Model):
    _inherit = 'purchase.approval.cycle'

    purchase_requisition_id = fields.Many2one('purchase.requisition')