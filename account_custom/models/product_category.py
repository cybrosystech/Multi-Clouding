from odoo import fields, models
ACCOUNT_DOMAIN = "['&','&',('company_id','=',company_id),('deprecated', '=', False), ('account_type', 'not in', ('asset_receivable','liability_payable','asset_cash','liability_credit_card','off_balance'))]"

class Product(models.Model):
    _inherit = 'product.category'

    asset_account_id = fields.Many2one('account.account',
                                       check_company=True,
                                       domain="[('deprecated', '=', False)]",
                                      string="Asset Account",
                                      )
    cip_account_id = fields.Many2one('account.account',
                                     check_company=True,
                                     domain="[('deprecated', '=', False)]",
                                     string="CIP Account",
                                     )