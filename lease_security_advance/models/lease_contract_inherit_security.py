import math
from datetime import timedelta
from odoo import models, fields, _, api
from odoo.exceptions import ValidationError
from odoo.tools.safe_eval import dateutil
import dateutil.relativedelta as relativedelta


class LeaseeContractInheritAdvance(models.Model):
    _inherit = 'leasee.contract'

    security_amount = fields.Monetary(currency_field='leasee_currency_id')
    security_prepaid_account = fields.Many2one('account.account',
                                               string="Security Expenses")
    security_advance_bool = fields.Boolean(default=False, copy=False)
    security_button_bool = fields.Boolean(default=False, copy=False)
    security_advance_id = fields.Many2one('leasee.security.advance', copy=False)
    security_deferred_account = fields.Many2one('account.account',
                                                string="Security Deferred"
                                                       " Account")
    sd_date_same_as_lease = fields.Selection(string="SD Date same as Lease",
                                             selection=[('yes', 'Yes'),
                                                        ('no', 'No')],
                                             copy=False,
                                             default='yes')

    sd_lessor_name_same_as_lease = fields.Selection(
        string="SD Lessor name same as Lease",
        selection=[('yes', 'Yes'), ('no', 'No')], copy=False, default='yes')
    sd_date = fields.Date(string='SD Date',
                          help="SD date for security advance bills.",
                          copy=False)
    sd_leasor = fields.Many2one('res.partner', string="SD Leasor",
                                help="Leasor for security advance "
                                     "bills.")
    new_sd_leasor_ids = fields.One2many(comodel_name="sd.leasor",
                                        inverse_name="leasee_contract_id",
                                        string="", required=False, copy=False,
                                        tracking=True)
    is_new_sd_leasor_visible = fields.Boolean(string="Is new sd leasor visible",
                                              compute='compute_is_new_sd_leasor_visible',
                                              store=True)
    is_new_sd_leasor_ids_visible = fields.Boolean(
        string="Is new sd leasors visible",
        compute='compute_is_new_sd_leasor_visible', store=True)

    @api.depends('leasor_type', 'sd_lessor_name_same_as_lease')
    def compute_is_new_sd_leasor_visible(self):
        for rec in self:
            if rec.sd_lessor_name_same_as_lease == 'no' and rec.leasor_type == 'single':
                rec.is_new_sd_leasor_visible = True
                rec.is_new_sd_leasor_ids_visible = False
            elif rec.sd_lessor_name_same_as_lease == 'no' and rec.leasor_type == 'multi':
                rec.is_new_sd_leasor_visible = False
                rec.is_new_sd_leasor_ids_visible = True
            else:
                rec.is_new_sd_leasor_visible = False
                rec.is_new_sd_leasor_ids_visible = False

    @api.constrains('new_sd_leasor_ids')
    def onsave_new_sd_leasor_ids(self):
        if self.new_sd_leasor_ids:
            percentage = 0
            for leasor in self.new_sd_leasor_ids:
                if leasor.type == 'percentage':
                    percentage += leasor.percentage
                else:
                    percentage += (
                            leasor.amount / self.security_amount * 100)
            if round(percentage, 3) != 100.0:
                raise ValidationError(_('New Leasors Total must be 100%'))

    @api.onchange('leasor_type')
    def onchange_leasor_type(self):
        if self.leasor_type == 'single':
            if self.new_sd_leasor_ids:
                self.new_sd_leasor_ids = [(5, 0, 0)]
        else:
            self.sd_leasor = False

    @api.onchange('leasee_template_id')
    def onchange_leasee_template_id(self):
        self.update({
            'lease_contract_period': self.leasee_template_id.lease_contract_period,
            'lease_contract_period_type': self.leasee_template_id.lease_contract_period_type,
            'terminate_month_number': self.leasee_template_id.terminate_month_number,
            'terminate_fine': self.leasee_template_id.terminate_fine,
            'type_terminate': self.leasee_template_id.type_terminate,
            'extendable': self.leasee_template_id.extendable,
            'interest_rate': self.leasee_template_id.interest_rate,
            'payment_frequency_type': self.leasee_template_id.payment_frequency_type,
            'payment_frequency': self.leasee_template_id.payment_frequency,
            'increasement_rate': self.leasee_template_id.increasement_rate,
            'increasement_frequency_type': self.leasee_template_id.increasement_frequency_type,
            'increasement_frequency': self.leasee_template_id.increasement_frequency,
            'prorata_computation_type': self.leasee_template_id.prorata_computation_type,
            'asset_model_id': self.leasee_template_id.asset_model_id.id,
            'lease_liability_account_id': self.leasee_template_id.lease_liability_account_id.id,
            'long_lease_liability_account_id': self.leasee_template_id.long_lease_liability_account_id.id,
            'provision_dismantling_account_id': self.leasee_template_id.provision_dismantling_account_id.id,
            'terminate_account_id': self.leasee_template_id.terminate_account_id.id,
            'interest_expense_account_id': self.leasee_template_id.interest_expense_account_id.id,
            'terminate_product_id': self.leasee_template_id.terminate_product_id.id,
            'installment_product_id': self.leasee_template_id.installment_product_id.id,
            'extension_product_id': self.leasee_template_id.extension_product_id.id,
            'installment_journal_id': self.leasee_template_id.installment_journal_id.id,
            'initial_journal_id': self.leasee_template_id.initial_journal_id.id,
            'analytic_account_id': self.leasee_template_id.analytic_account_id.id,
            'project_site_id': self.leasee_template_id.project_site_id.id,

            'analytic_distribution': self.analytic_distribution,
            'incentives_account_id': self.leasee_template_id.incentives_account_id.id,
            'incentives_product_id': self.leasee_template_id.incentives_product_id.id,
            'initial_product_id': self.leasee_template_id.initial_product_id.id,
            'security_prepaid_account': self.leasee_template_id.security_prepaid_account,
            'security_deferred_account': self.leasee_template_id.security_deferred_account,
        })

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
            if rec.sd_date:
                invoice_date = rec.sd_date
            else:
                invoice_date = False

            for instalment in rec.installment_ids:
                if instalment.date not in instalment_date:
                    if rec.leasor_type == 'single':
                        if rec.sd_lessor_name_same_as_lease == 'no':
                            rec.create_security_moves(instalment,
                                                      advance_security_id,
                                                      rec.security_amount,
                                                      rec.sd_leasor,
                                                      invoice_date)
                        else:
                            rec.create_security_moves(instalment,
                                                      advance_security_id,
                                                      rec.security_amount,
                                                      rec.vendor_id,
                                                      invoice_date)
                        instalment_date.append(instalment.date)
                    else:
                        if rec.sd_lessor_name_same_as_lease == 'no':
                            for leasor in rec.new_sd_leasor_ids:
                                partner = leasor.partner_id
                                leasor_amount = leasor.amount if leasor.type == 'amount' else (leasor.percentage/100 )* rec.security_amount
                                rec.create_security_moves(instalment,
                                                          advance_security_id,
                                                          leasor_amount,
                                                          partner, invoice_date)
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
                                                          partner, invoice_date)
                                instalment_date.append(instalment.date)
                    if rec.sd_date and rec.sd_date_same_as_lease == 'no':
                        if rec.lease_contract_period_type == 'years':
                            if rec.payment_frequency_type == 'years':
                                invoice_date = invoice_date + relativedelta.relativedelta(
                                    years=1)
                            else:
                                invoice_date = invoice_date + relativedelta.relativedelta(
                                    months=1)
                        else:
                            invoice_date = invoice_date + relativedelta.relativedelta(
                                months=1)
            rec.security_advance_bool = True
            rec.security_button_bool = False

    def create_security_moves(self, instalment, advance_security_id, amount,
                              partner, invoice_date):
        if instalment.leasee_contract_id.lease_contract_period and instalment.leasee_contract_id.payment_frequency:
            total_contract_months = instalment.leasee_contract_id.lease_contract_period * (
                1 if instalment.leasee_contract_id.lease_contract_period_type == 'months' else 12)
            payment_freq_months = instalment.leasee_contract_id.payment_frequency * (
                1 if instalment.leasee_contract_id.payment_frequency_type == 'months' else 12)
            count = math.floor(total_contract_months / payment_freq_months)
        else:
            count = 0
        if instalment.leasee_contract_id.payment_frequency_type == 'months':
            deferred_end_date = instalment.date + dateutil.relativedelta.relativedelta(
                months=(
                    instalment.leasee_contract_id.payment_frequency)) - dateutil.relativedelta.relativedelta(
                days=1)
        else:
            deferred_end_date = instalment.date + dateutil.relativedelta.relativedelta(
                years=(
                    instalment.leasee_contract_id.payment_frequency)) - dateutil.relativedelta.relativedelta(
                days=1)

        invoice_lines = [(0, 0, {
            'name': self.name + ' - ' + instalment.date.strftime(
                '%d/%m/%Y'),
            'account_id': self.security_prepaid_account.id,
            'deferred_account_id': self.security_deferred_account.id,
            'price_unit': amount,
            'quantity': 1,
            'analytic_account_id': self.analytic_account_id.id,
            'project_site_id': self.project_site_id.id,
            'analytic_distribution': self.analytic_distribution,
            'deferred_start_date': instalment.date,
            'deferred_end_date': deferred_end_date,
        })]
        invoice = self.env['account.move'].create({
            'partner_id': partner.id,
            'move_type': 'in_invoice',
            'currency_id': self.leasee_currency_id.id,
            'ref': self.name + '- SD - ' + instalment.date.strftime(
                '%d/%m/%Y'),
            'invoice_date': invoice_date if invoice_date and self.sd_date_same_as_lease == 'no' else instalment.date,
            'invoice_date_due': instalment.date,
            'invoice_payment_term_id': self.env.ref(
                'account.account_payment_term_immediate').id,
            'invoice_line_ids': invoice_lines,
            'journal_id': self.installment_journal_id.id,
            'lease_security_advance_id': advance_security_id.id,
            # 'auto_post': 'at_date',
        })
        if invoice.date >= self.commencement_date and invoice.date <= self.inception_date:
            invoice.date = self.inception_date
            invoice.invoice_date_due = self.inception_date
            invoice.auto_post = 'at_date'

    def action_security_bills(self):
        advance_security_id = self.env['leasee.security.advance'].search(
            [('leasee_contract_id', '=', self.id)])
        if advance_security_id:
            domain = [
                ('lease_security_advance_id', 'in', advance_security_id.ids),
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
                [(
                    'lease_security_advance_id', '=',
                    self.security_advance_id.id),
                    ('date', '>', disposal_date)])
            security_moves.filtered(lambda x: x.state != 'draft').button_draft()
            # security_moves.button_draft()
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
                'nextcall': date + timedelta(seconds=15)
            })

    @api.model
    def security_advance_cron_update(self):
        date = fields.Datetime.now()
        schedule = self.env.ref(
            'lease_security_advance.action_advance_security_activation')
        schedule.update({
            'nextcall': date + timedelta(seconds=15)
        })

    @api.model
    def security_advance_set_deferred_start_and_end_date(self, limits):
        security_move_line = self.env['account.move.line'].search(
            [('move_id.lease_security_advance_id', '!=', False),
             ('move_id.move_type', 'in', ['in_invoice']),
             ('deferred_start_date', '=', False),
             ('deferred_end_date', '=', False),
             ('move_id.state', 'in', ['draft', 'to_approve']),
             ('debit', '>', 0)], limit=limits)
        for line in security_move_line:

            if line.move_id.lease_security_advance_id.leasee_contract_id.payment_frequency_type == 'months':
                line.deferred_end_date = line.move_id.invoice_date + dateutil.relativedelta.relativedelta(
                    months=(
                        line.move_id.lease_security_advance_id.leasee_contract_id.payment_frequency)) - dateutil.relativedelta.relativedelta(
                    days=1)
            else:
                line.deferred_end_date = line.move_id.invoice_date + dateutil.relativedelta.relativedelta(
                    years=(
                        line.move_id.lease_security_advance_id.leasee_contract_id.payment_frequency)) - dateutil.relativedelta.relativedelta(
                    days=1)
            line.deferred_start_date = line.move_id.invoice_date
        security_move_lines = self.env['account.move.line'].search(
            [('move_id.lease_security_advance_id', '!=', False),
             ('move_id.move_type', 'in', ['in_invoice']),
             ('deferred_start_date', '=', False),
             ('deferred_end_date', '=', False),
             ('move_id.state', 'in', ['draft', 'to_approve']),
             ('debit', '>', 0)], limit=limits)
        schedule = self.env.ref(
            'lease_security_advance.action_set_deferred_start_and_end_date_cron_update')
        if len(security_move_lines) > 0 and schedule.active:
            date = fields.Datetime.now()
            schedule.update({
                'nextcall': date + timedelta(seconds=15)
            })

    @api.model
    def security_advance_set_deferred_start_and_end_date_cron_update(self):
        date = fields.Datetime.now()
        schedule = self.env.ref(
            'lease_security_advance.action_set_deferred_start_and_end_date')
        schedule.update({
            'nextcall': date + timedelta(seconds=15)
        })


class SDLeasor(models.Model):
    _name = 'sd.leasor'
    _description = 'New SD Leasor'

    leasee_contract_id = fields.Many2one(comodel_name="leasee.contract",
                                         ondelete='cascade')
    partner_id = fields.Many2one(comodel_name="res.partner", required=True)
    type = fields.Selection(default="percentage",
                            selection=[('percentage', 'Percentage'),
                                       ('amount', 'Amount'), ], required=True, )
    amount = fields.Float(string="", default=0.0, required=False)
    percentage = fields.Float(string="", default=100, required=False)
