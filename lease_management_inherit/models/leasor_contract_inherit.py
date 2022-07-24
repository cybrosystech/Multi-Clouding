from odoo import models, fields


class LeaseeContractTemplateInherit(models.Model):
    _inherit = 'leasor.contract'

    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.user.company_id)
