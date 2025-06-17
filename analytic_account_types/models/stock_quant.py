# from odoo import api,fields,models,_
# from odoo.tools import float_compare, float_round
# from odoo.exceptions import ValidationError, AccessError
#
#
# class StockQuant(models.Model):
#     _inherit = 'stock.quant'
#
#     project_site_id = fields.Many2one(comodel_name="account.analytic.account",
#                                       string="Destination Project/Site",
#                                       domain=[('analytic_account_type', '=',
#                                                'project_site')],
#                                       )
#     source_project_site_id = fields.Many2one(comodel_name="account.analytic.account",
#                                              string=" Source Project/Site",
#                                              domain=[('analytic_account_type', '=',
#                                                       'project_site')],
#                                              )
