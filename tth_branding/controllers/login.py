from odoo import http
from odoo.http import request
from odoo.addons.auth_oauth.controllers.main import OAuthLogin

class OAuthLoginOnly(OAuthLogin):
    @http.route()
    def web_login(self, *args, **kw):
        response = super(OAuthLoginOnly, self).web_login(*args, **kw)
        if request.params.get('password_login') == "1":
            response.qcontext['disable_password_login'] = False
        else:
            response.qcontext['disable_password_login'] = True
            response.qcontext['disable_footer'] = True
            response.qcontext['signup_enabled'] = False
            response.qcontext['reset_password_enabled'] = False   
        return response
