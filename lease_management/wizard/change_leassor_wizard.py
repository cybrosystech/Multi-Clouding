# -*- coding: utf-8 -*-
""" init object """
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from datetime import date, datetime
import logging

LOGGER = logging.getLogger(__name__)


class ChangeLeasorWizard(models.TransientModel):
    _name = 'change.leasor.wizard'
    _description = 'Change Leasor Wizard'

    leasor_type = fields.Selection(string="Leasor Type",default="single", selection=[('single', 'Single'), ('multi', 'Multi'), ], required=True, )
    multi_leasor_ids = fields.One2many(comodel_name="change.leasor.line.wizard", inverse_name="wizard_id", string="", required=False, )
    vendor_id = fields.Many2one(comodel_name="res.partner", string="Leassor Name", required=False, )
    leasee_contract_id = fields.Many2one(comodel_name="leasee.contract", string="", required=False, )
    change_date = fields.Date(required=True)

    @api.model
    def default_get(self, fields):
        res = super(ChangeLeasorWizard, self).default_get(fields)
        leasee_contract_id = self._context.get('active_id')
        leasee_contract = self.env['leasee.contract'].browse(leasee_contract_id)
        res['leasor_type'] = leasee_contract.leasor_type
        res['leasee_contract_id'] = leasee_contract_id
        multi_leasor_vals = []
        for ml in leasee_contract.multi_leasor_ids:
            vals = (0,0,{
                'partner_id': ml.partner_id.id,
                'type': ml.type,
                'amount': ml.amount,
                'percentage': ml.percentage,
                'multi_leasor_id': ml.id,
            })
            multi_leasor_vals.append(vals)
        if multi_leasor_vals:
            res['multi_leasor_ids'] = multi_leasor_vals
        res['vendor_id'] = leasee_contract.vendor_id.id
        return res

    def check_leasor(self):
        percentage = 0
        if self.leasor_type == 'multi':
            for leasor in self.multi_leasor_ids:
                if leasor.type == 'percentage':
                    percentage += leasor.percentage
                else:
                    percentage += (leasor.amount / self.leasee_contract_id.installment_amount * 100)
            if round(percentage,2) != 100.0:
                raise ValidationError(_('Leasors Total must be 100%'))

    def check_date(self):
        if self.change_date < date.today():
            raise ValidationError(_('The date for applying the changes must be in the future'))

    def action_apply(self):
        self.check_leasor()
        contract = self.leasee_contract_id
        multi_leasor = contract.multi_leasor_ids
        vendor = contract.vendor_id
        company_lock_date = contract.company_id.period_lock_date
        if company_lock_date and self.change_date < company_lock_date:
            raise ValidationError(
                f"The date {self.change_date} cannot be earlier than the journal entries lock date {company_lock_date}."
            )
        if vendor:
            vendor_from = vendor.name
        elif multi_leasor:
            vendor_from = ', '.join(
                multi_leasor.mapped('partner_id').mapped('name'))
        else:
            vendor_from = ''
        if self.leasor_type != contract.leasor_type:
            contract.leasor_type = self.leasor_type
            bills = self.env['account.move'].search([
                ('leasee_contract_id', '=', contract.id),
                ('move_type', '=', 'in_invoice'),
                ('state', '=', 'draft'),
            ]).filtered(lambda m: m.invoice_date >= self.change_date)
            bills.sudo().unlink()

            if self.leasor_type == 'single':
                contract.multi_leasor_ids = [(5,)]
            elif self.leasor_type == 'multi':
                contract.vendor_id = False

        if self.leasor_type == 'single':
            if self.vendor_id != contract.vendor_id:
                contract.vendor_id = self.vendor_id.id
                bdy = 'Leasor Changed: ' + vendor_from + " -> " + contract.vendor_id.name
                contract.message_post(body=bdy)
                contract.multi_leasor_ids.unlink()
                bills = self.env['account.move'].search([
                    ('leasee_contract_id', '=', contract.id),
                    ('move_type', '=', 'in_invoice'),
                    ('state', '=', 'draft'),
                ]).filtered(lambda m: m.invoice_date >= self.change_date)
                bills.unlink()
                installments = self.env['leasee.installment'].search([
                    ('leasee_contract_id', '=', contract.id),
                ]).filtered(lambda i: i.date >= self.change_date)

                existing_posted_bills_dates = self.env['account.move'].search([
                    ('leasee_contract_id', '=', contract.id),
                    ('move_type', '=', 'in_invoice'),
                    ('state', '=', 'posted'),
                    ('date', '>=', self.change_date)
                ]).mapped('invoice_date')
                changed_bills = 0
                for installment in installments:
                    if installment.date not in existing_posted_bills_dates:
                        changed_bills +=1
                        contract.create_installment_bill(contract, installment, contract.vendor_id, installment.amount)
                not_changed_bills = len(installments.ids)- changed_bills
                body = 'Total bills updated = ' + str(changed_bills)
                if not_changed_bills:
                    body += ", Total Bills not updated (as status is posted) = " + str(not_changed_bills)

                body+= ",\nChanged Date = " +self.change_date.strftime('%d-%b-%Y')
                contract.message_post(body=body)
                
        if self.leasor_type == 'multi':
            if vendor:
                vendor_from = vendor.name
            else:
                vendor_from = ', '.join(multi_leasor.mapped('partner_id').mapped('name'))
            removed_lines = contract.multi_leasor_ids - self.multi_leasor_ids.mapped('multi_leasor_id')
            if removed_lines:
                for line in removed_lines:
                    bills = self.env['account.move'].search([
                        ('leasee_contract_id', '=', contract.id),
                        ('move_type', '=', 'in_invoice'),
                        ('state', '=', 'draft'),
                        ('partner_id', '=', line.partner_id.id),
                    ]).filtered(lambda m:  m.invoice_date >= self.change_date)
                    bills.sudo().unlink()
            removed_lines.sudo().unlink()
            changed_bills = 0
            not_changed_bills = 0
            for ml in self.multi_leasor_ids:
                if not ml.multi_leasor_id:
                    self.env['multi.leasor'].create({
                        'partner_id': ml.partner_id.id,
                        'type': ml.type,
                        'amount': ml.amount,
                        'percentage': ml.percentage,
                        'leasee_contract_id': contract.id,
                    })
                    installments = self.env['leasee.installment'].search([
                            ('leasee_contract_id', '=', contract.id),
                        ]).filtered(lambda i: i.date >= self.change_date)

                    existing_posted_bills_dates = self.env[
                        'account.move'].search([
                        ('leasee_contract_id', '=', contract.id),
                        ('move_type', '=', 'in_invoice'),
                        ('state', '=', 'posted'),
                        ('date', '>=', self.change_date)
                    ]).mapped('invoice_date')
                    changed_bills = 0
                    for install in installments:
                        partner = ml.partner_id
                        amount = (ml.amount / contract.installment_amount) * install.amount if ml.type == 'amount' else ml.percentage * install.amount / 100
                        if install.date not in existing_posted_bills_dates:
                            changed_bills+=1
                            contract.create_installment_bill(contract, install, partner, amount)
                    not_changed_bills = len(installments.ids) - changed_bills
                else:
                    bills = self.env['account.move'].search([
                        ('leasee_contract_id', '=', contract.id),
                        ('move_type', '=', 'in_invoice'),
                        ('state', '=', 'draft'),
                        ('partner_id', '=', ml.partner_id.id),
                    ]).filtered(lambda m: m.date >= self.change_date)
                    existing_posted_bills_dates = self.env[
                        'account.move'].search([
                        ('leasee_contract_id', '=', contract.id),
                        ('move_type', '=', 'in_invoice'),
                        ('state', '=', 'posted'),
                        ('date', '>=', self.change_date)
                    ]).mapped('invoice_date')
                    installments = self.env['leasee.installment'].search([
                            ('leasee_contract_id', '=', contract.id),
                        ]).filtered(lambda i: i.date >= self.change_date)

                    changed = False
                    if ml.partner_id != ml.multi_leasor_id.partner_id:
                        ml.multi_leasor_id.partner_id = ml.partner_id.id
                        changed = True
                    if ml.type != ml.multi_leasor_id.type:
                        ml.multi_leasor_id.type = ml.type
                        changed = True
                    if ml.amount != ml.multi_leasor_id.amount:
                        ml.multi_leasor_id.amount = ml.amount
                        changed = True
                    if ml.percentage != ml.multi_leasor_id.percentage:
                        ml.multi_leasor_id.percentage = ml.percentage
                        changed = True
                    if changed:
                        bills.sudo().unlink()
                        changed_bills = 0
                        for install in installments:
                            partner = ml.partner_id
                            amount = (ml.amount / contract.installment_amount) * install.amount if ml.type == 'amount' else ml.percentage * install.amount / 100
                            if install.date not in existing_posted_bills_dates:
                                changed_bills +=1
                                contract.create_installment_bill(contract, install, partner, amount)
                        not_changed_bills = len(
                            installments.ids) - changed_bills

            vendor_to = ','.join(contract.multi_leasor_ids.mapped('partner_id').mapped('name'))
            bdy = 'Leasor Changed: ' + vendor_from + " -> " + vendor_to
            contract.message_post(body=bdy)

            body = 'Total bills updated = ' + str(
                changed_bills)
            if not_changed_bills:
                body += "," + "Total Bills not updated (as status is  posted) = " + str(
                not_changed_bills)
            body += ",\nChanged Date = " +self.change_date.strftime('%d-%b-%Y')
            contract.message_post(body=body)


class ChangeLeasorLineWizard(models.TransientModel):
    _name = 'change.leasor.line.wizard'
    _description = 'Change Leasor Lines Wizard'
    
    wizard_id = fields.Many2one(comodel_name="change.leasor.wizard",ondelete='cascade')
    partner_id = fields.Many2one(comodel_name="res.partner",required=True )
    type = fields.Selection(default="percentage", selection=[('percentage', 'Percentage'), ('amount', 'Amount'), ], required=True, )
    amount = fields.Float(string="", default=0.0, required=False)
    percentage = fields.Float(string="", default=0.0, required=False)
    multi_leasor_id = fields.Many2one(comodel_name="multi.leasor", string="", required=False, )

