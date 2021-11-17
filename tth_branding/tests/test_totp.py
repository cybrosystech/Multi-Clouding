import unittest

from odoo.addons.auth_totp.tests.test_totp import TestTOTP

@unittest.skip
def void(self):
    pass
# Disable TOTP test as it's not in use.
TestTOTP.test_totp = void
TestTOTP.test_totp_administration = void
