from odoo import models, fields


class AccountAnalyticAccountProject(models.Model):
    _inherit = 'account.analytic.account'

    site_address = fields.Char(string='Site Address')


class AccountAssetSite(models.Model):
    _inherit = 'account.asset'

    site_address = fields.Char(string='Site Address',
                               related='project_site_id.site_address')
