from odoo import models,fields

class StockLocation(models.Model):
    _inherit = 'stock.location'

    project_site_id = fields.Many2one('account.analytic.account',string="Project Site",
                                      domain=[('analytic_account_type', '=',
                                               'project_site')],
                                      )
