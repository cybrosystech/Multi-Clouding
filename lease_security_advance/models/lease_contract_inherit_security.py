from datetime import timedelta

from odoo import models, fields, _, api
from odoo.exceptions import ValidationError


class LeaseeContractInheritAdvance(models.Model):
    _inherit = 'leasee.contract'

    security_amount = fields.Monetary(currency_field='leasee_currency_id')
    security_prepaid_account = fields.Many2one('account.account')
    security_advance_bool = fields.Boolean(default=False, copy=False)
    security_button_bool = fields.Boolean(default=False, copy=False)
    security_advance_id = fields.Many2one('leasee.security.advance', copy=False)

    def action_security_advance(self):
        for rec in self:
            if not rec.security_prepaid_account or rec.security_amount <= 0:
                raise ValidationError(
                    _('Please choose the security prepaid account and security amount'))
            advance_security_id = rec.env['leasee.security.advance'].create({
                'leasee_reference': rec.name,
                'leasee_contract_id': rec.id
            })
            rec.security_advance_id = advance_security_id.id
            instalment_date = []
            for instalment in rec.installment_ids:
                if instalment.date not in instalment_date:
                    if rec.leasor_type == 'single':
                        rec.create_security_moves(instalment,
                                                  advance_security_id,
                                                  rec.security_amount,
                                                  rec.vendor_id)
                        instalment_date.append(instalment.date)
                    else:
                        for leasor in rec.multi_leasor_ids:
                            partner = leasor.partner_id
                            leasor_amount = leasor.amount / sum(
                                rec.multi_leasor_ids.mapped(
                                    'amount')) * rec.security_amount if leasor.type == 'amount' else leasor.percentage / sum(
                                rec.multi_leasor_ids.mapped(
                                    'percentage')) * rec.security_amount
                            rec.create_security_moves(instalment,
                                                      advance_security_id,
                                                      leasor_amount,
                                                      partner)
                            instalment_date.append(instalment.date)
            rec.security_advance_bool = True
            rec.security_button_bool = False

    def create_security_moves(self, instalment, advance_security_id, amount,
                              partner):
        invoice_lines = [(0, 0, {
            'name': self.name + ' - ' + instalment.date.strftime(
                '%d/%m/%Y'),
            'account_id': self.security_prepaid_account.id,
            'price_unit': amount,
            'quantity': 1,
            'analytic_account_id': self.analytic_account_id.id,
            'project_site_id': self.project_site_id.id,
            'type_id': self.type_id.id,
            'location_id': self.location_id.id,
        })]
        self.env['account.move'].create({
            'partner_id': partner.id,
            'move_type': 'in_invoice',
            'currency_id': self.leasee_currency_id.id,
            'ref': self.name + '- SD - ' + instalment.date.strftime(
                '%d/%m/%Y'),
            'invoice_date': instalment.date,
            'invoice_line_ids': invoice_lines,
            'journal_id': self.installment_journal_id.id,
            'lease_security_advance_id': advance_security_id.id,
            'auto_post': True,
        })

    def action_security_bills(self):
        advance_security_id = self.env['leasee.security.advance'].search(
            [('leasee_contract_id', '=', self.id)])
        if advance_security_id:
            domain = [
                ('lease_security_advance_id', '=', advance_security_id.id),
                ('move_type', 'in', ['in_invoice'])]
            view_tree = {
                'name': _(' Vendor Bills '),
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'account.move',
                'type': 'ir.actions.act_window',
                'domain': domain,
            }

            return view_tree

    def action_activate(self):
        self.security_button_bool = True
        return super(LeaseeContractInheritAdvance, self).action_activate()

    def process_termination(self, disposal_date):
        if self.security_advance_id:
            security_moves = self.env['account.move'].search(
                [('lease_security_advance_id', '=', self.security_advance_id.id),
                 ('date', '>', disposal_date)])
            security_moves.button_draft()
            security_moves.button_cancel()
        return super(LeaseeContractInheritAdvance, self).process_termination(
            disposal_date)

    @api.model
    def security_advance_activation(self, limits):
        lease_contract = self.env['leasee.contract'].search(
            [('state', '=', 'active'), ('company_id', '=', self.env.company.id),
             ('security_advance_id', '=', False),
             ('security_prepaid_account', '!=', False),
             ('security_amount', '>', '0')],
            limit=limits)
        lease_contract.action_security_advance()
        lease_contracts = self.env['leasee.contract'].search(
            [('state', '=', 'active'), ('company_id', '=', self.env.company.id),
             ('security_advance_id', '=', False),
             ('security_amount', '>', '0'),
             ('security_prepaid_account', '!=', False)])
        schedule = self.env.ref(
            'lease_security_advance.action_advance_security_cron_update')
        if len(lease_contracts) > 0 and schedule.active:
            date = fields.Datetime.now()
            schedule.update({
                'nextcall': date + timedelta(seconds=20)
            })

    @api.model
    def security_advance_cron_update(self):
        date = fields.Datetime.now()
        schedule = self.env.ref(
            'lease_security_advance.action_advance_security_activation')
        schedule.update({
            'nextcall': date + timedelta(seconds=30)
        })
