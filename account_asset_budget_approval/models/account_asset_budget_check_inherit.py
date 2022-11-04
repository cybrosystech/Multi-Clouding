from odoo import models, fields


class AccountAssetBudget(models.Model):
    _inherit = 'account.asset'

    state = fields.Selection(selection_add=[('to_approve', 'To Approve')])
    asset_approval_cycle_ids = fields.One2many('purchase.approval.cycle',
                                               'asset_id')
    life_cycle_id = fields.Many2one('purchase.approval.cycle')
    asset_approve_bool = fields.Boolean(
        compute='compute_approval_process')
    request_approval_bool = fields.Boolean(compute='_compute_request_approval')
    approved_life_bool = fields.Boolean(default=False)
    button_validate_bool = fields.Boolean(default=False)

    def _compute_request_approval(self):
        for rec in self:
            name = rec.name.lower()
            if name.find('lease') != -1:
                rec.request_approval_bool = True
                rec.button_validate_bool = True
                if self.state in ['open', 'model']:
                    rec.button_validate_bool = False
            else:
                if self.env['budget.asset.check.in.out'].search(
                        [('active', '=', True),
                         ('company_id', '=', self.env.company.id)]):
                    rec.request_approval_bool = False
                else:
                    rec.request_approval_bool = True
            if self.asset_approval_cycle_ids.filtered(
                    lambda x: x.is_approved == True):
                self.request_approval_bool = True

    def compute_approval_process(self):
        approval_lines = self.asset_approval_cycle_ids
        for rec in range(0, len(approval_lines)):
            if approval_lines[rec].is_approved:
                continue
            else:
                self.life_cycle_id = approval_lines[rec]
                break
        if self.life_cycle_id.user_approve_ids.filtered(
                lambda x: x.id == self.env.user.id):
            self.asset_approve_bool = True
        else:
            self.asset_approve_bool = False

    def send_asset_user_notification(self, user_ids):
        for user in user_ids:
            email_template_id = self.env.ref('account_asset_budget_approval.email_template_send_mail_approval_asset_acc')
            if email_template_id:
                email_template_id.sudo().write({'email_to': user.email})
                email_template_id.with_context(name=user.name).sudo().send_mail(
                    res_id=self.id,
                    force_send=True)

    def request_approval_asset(self):
        approval_ids = self.env['budget.asset.check.in.out'].search(
            [('active', '=', True),
             ('company_id', '=', self.env.company.id)])
        sorted_approval = (
            approval_ids.mapped(lambda x: x.budget_line_ids)).sorted(
            lambda x: x.approval_seq)
        approval = []
        approval_cycle_ids = []
        for rec in sorted_approval:
            if rec.from_amount <= self.original_value:
                purchase = self.env['purchase.approval.cycle'].create({
                    'approval_seq': rec.approval_seq,
                    'user_approve_ids': [(6, 0, rec.user_ids.ids)],
                    'is_approved': False,
                })
                approval_cycle_ids.append(purchase.id)
                approval.append(rec.id)
        self.asset_approval_cycle_ids = [(6, 0, approval_cycle_ids)]

        if approval:
            self.state = 'to_approve'
            self.send_asset_user_notification(sorted_approval[0].user_ids)

    def asset_approve(self):
        self.life_cycle_id.is_approved = True
        if self.asset_approval_cycle_ids.filtered(
                lambda x: x.is_approved == False):
            self.approved_life_bool = False
        else:
            self.approved_life_bool = True
            self.validate()

    def reject_asset(self):
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

    def set_to_draft(self):
        self.asset_approval_cycle_ids.mapped(lambda x: x.unlink())

        return super(AccountAssetBudget, self).set_to_draft()
