from odoo import models, fields


class LeaseeContractInherit(models.Model):
    _inherit = 'leasee.contract'

    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.user.company_id)
