# -*- coding: utf-8 -*-
""" HR Payroll Multi Currency """

from odoo import api, models


class HrPayrollStructure(models.Model):
    _inherit = 'hr.payroll.structure'

    @api.constrains('journal_id')
    def _check_journal_id(self):
        """
        override odoo function implemented in this commit
        a96705b22738bc765553da0ac51d6f20e948bffa
        """
        pass
