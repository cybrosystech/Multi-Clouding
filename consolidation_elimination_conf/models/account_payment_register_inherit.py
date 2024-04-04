from odoo import models


class AccountPaymentRegisterInherit(models.TransientModel):
    _inherit = 'account.payment.register'

    def _create_payments(self):
        res = super(AccountPaymentRegisterInherit,
                    self)._create_payments()
        journal_id = self.env[self._context['active_model']].browse(self._context['active_id'])
        if journal_id.consolidation_bool:
            res.move_id.consolidation_bool = journal_id.consolidation_bool
            res.move_id.consolidation_company = journal_id.consolidation_company.id
        return res
