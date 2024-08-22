import odoo
import odoo.modules.registry
from odoo.api import call_kw
from odoo.addons.base.models.ir_qweb import render as qweb_render
from odoo.modules import get_resource_path, module
from odoo.tools.translate import _
from odoo.tools.misc import file_open, file_path
from odoo.tools.safe_eval import safe_eval, time
from odoo import http
from werkzeug.exceptions import BadRequest
from lxml import etree, html
from odoo.http import request, serialize_exception as _serialize_exception
from odoo.exceptions import AccessError, UserError, AccessDenied
import json
import base64
from odoo import SUPERUSER_ID


class DashboardEmbadeBits(http.Controller):
    def render_embade(self, dashboard_obj):
        params = {
            "dashboard_id": dashboard_obj.get("id"),
            "name": dashboard_obj.get("name"),
        }
        with file_open(
            "analytix_dashboard_bits/static/public/dashboard_embade_bits.html", "r"
        ) as fd:
            template = fd.read()

        def load(template_name, options):
            return (html.fragment_fromstring(templates[template_name]), template_name)

        return qweb_render(html.document_fromstring(template), params, load=load)

    @http.route("/dashboard/<int:dashboard_id>/embed", type="http", auth="none")
    def embade_dashboard_bits(self, dashboard_id, **kw):
        token = request.params.get("security_token")
        dashboard_obj = request.env["dashboard.bits"].sudo()
        if token and dashboard_id:
            dashboard_obj = dashboard_obj.search_read(
                fields=["id", "name", "is_public"],
                domain=[("security_token_bits", "=", token), ("id", "=", dashboard_id)],
            )
            if len(dashboard_obj) and dashboard_obj[0].get("is_public"):
                if request.db:
                    request.env.cr.close()
                return self.render_embade(dashboard_obj[0])
            else:
                if request.db:
                    request.env.cr.close()
                return BadRequest()
        if request.db:
            request.env.cr.close()
        return BadRequest()

    @http.route("/dashboard/<int:dashboard_id>/data", type="json", auth="none")
    def get_dashboard_data(self, dashboard_id, **kw):
        dashboard_obj = request.env["dashboard.bits"].sudo()
        if dashboard_id:
            dashboard_obj = dashboard_obj.browse(dashboard_id)
            filters = []
            if len(dashboard_obj.fav_filter_ids):
                active_filter = dashboard_obj.fav_filter_ids.filtered(
                    lambda x: x.is_active
                )
                filters = (
                    safe_eval(active_filter.filter_value, {})
                    if len(active_filter)
                    else []
                )
            dashboard_data = dashboard_obj.with_context(
                time_frame=dashboard_obj.default_time_frame,
                color_theme=dashboard_obj.default_color_theme.id,
                filters=filters,
            ).get_dashboard_data()
        return dashboard_data

    @http.route("/get/<int:item_id>/list", type="json", auth="none")
    def get_more_data(self, item_id, **kw):
        req = request.params
        dashboard_id = req.get("dashboard_id")
        params = {
            "model": req.get("model"),
            "target_event": req.get("target_event"),
            "curr_list": req.get("curr_list"),
        }
        return (
            request.env["dashboard.bits"]
            .sudo()
            .prepare_more_list_data(item_id, params, dashboard_id)
        )

    @http.route("/export/dashboard", type="json", auth="none")
    def export_dashboard(self, dashboard_id):
        dashboards = (
            request.env["dashboard.bits"]
            .sudo()
            .search_read([("id", ">", 0)], ["id", "name"])
        )
        return (
            request.env["dashboard.bits"].sudo().export_dashboard_action(dashboard_id)
        )

    # Favourite action
    @http.route("/get/dashboard/list", type="json", auth="none")
    def get_dashboard_list(self):
        dashboards = (
            request.env["dashboard.bits"]
            .sudo()
            .search_read([("id", ">", 0)], ["id", "name"])
        )
        return {"dashboards": dashboards}

    @http.route("/export/dashboard/item", type="json", auth="none")
    def export_dashboard_item(self, item_id):
        dashboards = (
            request.env["dashboard.bits"]
            .sudo()
            .search_read([("id", ">", 0)], ["id", "name"])
        )
        return request.env["dashboard.item.bits"].sudo().export_xlsx_item_data(item_id)

    # Favourite save action
    @http.route("/set/dashboard/action/view", type="json", auth="none")
    def set_dashboard_action_view(self, ids=[], data={}):
        data["context_to_save"] = json.loads(data["context_to_save"])
        data["domain"] = data["domain"]
        for id in ids:
            new_menu = request.env["dashboard.item.bits"].create(
                {"view_data": json.dumps(data)}
            )
            if new_menu:
                dashboard = request.env["dashboard.bits"].browse(id.get("id", False))
                if dashboard:
                    dashboard.write({"dashboard_item_ids": [(4, new_menu.id)]})
            else:
                return False
        return True
