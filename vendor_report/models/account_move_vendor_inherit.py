from collections import defaultdict

from odoo import models, api
from odoo.exceptions import ValidationError


class AccountMoveVendor(models.Model):
    _inherit = 'account.move'

    def vendor_report(self):
        pass
