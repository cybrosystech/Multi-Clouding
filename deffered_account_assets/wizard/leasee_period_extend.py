from odoo import models,_
from odoo.exceptions import UserError


class LeaseePeriodExtend(models.TransientModel):
    _inherit = 'leasee.period.extend'

    def action_apply(self):
        if self.leasee_contract_id.asset_id.state in ('draft','to_approve'):
            raise UserError(_('Please confirm asset before extending lease.'))
        super(LeaseePeriodExtend, self).action_apply()

