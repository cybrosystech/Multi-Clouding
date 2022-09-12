from odoo import models


class AccountMoveVendor(models.Model):
    _inherit = 'account.move'

    def vendor_report(self):
        pass
