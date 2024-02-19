from odoo import api, models, fields, _
from odoo.exceptions import ValidationError


class PaymentApprovalCheck(models.Model):
    _name = 'payment.approval.check'
    _description = 'Payment Approval Check'
    _rec_name = 'name'

    name = fields.Char(string="Name", required=False, )
    payment_approval_line_ids = fields.One2many(
        comodel_name="payment.approval.check.line",
        inverse_name="payment_approval_check_id",
        string="",
        required=False, )
    company_id = fields.Many2one('res.company', 'Company',
                                 default=lambda self: self.env.company)

    @api.constrains('payment_approval_line_ids')
    def check_lines(self):
        for rec in self:
            count_map = {}
            latest_to = 0
            for line in rec.payment_approval_line_ids:
                count = count_map.get(line.approval_seq, 0)
                if count != 0:
                    raise ValidationError(
                        _('Cannot add the same sequence more than once, a sequence of  %s is repeated') % line.name)
                count_map[line.approval_seq] = 1
                latest_to = line.to_amount

    # @api.model
    # def create(self, vals):
    #     if vals.get('type'):
    #         check = self.env['payment.approval.check'].sudo().search(
    #             [
    #                 ('company_id', '=', vals['company_id'])])
    #         if check:
    #             raise ValidationError(_('This Type is already created'))
    #     return super(PaymentApprovalCheck, self).create(vals)


class PaymentApprovalCheckLine(models.Model):
    _name = 'payment.approval.check.line'
    _description = 'Payment Approval Check Line'
    _rec_name = 'name'

    payment_approval_check_id = fields.Many2one(
        comodel_name="payment.approval.check",
        string="", required=False, )
    name = fields.Char(string="Name", required=True, )
    from_amount = fields.Float(string="From", required=False, )
    to_amount = fields.Float(string="To", required=False, )
    approval_seq = fields.Integer(string="Approval Sequence", required=False, )
    user_ids = fields.Many2many(comodel_name="res.users", string="User",
                                required=True, )

    company_id = fields.Many2one('res.company', 'Company',
                                 related='payment_approval_check_id.company_id',
                                 store=True)

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
