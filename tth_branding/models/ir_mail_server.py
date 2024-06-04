# Copyright 2014 Ivan Yelizariev <https://it-projects.info/team/yelizariev>
# Copyright 2019 Anvar Kildebekov <https://it-projects.info/team/fedoranvar>
# License MIT (https://opensource.org/licenses/MIT).

import base64
import re

from odoo import models, tools
from odoo.loglevels import ustr

from email.message import EmailMessage
from email.utils import make_msgid
import datetime
import email
import email.policy
import logging
import re

import html2text

from odoo.tools import ustr, pycompat

_logger = logging.getLogger(__name__)
_test_logger = logging.getLogger('odoo.tests')


class IrMailServer(models.Model):
    _inherit = "ir.mail_server"

    def build_email(self, email_from, email_to, subject, body, email_cc=None,
                    email_bcc=None, reply_to=False,
                    attachments=None, message_id=None, references=None,
                    object_id=False, subtype='plain', headers=None,
                    body_alternative=None, subtype_alternative='plain'):

        ftemplate = "__image-%s__"
        fcounter = 0
        attachments = attachments or []

        pattern = re.compile(r'"data:image/png;base64,[^"]*"')
        pos = 0
        new_body = ""
        body = body or ""
        while True:
            match = pattern.search(body, pos)
            if not match:
                break
            s = match.start()
            e = match.end()
            data = body[s + len('"data:image/png;base64,'): e - 1]
            new_body += body[pos:s]
            fname = ftemplate % fcounter
            fcounter += 1
            attachments.append((fname, base64.b64decode(data), 'image/png'))

            new_body += '"cid:%s"' % fname
            pos = e

        new_body += body[pos:]
        body = new_body

        email_from = email_from or self._get_default_from_address()
        assert email_from, "You must either provide a sender address explicitly or configure " \
                           "using the combination of `mail.catchall.domain` and `mail.default.from` " \
                           "ICPs, in the server configuration file or with the " \
                           "--email-from startup parameter."

        headers = headers or {}  # need valid dict later
        email_cc = email_cc or []
        email_bcc = email_bcc or []
        body = body or u''

        msg = EmailMessage(policy=email.policy.SMTP)
        msg.set_charset('utf-8')

        if not message_id:
            if object_id:
                message_id = tools.generate_tracking_message_id(object_id)
            else:
                message_id = make_msgid()
        msg['Message-Id'] = message_id
        if references:
            msg['references'] = references
        msg['Subject'] = subject

        email_from, return_path = self._get_email_from(email_from)
        msg['From'] = email_from
        if return_path:
            headers.setdefault('Return-Path', return_path)

        del msg['Reply-To']
        msg['Reply-To'] = reply_to or email_from
        msg['To'] = email_to
        if email_cc:
            msg['Cc'] = email_cc
        if email_bcc:
            msg['Bcc'] = email_bcc
        msg['Date'] = datetime.datetime.utcnow()
        for key, value in headers.items():
            msg[pycompat.to_text(ustr(key))] = value

        email_body = ustr(body)
        if subtype == 'html' and not body_alternative:
            msg.add_alternative(html2text.html2text(email_body),
                                subtype='plain', charset='utf-8')
            msg.add_alternative(email_body, subtype=subtype, charset='utf-8')
        elif body_alternative:
            msg.add_alternative(ustr(body_alternative),
                                subtype=subtype_alternative, charset='utf-8')
            msg.add_alternative(email_body, subtype=subtype, charset='utf-8')
        else:
            msg.set_content(email_body, subtype=subtype, charset='utf-8')

        if attachments:
            for (fname, fcontent, mime) in attachments:
                maintype, subtype = mime.split(
                    '/') if mime and '/' in mime else (
                    'application', 'octet-stream')
                msg.add_attachment(fcontent, maintype, subtype, filename=fname,
                                   cid="<%s>" % fname)
        return msg
