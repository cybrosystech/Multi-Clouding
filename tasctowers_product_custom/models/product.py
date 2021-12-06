# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions, _

class ProductCategory(models.Model):
    _inherit = "product.category"

    company_id = fields.Many2one('res.company', string="Company")

class ProductTemplate(models.Model):
    _inherit = "product.template"

    categ_company_id = fields.Many2one('res.company', related="categ_id.company_id", string="Category Company")
