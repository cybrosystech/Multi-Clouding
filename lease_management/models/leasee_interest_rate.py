from odoo import models, fields


class LeaseeInterestRate(models.Model):
    _name = 'leasee.interest.rate'
    _description = 'Leasee Interest Rate'
    _rec_name = 'years'

    company_id = fields.Many2one('res.company', string='Company',
                                 required=True, tracking=True, )
    years = fields.Integer(string="Years", help="Number of years",
                           required=True, tracking=True, )
    rate = fields.Float(string="Rate", help="Interest Rate", required=True,
                        tracking=True, )

    _sql_constraints = [
        ('unique_company_years', 'unique(company_id, years)',
         'The combination of Company and Years must be unique.')
    ]
