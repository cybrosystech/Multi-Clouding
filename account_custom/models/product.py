from odoo import fields, models
ACCOUNT_DOMAIN = "['&','&',('company_id','in',company_ids), ('deprecated', '=', False), ('account_type', 'not in', ('asset_receivable','liability_payable','asset_cash','liability_credit_card','off_balance'))]"

class Product(models.Model):
    _inherit = 'product.template'

    company_ids = fields.Many2many('res.company', string="Company")

    asset_account_id = fields.Many2one('account.account',
                                                  company_dependent=True,
                                                  string="Asset Account",
                                                  domain=ACCOUNT_DOMAIN,
                                                  )
    cip_account_id = fields.Many2one('account.account',
                                                  company_dependent=True,
                                                  string="CIP Account",
                                                  domain=ACCOUNT_DOMAIN,
                                                  )
    inventory_account_id = fields.Many2one('account.account',
                                                  company_dependent=True,
                                                  string="Inventory Account",
                                                  domain=ACCOUNT_DOMAIN,
                                                  )
    property_account_income_id = fields.Many2one('account.account',
                                                 company_dependent=True,
                                                 string="Income Account",
                                                 domain=ACCOUNT_DOMAIN,
                                                 help="Keep this field empty to use the default value from the product category.")
    property_account_expense_id = fields.Many2one('account.account',
                                                  company_dependent=True,
                                                  string="Expense Account",
                                                  domain=ACCOUNT_DOMAIN,
                                                  help="Keep this field empty to use the default value from the product category. If anglo-saxon accounting with automated valuation method is configured, the expense account on the product category will be used.")
