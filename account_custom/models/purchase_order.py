from odoo import models, api, fields


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id and self.product_id.business_unit_id:
            self.business_unit_id = self.product_id.business_unit_id.id
        else:
            self.business_unit_id = False
