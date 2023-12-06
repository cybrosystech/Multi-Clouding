from odoo import models, fields


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    product_expense_type = fields.Selection(string="Expense Type", selection=[
        ('overtime', 'Over Time'), ('per_diem', 'Per Diem'),
        ('others', 'Others'), ('reimbursement', 'Reimbursement')])


class Product(models.Model):
    _inherit = 'product.product'

    product_expense_type = fields.Selection(string="Expense Type", related='product_tmpl_id.product_expense_type')
