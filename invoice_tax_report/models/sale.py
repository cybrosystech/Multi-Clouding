# -*- coding: utf-8 -*-

import math
from odoo import api, fields, models, _

class Sale(models.Model):
    _inherit = 'sale.order'

    service_date_from = fields.Date('Service Date From')
    service_date_to = fields.Date('Service Date To')

    # def _prepare_invoice(self):
    #     res = super(Sale, self)._prepare_invoice()
    #     res.update({
    #         'service_date_from':self.service_date_from,
    #         'service_date_to':self.service_date_to,
    #     })
    #     return res