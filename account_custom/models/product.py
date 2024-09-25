from odoo import fields, models
ACCOUNT_DOMAIN = "['&', ('deprecated', '=', False), ('account_type', 'not in', ('asset_receivable','liability_payable','asset_cash','liability_credit_card','off_balance'))]"

class Product(models.Model):
    _inherit = 'product.template'

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
