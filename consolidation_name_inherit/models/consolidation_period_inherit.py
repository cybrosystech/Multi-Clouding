from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ConsolidationPeriod(models.Model):
    _inherit = "consolidation.period"

    name = fields.Char(readonly=True)
    description = fields.Char()

    @api.constrains('chart_id', 'description')
    def name_update(self):
        self.name = self.chart_id.name
        if self.description:
            consolidation_period = self.search([('description', '=',
                                                 self.description)]).filtered(lambda x: x.id != self.id)
            if consolidation_period:
                raise ValidationError(
                    'The description has already configured for ' + consolidation_period.name)
            self.name = self.chart_id.name + ' ' + self.description

    def name_get(self):
        res = []
        for line in self:
            if line.name:
                res.append((line.id, line.name))
            else:
                demo = '/'
                res.append((line.id, demo))
        return res
