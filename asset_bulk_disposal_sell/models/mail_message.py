from odoo import api, _
from odoo.addons.account_audit_trail.models.mail_message import Message,bypass_token
from odoo.exceptions import UserError


@api.ondelete(at_uninstall=True)
def _except_audit_log(self):
    if self.env.context.get('bypass_audit') is bypass_token:
        return
    to_check = self
    partner_message = self.filtered(lambda m: m.account_audit_log_partner_id)
    if partner_message:
        # The audit trail uses the cheaper check on `customer_rank`, but that field could be set
        # without actually having an invoice linked (i.e. creation of the contact through the
        # Invoicing/Customers menu)
        has_related_move = self.env['account.move'].sudo().search_count([
            ('partner_id', 'in',
             partner_message.account_audit_log_partner_id.ids),
            ('company_id.check_account_audit_trail', '=', True),
        ], limit=1)
        if not has_related_move:
            to_check -= partner_message
    for message in to_check:
        if message.show_audit_log and not (
                message.account_audit_log_move_id
                and not message.account_audit_log_move_id.posted_before
        ) and not self.env.context.get('bypass_audit_log'):
            raise UserError(
                _("You cannot remove parts of the audit trail. Archive the record instead."))


Message._except_audit_log=_except_audit_log