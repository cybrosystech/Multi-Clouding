from odoo import api, models, fields, _
from odoo.exceptions import ValidationError


class AccountStatementApprovalCheck(models.Model):
    _name = 'account.statement.approval.check'
    _description = 'Account Statement Approval Check'
    _rec_name = 'name'

    name = fields.Char(string="Name", required=False, )
    statement_approval_line_ids = fields.One2many(
        comodel_name="account.statement.approval.check.line",
        inverse_name="statement_approval_check_id",
        string="",
        required=False, )
    company_id = fields.Many2one('res.company', 'Company',
                                 default=lambda self: self.env.company)

    @api.constrains('statement_approval_line_ids')
    def check_lines(self):
        for rec in self:
            count_map = {}
            for line in rec.statement_approval_line_ids:
                count = count_map.get(line.approval_seq, 0)
                if count != 0:
                    raise ValidationError(
                        _('Cannot add the same sequence more than once, a sequence of  %s is repeated') % line.name)
                count_map[line.approval_seq] = 1


class AccountStatementApprovalCheckLine(models.Model):
    _name = 'account.statement.approval.check.line'
    _description = 'Account Statement Approval Check Line'
    _rec_name = 'name'

    statement_approval_check_id = fields.Many2one(
        comodel_name="account.statement.approval.check",
        string="", required=False, )
    name = fields.Char(string="Name", required=True, )
    approval_seq = fields.Integer(string="Approval Sequence", required=False, )
    user_ids = fields.Many2many(comodel_name="res.users", string="User",
                                required=True, )

    company_id = fields.Many2one('res.company', 'Company',
                                 related='statement_approval_check_id.company_id',
                                 store=True)

    @api.onchange('approval_seq')
    def approval_seq_check(self):
        for rec in self:
            if rec.name and rec.approval_seq <= 0:
                rec.approval_seq = False
                raise ValidationError(
                    _('Approval Sequence cannot be lower than 1'))
