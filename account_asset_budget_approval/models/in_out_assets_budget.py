from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class InOutAssetBudgets(models.Model):
    _name = 'budget.asset.check.in.out'

    name = fields.Char(string="Name", required=False, )
    active = fields.Boolean(default=False)
    company_id = fields.Many2one('res.company', 'Company',
                                 default=lambda self: self.env.company)
    budget_line_ids = fields.One2many("budget.asset.lines.in.out", "budget_id",
                                      string="",
                                      required=False)

    @api.constrains('budget_line_ids')
    def check_lines(self):
        for rec in self:
            count_map = {}
            for line in rec.budget_line_ids:
                count = count_map.get(line.approval_seq, 0)
                if count != 0:
                    raise ValidationError(
                        _('Cannot add the same sequence more than once, '
                          'asequence of  %s is repeated') % line.name)
                count_map[line.approval_seq] = 1

    @api.onchange('active', 'company_id')
    def onchange_active_bool(self):
        active_ids = self.env['budget.asset.check.in.out'].search([('active',
                                                                    '=', True),
                                                                   ('company_id', '=', self.company_id.id)])
        if self.active:
            for rec in active_ids:
                rec.active = False


class BudgetAssetInOutLines(models.Model):
    _name = 'budget.asset.lines.in.out'

    budget_id = fields.Many2one('budget.asset.check.in.out', string="",
                                required=False, )
    name = fields.Char(string="Name", required=True, )
    from_amount = fields.Float(string="From", required=False, )
    to_amount = fields.Float(string="To", required=False, )
    approval_seq = fields.Integer(string="Approval Sequence", required=False, )
    user_ids = fields.Many2many("res.users", string="User",
                                required=True, )

    @api.onchange('approval_seq')
    def approval_seq_check(self):
        for rec in self:
            if rec.name and rec.approval_seq <= 0:
                rec.approval_seq = False
                raise ValidationError(
                    _('Approval Sequence cannot be lower than 1'))

    @api.constrains('from_amount', 'to_amount')
    def get_from_to_amount(self):
        for rec in self:
            if rec.from_amount < 0:
                raise ValidationError(_('From amount is lower than 0'))


class AssetApprovalCycle(models.Model):
    _inherit = 'purchase.approval.cycle'

    asset_id = fields.Many2one('account.asset')

