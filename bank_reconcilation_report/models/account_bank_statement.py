from odoo import api, fields, models
from odoo.exceptions import UserError


class AccountBankStatement(models.Model):
    _name = 'account.bank.statement'
    _inherit = ['account.bank.statement', 'mail.thread', 'mail.activity.mixin']

    request_approve_bool = fields.Boolean(default=False, copy=False)
    show_request_approve_button = fields.Boolean(string="", copy=False)
    show_approve_button = fields.Boolean(string="",
                                         compute='check_show_approve_button')
    approval_cycle_ids = fields.One2many(
        comodel_name="purchase.approval.cycle", inverse_name="statement_id",
        string="", required=False, )
    state = fields.Selection([('draft', 'Draft'),
                              ('in_approval', 'In Approval'),
                              ('approved', 'Approved')
                              ],
                             required=True, default='draft', tracking=True)
    total_lines = fields.Integer(string="Total Lines",
                                 compute='_compute_total_lines',
                                 help="Total number of statement lines")
    total_lines_reconciled = fields.Integer(string="Lines Reconciled",
                                            compute='_compute_total_lines',
                                            help="Total number of statement lines reconciled",
                                            store=True)

    @api.depends('line_ids.is_reconciled')
    def _compute_total_lines(self):
        for rec in self:
            if rec.line_ids:
                rec.total_lines = len(rec.line_ids.ids)
                rec.total_lines_reconciled = len(rec.line_ids.filtered(lambda x:x.is_reconciled).ids)
            else:
                rec.total_lines = 0
                rec.total_lines_reconciled = 0

    def action_bank_statement_change_state(self):
        statements = self.env['account.bank.statement'].search([('state','!=','approved')])
        if statements:
            statements.write({'state': 'approved'})
            for stmt in statements:
                stmt.total_lines = len(stmt.line_ids.ids)
                stmt.total_lines_reconciled = len(stmt.line_ids.filtered(lambda x: x.is_reconciled).ids)

    def send_user_notification(self, user):
        for us in user:
            reseiver = us.partner_id
            if reseiver:
                for pay in self:
                    email_template_id = self.env.ref(
                        'bank_reconcilation_report.email_template_send_mail_approval_bank_statement')
                    ctx = self._context.copy()

                    ctx.update({'name': us.name, })
                    if email_template_id:
                        email_template_id.with_context(ctx).send_mail(pay.id,
                                                                      force_send=True,
                                                                      email_values={
                                                                          'email_to': us.email,
                                                                          'model': None,
                                                                          'res_id': None})

    @api.depends()
    def check_show_approve_button(self):
        self.show_approve_button = False
        current_approve = self.approval_cycle_ids.filtered(
            lambda x: x.is_approved).mapped('approval_seq')
        last_approval = max(current_approve) if current_approve else 0
        check_last_approval_is_approved = self.approval_cycle_ids.filtered(
            lambda x: x.approval_seq == int(last_approval))
        for rec in self.approval_cycle_ids:
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
        for record in self:
            if (
                    record.state not in ['approved', 'selected', 'in_approval']
                    and(not record.request_approve_bool or not record.request_approval_button())
                    and (record.total_lines != 0 and record.total_lines == record.total_lines_reconciled)
            ):
                if not record.approval_cycle_ids:
                    payment_approval_check_list = []
                    payment_approval_check = self.env[
                        'account.statement.approval.check'].search(
                        [('company_id', '=', self.env.company.id)], limit=1)
                    for rec in payment_approval_check.statement_approval_line_ids:
                        payment_approval_check_list.append((0, 0, {
                            'approval_seq': rec.approval_seq,
                            'user_approve_ids': rec.user_ids.ids,
                        }))
                    record.write(
                        {'approval_cycle_ids': payment_approval_check_list})
                    record.request_approve_bool = True
                record.show_request_approve_button = True
                if record.approval_cycle_ids:
                    min_seq_approval = min(
                        record.approval_cycle_ids.mapped('approval_seq'))
                    notification_to_user = self.approval_cycle_ids.filtered(
                        lambda x: x.approval_seq == int(min_seq_approval))
                    user = notification_to_user.user_approve_ids
                    record.state = 'in_approval'
                    record.send_user_notification(user)
                    record.request_approve_bool = True

    def button_reject_payment_cycle(self):
        self.state = 'draft'
        self.show_approve_button = False
        self.request_approve_bool = False
        self.show_request_approve_button = False
        self.approval_cycle_ids = False
        message = 'Rejected by :' + str(
            self.env.user.name)
        self.message_post(body=message)

    def button_approve_payment_cycle(self):
        for rec in self:
            min_seq_approval = min(
                rec.approval_cycle_ids.filtered(
                    lambda x: x.is_approved is not True).mapped('approval_seq'))
            last_approval = rec.approval_cycle_ids.filtered(
                lambda x: x.approval_seq == int(min_seq_approval))
            if rec.env.user not in last_approval.user_approve_ids:
                raise UserError(
                    'You cannot approve this record' + ' ' + str(rec.name))
            last_approval.is_approved = True
            if not rec.approval_cycle_ids.filtered(
                    lambda x: x.is_approved is False):
                rec.state = 'approved'
            else:
                new_min_seq = min(rec.approval_cycle_ids.filtered(
                    lambda x: x.is_approved is False).mapped('approval_seq'))
                next_approvers = rec.approval_cycle_ids.filtered(
                    lambda x: x.approval_seq == int(new_min_seq)).mapped(
                    'user_approve_ids')
                rec.send_user_notification(next_approvers)
                rec.state = 'in_approval'
            message = 'Level ' + str(
                last_approval.approval_seq) + ' Approved by :' + str(
                rec.env.user.name)
            rec.message_post(body=message)


class PaymentApprovalCycle(models.Model):
    _inherit = 'purchase.approval.cycle'

    statement_id = fields.Many2one('account.bank.statement')
