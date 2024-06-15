# -*- coding: utf-8 -*-
""" HR Payroll Multi Currency """

from odoo import api, fields, models


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'
    """
    HR Payroll Multi-Currency
    allow generate journal entry based on it
    """

    def _get_currency_amount(self, currency_from, currency_to, company_id,
                             amount, date=False):
        """

        :param currency_from: many2one
        :param currency_to: many2one
        :param company_id: many2one
        :param amount: float
        :param date: date
        :return: float
        """
        return currency_from._convert(amount,
                                      currency_to,
                                      company_id,
                                      date or fields.Date.today())

    def action_payslip_done(self):
        """ update journal entry created with new amount based on journal currency """
        res = super(HrPayslip, self).action_payslip_done()
        payslips_to_update = self.filtered(lambda slip: not slip.payslip_run_id)
        payslip_runs = (self - payslips_to_update).mapped('payslip_run_id')
        for run in payslip_runs:
            if run._are_payslips_ready():
                payslips_to_update |= run.slip_ids
        payslips_to_update = payslips_to_update.filtered(
            lambda slip: slip.state == 'done' and slip.move_id)
        for slip in payslips_to_update:
            if slip.journal_id.currency_id \
                    and slip.journal_id.currency_id != \
                    slip.journal_id.company_id.currency_id:
                currency_id = slip.journal_id.currency_id
                if slip.move_id:
                    for move_line in slip.move_id.line_ids:
                        original_debit = move_line.debit
                        original_credit = move_line.credit
                        amount = self._get_currency_amount(
                            currency_from=slip.journal_id.currency_id,
                            currency_to=slip.journal_id.company_id.currency_id,
                            company_id=slip.journal_id.company_id,
                            amount=original_debit if original_debit > 0.0 else original_credit,
                            date=slip.move_action_payslip_doneid.date)
                        move_line.with_context(check_move_validity=False).write(
                            {"debit": amount if original_debit > 0.0 else 0.0,
                             "credit": amount if original_credit > 0.0 else 0.0,
                             "amount_currency": original_debit if original_debit > 0.0 else -original_credit,
                             "currency_id": currency_id.id,
                             })
        return res

    @api.depends('struct_id', 'company_id')
    def _get_payslip_currency(self):
        """ appear currency of payslip """
        for rec in self:
            if rec.struct_id.journal_id.currency_id:
                rec.currency_id = rec.struct_id.journal_id.currency_id
            else:
                rec.currency_id = rec.company_id.currency_id

    currency_id = fields.Many2one(
        comodel_name='res.currency',
        readonly=True,
        compute="_get_payslip_currency",
        related="",
        store=True,
    )


# class HrPayslipLine(models.Model):
#     _inherit = 'hr.payslip.line'
#     amount = fields.Float()
#     total = fields.Float(compute='_compute_total', string='Total', store=True)
#     currency_id = fields.Many2one('res.currency', related='slip_id.currency_id')
