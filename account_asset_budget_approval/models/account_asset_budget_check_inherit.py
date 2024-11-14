import re

from odoo import api, models, fields
from odoo.exceptions import UserError


class AccountAssetBudget(models.Model):
    _inherit = 'account.asset'

    state = fields.Selection(selection_add=[('to_approve', 'To Approve')])
    asset_approval_cycle_ids = fields.One2many('purchase.approval.cycle',
                                               'asset_id', copy=False)
    life_cycle_id = fields.Many2one('purchase.approval.cycle', copy=False)
    asset_approve_bool = fields.Boolean(
        compute='compute_approval_process')
    request_approval_bool = fields.Boolean(compute='_compute_request_approval')
    approved_life_bool = fields.Boolean(default=False, copy=False)
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
                         ('company_id', '=', self.env.company.id),
                         ('budget_line_ids', '!=', False)]):
                    rec.request_approval_bool = False
                else:
                    rec.request_approval_bool = True
            if self.asset_approval_cycle_ids.filtered(
                    lambda x: x.is_approved == True):
                self.request_approval_bool = False

    @api.depends('asset_approval_cycle_ids',
                 'asset_approval_cycle_ids.is_approved')
    def compute_approval_process(self):
        self.asset_approve_bool = False
        current_approve = self.asset_approval_cycle_ids.filtered(
            lambda x: x.is_approved).mapped('approval_seq')

        last_approval = max(current_approve) if current_approve else 0
        check_last_approval_is_approved = self.asset_approval_cycle_ids.filtered(
            lambda x: x.approval_seq == int(last_approval))
        for rec in self.asset_approval_cycle_ids:
            if check_last_approval_is_approved:
                if not rec.is_approved and self.env.user.id in rec.user_approve_ids.ids and check_last_approval_is_approved.is_approved:
                    self.asset_approve_bool = True
                    break
            else:
                if not rec.is_approved and self.env.user.id in rec.user_approve_ids.ids:
                    self.asset_approve_bool = True
                    break
                break


    def send_asset_user_notification(self, user_ids):
        for user in user_ids:
            email_template_id = self.env.ref(
                'account_asset_budget_approval.email_template_send_mail_approval_asset_acc')
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
        for asset in self:
            if not asset.asset_approval_cycle_ids:
                asset.request_approval_asset()
            if asset.asset_approval_cycle_ids:
                min_seq_approval = min(
                    asset.asset_approval_cycle_ids.filtered(
                        lambda x: x.is_approved is not True).mapped(
                        'approval_seq'))
                last_approval = asset.asset_approval_cycle_ids.filtered(
                    lambda x: x.approval_seq == int(min_seq_approval))
                if self.env.user not in last_approval.user_approve_ids:
                    raise UserError(
                        'You cannot approve this record' + ' ' + str(
                            asset.name))
                last_approval.is_approved = True
                remaining_approvals = asset.asset_approval_cycle_ids.filtered(
                        lambda x: x.is_approved is not True).mapped(
                        'approval_seq')
                if len(remaining_approvals) > 0:
                    min_seq_approval_next = min(remaining_approvals)
                    last_approval_to_approve = asset.asset_approval_cycle_ids.filtered(
                        lambda x: x.approval_seq == int(min_seq_approval_next))
                    asset.send_asset_user_notification(last_approval_to_approve.user_approve_ids)
                if not asset.asset_approval_cycle_ids.filtered(
                        lambda x: x.is_approved is False):
                    asset.validate()
                message = 'Level ' + str(
                    last_approval.approval_seq) + ' Approved by :' + str(
                    self.env.user.name)
                asset.message_post(body=message)

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
