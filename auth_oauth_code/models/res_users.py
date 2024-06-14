import logging
import requests

from odoo import api, models, fields
from odoo.exceptions import AccessDenied
from odoo.http import request

_logger = logging.getLogger(__name__)

class ResUsers(models.Model):
    _inherit = "res.users"
    
    oauth_enforced = fields.Boolean(string='Enforce OAuth')

    # def __init__(self, pool, cr):
    #     """ Override of __init__ to add access rights on oauth_enforced
    #         field. Access rights are disabled by default, but allowed on some
    #         specific fields defined in self.SELF_{READ/WRITE}ABLE_FIELDS.
    #     """
    #     init_res = super(ResUsers, self).__init__(pool, cr)
    #     type(self).SELF_READABLE_FIELDS = list(self.SELF_READABLE_FIELDS)
    #     type(self).SELF_READABLE_FIELDS.extend(['oauth_enforced'])
    #     return init_res

    def _get_tokens(self, oauth_provider, params):
        response = requests.post(
            oauth_provider.token_endpoint,
            data=dict(
                client_id=oauth_provider.client_id,
                grant_type="authorization_code",
                code=params.get("code"),
                code_verifier=request.session["code_verifier"],
                redirect_uri=request.httprequest.url_root + "auth_oauth/signin",
                client_secret=oauth_provider.client_secret
            )
        )
        response_json = response.json()
        return response_json.get("access_token"), response_json.get("id_token")

    @api.model
    def _generate_signup_values(self, provider, validation, params):
        oauth_uid = validation['user_id']
        email = validation.get('email', 'provider_%s_user_%s' % (provider, oauth_uid))
        name = validation.get('name', email)
        return {
            'name': name,
            'login': email,
            'email': email,
            'oauth_provider_id': provider,
            'oauth_uid': oauth_uid,
            'oauth_access_token': params['access_token'],
            'active': True,
            'oauth_enforced': True
        }

    @api.model
    def auth_oauth(self, provider, params):
        oauth_provider = self.env["auth.oauth.provider"].browse(provider)
        if oauth_provider.auth_flow == "code":
            access_token, id_token = self._get_tokens(
                oauth_provider, params
            )
        else:
            return super(ResUsers, self).auth_oauth(provider, params)
        if not access_token:
            _logger.error("access_token is not found in the responce from auth provider.")
            raise AccessDenied()
        if not id_token:
            _logger.error("id_token is not found in the responce from auth provider.")
            raise AccessDenied()
        validation = oauth_provider._validate_id_token(id_token, access_token)
        if not validation.get("user_id"):
            _logger.error("user_id claim not found in id_token (after mapping).")
            raise AccessDenied()
        params["access_token"] = access_token
        login = self._auth_oauth_signin(provider, validation, params)
        if not login:
            raise AccessDenied()
        return (self.env.cr.dbname, login, access_token)

    def _check_credentials(self, password, env):
        try:
            if self.env.user.oauth_enforced:
                raise AccessDenied()
            else:
                return super(ResUsers, self)._check_credentials(password, env)
                
        except AccessDenied:
            passwd_allowed = env['interactive'] or not self.env.user._rpc_api_keys_only()
            if passwd_allowed and self.env.user.active:
                res = self.sudo().search([('id', '=', self.env.uid), ('oauth_access_token', '=', password)])
                if res:
                    return
            raise
