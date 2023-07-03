from odoo import fields, models


class AccountMove(models.Model):
    """ Add a field to account.move """
    _inherit = 'account.move'

    invoice_type = fields.Selection(string="Refund Type",
                                    selection=[
                                        ('out_refund', 'Credit Note '),
                                        ('in_refund', 'Debit Note')],
                                    default='out_refund')
