
from odoo import models, fields, api
from odoo.addons.mail.models import mail_template
from odoo.addons.mail.models.mail_template import MailTemplate

class DefaultMailTemplate(models.Model):
    _inherit = 'mail.template'

    def send_mail(self, res_id, force_send=False, raise_exception=False, email_values=None, notif_layout=False):
        if not notif_layout:
            notif_layout = 'tth_branding.tth_branding_mail_layout'

        return super().send_mail(res_id, force_send=force_send, raise_exception=raise_exception, email_values=email_values, notif_layout=notif_layout)
