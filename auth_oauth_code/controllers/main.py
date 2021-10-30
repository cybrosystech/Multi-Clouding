import base64
import hashlib
import logging
import secrets
import werkzeug.utils

from odoo.http import request
from odoo.addons.auth_oauth.controllers.main import OAuthLogin

_logger = logging.getLogger(__name__)

class OAuthCodeLogin(OAuthLogin):
    def list_providers(self):
        providers = super(OAuthCodeLogin, self).list_providers()
        for provider in providers:
            auth_flow = provider.get("auth_flow")
            if auth_flow == "code":
                params = werkzeug.url_decode(provider["auth_link"].split("?")[-1])
                params["nonce"] = secrets.token_urlsafe()
                params["response_type"] = "code"
                code_verifier = secrets.token_urlsafe(64)
                request.session["code_verifier"] = code_verifier # Save code_verifier to be used in request to token_endpoint
                code_challenge = base64.urlsafe_b64encode(
                    hashlib.sha256(code_verifier.encode("ascii")).digest()
                ).rstrip(b"=")
                params["code_challenge"] = code_challenge
                params["code_challenge_method"] = "S256"
                params["scope"] = provider["scope"]
                provider["auth_link"] = "{}?{}".format(
                    provider["auth_endpoint"], werkzeug.url_encode(params)
                )
        return providers
