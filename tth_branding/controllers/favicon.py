from odoo import http
from odoo.tools.misc import file_open


class Favicon(http.Controller):

    @http.route('/favicon', type='http', auth="none")
    def pngicon(self):
        request = http.request
        favicon = file_open('tth_branding/static/src/img/favicon-32x32.png', 'rb')
        mimetype = 'image/png'
        return request.make_response(
            favicon.read(), [('Content-Type', mimetype)])