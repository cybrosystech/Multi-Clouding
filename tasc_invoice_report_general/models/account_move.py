from odoo import fields, models


class AccountMove(models.Model):
    """ Add a field to account.move """
    _inherit = 'account.move'

    invoice_type = fields.Selection(string="Refund Type",
                                    selection=[
                                        ('out_refund', 'Customer Credit Note '),
                                        ('in_refund', 'Vendor Debit Note')],
                                    default='out_refund')
