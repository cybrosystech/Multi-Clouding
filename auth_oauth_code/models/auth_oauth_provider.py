import logging
import requests

from odoo import fields, models, tools

try:
    from jose import jwt
except ImportError:
    logging.getLogger(__name__).debug("python-jose library is not installed")


class AuthOauthProvider(models.Model):
    _inherit = "auth.oauth.provider"

    auth_flow = fields.Selection(
        [
            ("access_token", "OAuth2 (Odoo native implicit flow)"),
            ("code", "OAuth2 Authorization Code Grant"),
        ],
        string="Auth Flow",
        required=True,
        default="access_token",
    )
    claim_map = fields.Char(
        help="Map respective claim from ID Token to user_id. For example: email:user_id fullname:name"
    )
    client_secret = fields.Char(
        help="Used in authorization code flow to request token",
    )
    validation_endpoint = fields.Char(required=False)
    token_endpoint = fields.Char(
        string="Token URL", help="Required for OpenID Connect authorization code flow."
    )
    jwks_endpoint = fields.Char(string="JWKS URL", help="Used to validate JWT signature.")

    def _map_claims(self, res):
        if self.claim_map:
            for p in self.claim_map.split(" "):
                from_key, to_key = [k.strip() for k in p.split(":", 1)]
                if to_key not in res:
                    res[to_key] = res.get(from_key, "")
        return res

    @tools.ormcache("self.jwks_endpoint", "kid")
    def _get_jwks_key(self, kid):
        r = requests.get(self.jwks_endpoint)
        r.raise_for_status()
        response = r.json()
        for key in response["keys"]:
            if key["kid"] == kid:
                return key
        return {}

    def _validate_id_token(self, id_token, access_token):
        self.ensure_one()
        res = {}
        header = jwt.get_unverified_header(id_token)
        res.update(
            jwt.decode(
                id_token,
                self._get_jwks_key(header.get("kid")),
                algorithms=header.get("alg"),
                audience=self.client_id,
                access_token=access_token,
            )
        )

        res.update(self._map_claims(res))
        return res
