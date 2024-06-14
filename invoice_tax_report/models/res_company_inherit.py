# -*- coding: utf-8 -*-
from odoo import models, fields


class ResCompany(models.Model):
    """Adding new fields to Company model"""
    _inherit = 'res.company'

    company_stamp = fields.Binary(string='Stamp')
    bank_name = fields.Char(string="Bank name")
    bank_account_name = fields.Char(string="Bank Account Name")
    iban = fields.Char(string="IBAN")
    short_code = fields.Char(string="Short Code")
    swift = fields.Char(string="SWIFT")
    footer_detail = fields.Text(string="Footer Detail")
