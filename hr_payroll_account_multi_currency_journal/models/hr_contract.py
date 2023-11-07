# -*- coding: utf-8 -*-
""" HR Payroll Multi Currency """

from odoo import api, fields, models


class HrContract(models.Model):
    _inherit = 'hr.contract'
    """
    HR Payroll Multi-Currency
    appear currency based on journal assigned in first salary structure
    """

    def _get_payslip_currency(self):
        """ return correct currency based on journal in default salary structure """
        for rec in self:
            if rec.structure_type_id.default_struct_id:
                if rec.structure_type_id.default_struct_id.journal_id.currency_id:
                    rec.currency_id = \
                        rec.structure_type_id.default_struct_id.journal_id.currency_id
                else:
                    rec.currency_id = \
                        rec.structure_type_id.default_struct_id.journal_id.company_id.currency_id
            else:
                rec.currency_id = rec.company_id.currency_id

    currency_id = fields.Many2one(
        comodel_name='res.currency',
        readonly=True,
        compute="_get_payslip_currency",
        related="",
    )
