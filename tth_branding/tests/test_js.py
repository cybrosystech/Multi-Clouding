# test_js.py
import re
import unittest

from odoo.addons.web.tests.test_js import WebSuite
from odoo.tests.common import tagged

RE_ONLY = re.compile('QUnit\.only\(')

@unittest.skip
def void(self):
    pass
# Disable native method.
WebSuite._check_only_call = void

# Rewrite native method to include <link/> and <title/> to web.layout template.
@tagged('post_install', '-at_install')
class WebSuiteInherited(WebSuite):
    def _check_only_call(self, suite):
        # As we currently aren't in a request context, we can't render `web.layout`.
        # redefinied it as a minimal proxy template.
        self.env.ref('web.layout').write({'arch_db': '<t t-name="web.layout"><head><meta charset="utf-8"/><link type="image/x-icon" rel="shortcut icon" t-att-href="x_icon"/><title t-esc="title"/><t t-raw="head"/></head></t>'})

        for asset in self.env['ir.qweb']._get_asset_content(suite, options={})[0]:
            filename = asset['filename']
            if not filename or asset['atype'] != 'text/javascript':
                continue
            with open(filename, 'rb') as fp:
                if RE_ONLY.search(fp.read().decode('utf-8')):
                    self.fail("`QUnit.only()` used in file %r" % asset['url'])
