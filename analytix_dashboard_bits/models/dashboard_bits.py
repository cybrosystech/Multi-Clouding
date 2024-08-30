from odoo import models, fields, api, _
import json
import uuid
from datetime import date,datetime,timedelta
from . import date_util as du
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from odoo.tools.safe_eval import safe_eval
import base64
from odoo.addons.advanced_web_domain_widget.models.domain_prepare import (
    prepare_domain_v2,
)


class DashboardBits(models.Model):
    _name = "dashboard.bits"
    _description = "For individual dashboard records."

    name = fields.Char("Dashboard Name")
    menu_name = fields.Char("Dashboard Menu Name", readonly=False, store=True)
    is_main_menu = fields.Boolean("Add Dashboard To Main menu", default=True)
    dashboard_icon = fields.Binary(
        "Main Menu icon", help="Upload Dashboard icon to show in main menu screen."
    )
    parent_menu_id = fields.Many2one(
        "ir.ui.menu",
        "Display under the menu",
        related="dashboard_menu_id.parent_id",
        readonly=False,
        help="Select parent menu id to display this dashboard menu under the selcted parent menu.",
    )

    d_icon_bits = fields.Char("Dashboard Icon", default="i mdi-light:view-dashboard")
    active = fields.Boolean(
        "Active",
        default=True,
        help="Enable to display dashboard on the dashboards screen.",
    )
    client_action_id = fields.Many2one("ir.actions.client", "Client Action")
    dashboard_menu_id = fields.Many2one("ir.ui.menu", "Dashboard Menu")
    menu_sequence = fields.Integer(related="dashboard_menu_id.sequence", readonly=False)
    dashboard_item_ids = fields.One2many(
        "dashboard.item.bits", "bits_dashboard_id", "Dashboard Item"
    )
    grid_config_id = fields.Many2one(
        "dashboard.gird.config",
        "Config Template",
        help="Select configuration template to add demo data layout in the dashboard.",
    )
    grid_config = fields.Char("Grid Configurations")
    time_frame = fields.Char()
    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
    )
    start_date = fields.Date()
    end_date = fields.Date()
    default_time_frame = fields.Selection(
        [
            ("default", "Default"),
            ("today", "Today"),
            ("next_day", "Next Day"),
            ("next_week", "Next Week"),
            ("next_month", "Next Month"),
            ("next_year", "Next Year"),
            ("this_week", "This Week"),
            ("this_month", "This Month"),
            ("this_year", "This Year"),
            ("yesterday", "Yesterday"),
            ("last_week", "Last Week"),
            ("last_month", "Last Month"),
            ("last_two_months", "Last 2 Months"),
            ("last_three_months", "Last 3 Months"),
            ("last_year", "Last Year"),
            ("last_24_hr", "Last 24 Hours"),
            ("last_10", "Last 10 Days"),
            ("last_30", "Last 30 Days"),
            ("last_60", "Last 60 Days"),
            ("last_90", "Last 90 Days"),
            ("last_365", "Last 365 Days"),
            ("custom", "Custom Range"),
        ],
        string="Default TimeFrame",
        default="default",
        help="Select the default timeframe to load dashboard data between selected timeframe.",
    )

    default_start_date = fields.Char()
    default_end_date = fields.Char()

    default_color_theme = fields.Many2one(
        "dashboard.themes",
        string="Default Color Theme",
        help="Select the default color theme to load dashboard charts eith selected color theme.",
    )
    filter_ids = fields.One2many(
        "dashboard.filter.bits",
        "dashboard_id",
        help="Add filters to show on dashboard header.",
    )
    default_view_mode = fields.Selection(
        [("light", "Light"), ("dark", "Dark")],
        default="light",
        string="Default View Mode",
        help="Selected view mode will applied on dashboard load time either light or dark.",
    )
    fav_filter_ids = fields.One2many(
        "favorite.filter.bits", "dashboard_id", string="Favorite Filters"
    )
    security_token_bits = fields.Char("Security Token")
    group_ids = fields.Many2many(
        "res.groups",
        related="dashboard_menu_id.groups_id",
        readonly=False,
        string="Groups",
        help="Add the group to show this dashboard only those users who has entered group access.",
    )
    is_public = fields.Boolean("Enable Sharing")

    @api.model
    def default_get(self, default_fields):
        res = super().default_get(default_fields)
        default_theme = self.env["dashboard.themes"].search(
            [("is_default", "=", True)], limit=1
        )
        if default_theme:
            res["default_color_theme"] = default_theme.id
        return res

    @api.onchange("is_main_menu")
    def onchange_is_main_menu(self):
        for rec in self:
            if rec.is_main_menu:
                rec.parent_menu_id = False

    @api.model_create_multi
    def create(self, vals_list):
        records = super(DashboardBits, self).create(vals_list)
        for record in records:
            dashboard_action = {
                "name": record.menu_name
                if record.menu_name
                else record.name,
                "res_model": "dashboard.bits",
                "tag": "bits_dashboard_action",
                "params": {
                    "dashboard_id": record.id,
                    "default_color_theme": record.default_color_theme.id or False,
                    "default_time_frame": record.default_time_frame,
                    "default_view_mode": record.default_view_mode,
                },
            }
            record.client_action_id = (
                self.env["ir.actions.client"].sudo().create(dashboard_action)
            )
            record.dashboard_menu_id = (
                self.env["ir.ui.menu"]
                .sudo()
                .create(
                    {
                        "name": record.menu_name,
                        "active": record.active,
                        "parent_id": record.parent_menu_id.id,
                        "action": "ir.actions.client,"
                        + str(record.client_action_id.id),
                    }
                )
            )
            if record.dashboard_icon and record.is_main_menu:
                record.dashboard_menu_id.sudo().write(
                    {"web_icon_data": record.dashboard_icon}
                )
            self.assign_grid_data(record)
        return records

    def write(self, vals):
        res = super(DashboardBits, self).write(vals)
        temp = {}

        if vals.get("default_color_theme"):
            temp.update({"default_color_theme": self.default_color_theme.id or False})

        if vals.get("default_time_frame"):
            temp.update({"default_time_frame": self.default_time_frame})

        if vals.get("default_view_mode"):
            temp.update({"default_view_mode": self.default_view_mode})

        if vals.get("menu_name"):
            self.client_action_id.write({"name": self.menu_name})

        if vals.get("dashboard_icon") and self.is_main_menu:
            self.dashboard_menu_id.sudo().write({"web_icon_data": self.dashboard_icon})

        if temp:
            x = self.client_action_id.params_store
            x = safe_eval(x.decode())
            x.update(temp)
            self.client_action_id.params_store = str.encode(str(x))

        if not len(self.client_action_id):
            dashboard_action = {
                "name": self.menu_name if self.menu_name else self.name,
                "res_model": "dashboard.bits",
                "tag": "bits_dashboard_action",
                "params": {
                    "dashboard_id": self.id,
                    "default_color_theme": self.default_color_theme.id or False,
                    "default_time_frame": self.default_time_frame,
                    "default_view_mode": self.default_view_mode,
                },
            }
            self.client_action_id = (
                self.env["ir.actions.client"].sudo().create(dashboard_action)
            )
            self.dashboard_menu_id = (
                self.env["ir.ui.menu"]
                .sudo()
                .create(
                    {
                        "name": self.menu_name if self.menu_name else self.name,
                        "active": self.active,
                        "parent_id": self.parent_menu_id.id,
                        "action": "ir.actions.client," + str(self.client_action_id.id),
                    }
                )
            )
        else:
            if "menu_name" in vals:
                self.client_action_id.sudo().update(
                    {
                        "name": vals.get("menu_name")
                        if vals.get("menu_name")
                        else self.name
                    }
                )
                self.dashboard_menu_id.sudo().update(
                    {
                        "name": vals.get("menu_name")
                        if vals.get("menu_name")
                        else self.name
                    }
                )
        return res

    def unlink(self):
        if self.client_action_id:
            self.client_action_id.unlink()
        if self.dashboard_menu_id:
            self.dashboard_menu_id.unlink()
        return super().unlink()

    @api.model
    def unlink_dashboard_bits(self, item_id):
        item_obj = False
        if item_id:
            item_obj = self.sudo().browse(item_id).unlink()
            self.env.cr.commit()
        return item_obj

    def assign_grid_data(self, record):
        if record.grid_config_id.grid_config_bits:
            dashboard_configuration = {}
            template_configurations = json.loads(record.grid_config_id.grid_config_bits)
            for d_item in template_configurations:
                dashboard_item = self.env.ref(d_item["d_item_id"]).copy(
                    {"bits_dashboard_id": record.id}
                )
                dashboard_configuration['item_'+str(dashboard_item.id)] = d_item["data"]
            record.grid_config = json.dumps(dashboard_configuration)

    def prepare_date_domain(self, date_field="create_date"):
        domain = []

        today = date.today()
        time_frame = self._context.get("time_frame", False)
        if not time_frame:
            time_frame = self.default_time_frame

        if self._context.get("previous_data", False):
            today = self.start_date
            if time_frame == "today":
                time_frame = "last_1"
            elif time_frame == "this_week":
                time_frame = "last_week"
            elif time_frame == "this_month":
                time_frame = "last_month"
            elif time_frame == "this_year":
                time_frame = "last_year"

        if time_frame:
            if time_frame == "today":
                start_date, end_date = du.today_dates(today)
            elif time_frame == "next_day":
                start_date, end_date = du.next_day_dates(today)
            elif time_frame == "next_week":
                start_date, end_date = du.next_week_dates(today)
            elif time_frame == "next_month":
                start_date, end_date = du.next_month_dates(today)
            elif time_frame == "next_year":
                start_date, end_date = du.next_year_dates(today)
            elif time_frame == "this_week":
                start_date, end_date = du.current_week_dates(today)
            elif time_frame == "this_month":
                start_date, end_date = du.current_month_dates(today)
            elif time_frame == "this_year":
                start_date, end_date = du.current_year_dates(today)
            elif time_frame == "yesterday":
                start_date, end_date = du.past_days_dates(today)
            elif time_frame == "last_week":
                start_date, end_date = du.past_week_dates(today)
            elif time_frame == "last_month":
                start_date, end_date = du.past_month_dates(today)
            elif time_frame == "last_two_month":
                start_date, end_date = du.past_month_dates(today, count=2)
            elif time_frame == "last_three_month":
                start_date, end_date = du.past_month_dates(today, count=3)
            elif time_frame == "last_year":
                start_date, end_date = du.past_year_dates(today)
            elif time_frame == 'last_24_hr':
                today = datetime.today()
                start_date, end_date = du.past_24_hr_dates(today)
            elif time_frame == "last_10":
                start_date, end_date = du.past_days_dates(today, count=10)
            elif time_frame == "last_20":
                start_date, end_date = du.past_days_dates(today, count=20)
            elif time_frame == "last_30":
                start_date, end_date = du.past_days_dates(today, count=30)
            elif time_frame == "last_60":
                start_date, end_date = du.past_days_dates(today, count=60)
            elif time_frame == "last_90":
                start_date, end_date = du.past_days_dates(today, count=90)
            elif time_frame == "last_365":
                start_date, end_date = du.past_days_dates(today, count=365)
            elif time_frame == "custom":
                start_date, end_date = self._context.get(
                    "from_date", False
                ), self._context.get("to_date", False)
                if start_date:
                    start_date = fields.datetime.strptime(
                        start_date, DEFAULT_SERVER_DATE_FORMAT
                    )
                if end_date:
                    end_date = fields.datetime.strptime(
                        end_date, DEFAULT_SERVER_DATE_FORMAT
                    )
            else:
                start_date, end_date = False, False

            if start_date:
                if start_date == end_date:
                    end_date = start_date + timedelta(days=1)
                self.start_date = start_date
                domain.append(
                    (
                        date_field,
                        ">=",
                        fields.datetime.strftime(
                            start_date, DEFAULT_SERVER_DATETIME_FORMAT
                        ),
                    )
                )

            if end_date:
                domain.append(
                    (
                        date_field,
                        "<",
                        fields.datetime.strftime(
                            end_date, DEFAULT_SERVER_DATETIME_FORMAT
                        ),
                    )
                )
        return domain

    def duplicate_dashboard(self):
        dashboard_items = self.dashboard_item_ids
        new_dashboard_items = []
        grid_config = json.loads(self.grid_config or "") if self.grid_config else {}
        new_grid_config = {}
        for rec in dashboard_items:
            new_rec = rec.copy()
            new_dashboard_items.append(new_rec.id)
            if self.grid_config and grid_config.get(str(rec.id)):
                new_grid_config['item_'+str(new_rec.id)] = grid_config['item_'+str(rec.id)]
        new_rec_data = {
            "dashboard_item_ids": new_dashboard_items,
            "name": self.name + "[duplicate]",
            "grid_config": json.dumps(new_grid_config) if self.grid_config else False,
            "client_action_id": False,
            "menu_name": (self.menu_name if self.menu_name else self.name)
            + "[duplicate]",
            "dashboard_menu_id": False,
        }
        if not self.parent_menu_id:
            new_rec_data["parent_menu_id"] = False
        new_dashboard = self.sudo().copy(new_rec_data)
        dashboard_action_config = {
            "type": "ir.actions.client",
            "tag": "bits_dashboard_action",
            "context": {
                "params": {
                    "dashboard_id": new_dashboard.id,
                    "default_color_theme": new_dashboard.default_color_theme.id,
                    "default_time_frame": new_dashboard.default_time_frame,
                    "default_view_mode": new_dashboard.default_view_mode,
                }
            },
        }
        return dashboard_action_config

    def get_dashboards(self, search):
        data = {}
        domain = []
        if search:
            domain = [("name", "ilike", search)]
        dashboards = self.sudo().search_read(domain)
        
        data["dashboards"] = []
        for dashboard in dashboards:
            # dashboard['group_ids']=self.env.user.sudo().groups_id[0]
            if dashboard.get("group_ids"):
                for group in dashboard.get("group_ids"):
                    eml_id = (
                        self.env["ir.model.data"]
                        .sudo()
                        .search([("res_id", "=", group), ("model", "=", "res.groups")])
                    )
                    has_group = self.env.user.sudo().has_group(eml_id.complete_name)
                    if has_group and dashboard not in data["dashboards"]:
                        data["dashboards"].append(dashboard)
            else:
                data["dashboards"].append(dashboard)

        has_group_admin_bits = self.env.user.sudo().has_group(
            "analytix_dashboard_bits.dashboard_builder_manager_bits"
        )
        data["has_group_admin_bits"] = has_group_admin_bits
        data["search"] = search
        return data

    def get_dashboard_data(self):
        dashboard_data = {}
        if self:
            time_frame = self._context.get("time_frame", False)
            color_theme = self._context.get("color_theme", False)
            items = self.dashboard_item_ids
            has_group_admin_bits = self.env.user.sudo().has_group("analytix_dashboard_bits.dashboard_builder_manager_bits")
            grid_config = json.loads(self.grid_config) if self.grid_config else False 
            dashboard_data.update(
                {
                    "grid_config": grid_config,
                    "grid_config_id": self.grid_config_id.id,
                    "dashboard_id": self.id,
                    "name": self.name,
                    "time_frame": time_frame,
                    "default_from_date": self.default_start_date
                    or self._context.get("from_date", False),
                    "default_to_date": self.default_end_date
                    or self._context.get("to_date", False),
                    "default_color_theme": color_theme,
                    "default_view_mode": self.default_view_mode or False,
                    "dashboards": self.sudo().search_read(
                        [("active", "=", True)], fields=["name"]),
                    "has_group_admin_bits": has_group_admin_bits,
                    "default_theme_paletts": self.default_color_theme.get_color_palette()
                    if self.default_color_theme
                    else ["#017e84", "#52374b"],
                    "is_public": self.is_public,
                }
            )

            dashboard_items = {}
            for item in items:
                item_id = 'item_' + str(item.id) 
                item_dict = {}
                data = item.prepare_item_data()
                if data:
                    item_dict.update(data)
                    dashboard_items[item_id] = item_dict
            dashboard_data["dashboard_items"] = dashboard_items
            dashboard_data["filters"] = self.get_dashboard_filters()

        return dashboard_data

    def remove_custom_view(self, custom_view_id):
        view = self.env["dashboard.item.bits"].browse(int(custom_view_id))
        res = view.unlink()
        return res

    @api.model
    def prepare_more_list_data(self, item, list_set, dashboard_id):
        data = {}
        model = list_set.get("model")
        item_obj = self.env["dashboard.item.bits"].sudo().browse(item)
        if not model:
            model = item_obj.model_name
        offset = list_set.get("curr_list")
        order = item_obj.display_order
        offset = list_set.get("curr_list")

        list_data = []
        if item_obj.is_query:
            field_names = (
                list(json.loads(item_obj.y_axis).items()) if item_obj.y_axis else []
            )
            data["fields"] = field_names
            list_data = item_obj.get_data_in_pandas()
            # list_data = item_obj.get_data_from_query()
            if not isinstance(list_data, list):
                if not list_data.empty and item_obj.y_axis:
                    try:
                        list_data = list(list_data.to_dict(orient='index', into=dict).values())
                    except Exception as e:
                        print(e)
                else:
                    list_data = []
        else:
            fields_list = [f.name for f in item_obj.sudo().list_view_field_ids]
            field_names = [
                [f.name, f.field_description]
                for f in item_obj.sudo().list_view_field_ids
            ]
            data["fields"] = field_names
            if self.time_frame:
                if self.env[model].sudo()._fields.get("create_date"):
                    list_data = (
                        self.env[model]
                        .sudo()
                        .search_read(
                            item_obj.get_item_domain(),
                            fields_list,
                            order=f'{fields_list[0] if fields_list and len(fields_list) > 0 else "display_name"} {"desc" if order and order == "descending" else "asc"}',
                        )
                    )
                else:
                    new_domain = []
                    for domm in safe_eval(self.item_domain):
                        if "date_filter" in domm:
                            date_domain = prepare_domain_v2(domm)
                            for dom in date_domain:
                                new_domain.append(dom)
                        else:
                            new_domain.append(domm)
                list_data = (
                    self.env[model]
                    .sudo()
                    .search_read(
                        new_domain,
                        fields_list,
                        order=f'{fields_list[0] if fields_list and len(fields_list) > 0 else "display_name"} {"desc" if order and order == "descending" else "asc"}',
                    )
                )
            else:
                list_data = (
                    self.env[model]
                    .sudo()
                    .search_read(
                        item_obj.get_item_domain(),
                        fields_list,
                        order=f'{fields_list[0] if fields_list and len(fields_list) > 0 else "display_name"} {"desc" if order and order == "descending" else "asc"}',
                    )
                )

        target_event = list_set.get("target_event")
        data["is_next"] = False
        data["is_previous"] = False
        records_per_page = item_obj.records_per_page
        if target_event == "next":
            list_last_len = offset + records_per_page
            list_start_len = offset

            if len(list_data) >= records_per_page:
                data["list_data"] = list_data[list_start_len:list_last_len]
                data["curr_list"] = list_last_len
                if list_last_len >= len(list_data):
                    data["list_numbers"] = (
                        str(list_start_len)
                        + "-"
                        + str(len(list_data))
                        + "/"
                        + str(len(list_data))
                    )
                    data["is_previous"] = True
                    data["is_next"] = False
                else:
                    data["list_numbers"] = (
                        str(list_start_len)
                        + "-"
                        + str(list_last_len)
                        + "/"
                        + str(len(list_data))
                    )
                    data["is_next"] = True
                    data["is_previous"] = True

        else:
            if offset > records_per_page:
                list_last_len = offset - records_per_page
                list_start_len = list_last_len - records_per_page
                data["is_next"] = True
                if list_start_len < records_per_page:
                    data["is_previous"] = False
                else:
                    data["is_previous"] = True
            else:
                list_last_len = records_per_page
                list_start_len = 0
                data["is_next"] = True
                data["is_previous"] = False

            if len(list_data) > records_per_page:
                data["list_data"] = list_data[list_start_len:list_last_len]
                data["curr_list"] = list_last_len
                data["list_numbers"] = (
                    str(list_start_len)
                    + "-"
                    + str(list_last_len)
                    + "/"
                    + str(len(list_data))
                )
        data["show_edit_button"] = item_obj.show_record_edit_button
        data["pager"] = True
        data["list_length"] = len(list_data)
        return data

    def get_fav_filtrer_data(self, uid):
        fav_filters = []
        if len(self):
            for rec in self.fav_filter_ids:
                if rec.user_id and rec.user_id.id == uid:
                    fav_filters.append(
                        {
                            "id": rec.id,
                            "name": rec.name,
                            "filters_value": safe_eval(rec.filter_value, {})
                            if rec.filter_value
                            else [],
                            "is_active": rec.is_active,
                        }
                    )
        return fav_filters

    def get_sharable_link(self):
        if not self.security_token_bits:
            self.generate_security_token()
        link = (
            "/dashboard/"
            + str(self.id)
            + "/embed?security_token=%s" % self.security_token_bits
        )
        return link

    def generate_security_token(self):
        self.security_token_bits = uuid.uuid4().hex

    def get_dashboard_filters(self):
        filters = []
        if len(self.filter_ids):
            for rec in self.sudo().filter_ids:
                data = {
                    "filter_id": rec.id,
                    "filter_model_id": rec.model_id.id,
                    "filter_model_name": rec.model_id.name,
                    "target_field_id": rec.field_id.id,
                    "target_field_name": rec.field_id.field_description,
                    "target_field_tname": rec.field_id.name,
                    "target_field_model": rec.field_id.relation,
                }
                if rec.field_id.ttype in ["one2many", "many2many", "many2one"]:
                    data["field_type"] = "relational"
                else:
                    data["target_field_model"] = rec.model_id.model
                    data["field_type"] = "selection"
                filters.append(data)

        return filters

    def export_dashboard_action(self, dashboard_id):
        main_data = {}
        if type(dashboard_id) == int:
            dashboard_record = self.sudo().search([("id", "=", dashboard_id)])
        else:
            dashboard_record = self.sudo()
        for rec in dashboard_record:
            dashboard_data = []
            for dashboard_item_id in rec.dashboard_item_ids:
                dashboard_data.append(
                    {
                        "id": dashboard_item_id.id,
                        "name": dashboard_item_id.name,
                        "model": {
                            "name": dashboard_item_id.model_id.name,
                            "model": dashboard_item_id.model_id.model,
                        },
                        "item_title": dashboard_item_id.item_title,
                        "statistics_item_title": dashboard_item_id.statistics_item_title,
                        "view_data": dashboard_item_id.view_data,
                        "trend_display_style": dashboard_item_id.trend_display_style,
                        "trend_primary_color": dashboard_item_id.trend_primary_color,
                        "apply_background": dashboard_item_id.apply_background,
                        "action_id": dashboard_item_id.action_id.name,
                        "kpi_display_style": dashboard_item_id.kpi_display_style,
                        "kpi_primary_color": dashboard_item_id.kpi_primary_color,
                        "is_smooth_line": dashboard_item_id.is_smooth_line,
                        "is_area_style": True
                        if dashboard_item_id.is_area_style
                        else False,
                        "is_background": dashboard_item_id.is_background,
                        "horizontal_chart": dashboard_item_id.horizontal_chart,
                        "bar_stack": dashboard_item_id.bar_stack,
                        "is_polar": dashboard_item_id.is_polar,
                        "circular_chart": dashboard_item_id.circular_chart,
                        "doughnut_chart": dashboard_item_id.doughnut_chart,
                        "half_pie": dashboard_item_id.half_pie,
                        "list_view_style": dashboard_item_id.list_view_style,
                        "list_view_field_ids": dashboard_item_id.list_view_field_ids.mapped(
                            "name"
                        ),
                        # "list_view_field_ids" : {'model': dashboard_item_id.model_id.model, "field_name":dashboard_item_id},
                        "show_record_edit_button": dashboard_item_id.show_record_edit_button,
                        "records_per_page": dashboard_item_id.records_per_page,
                        "chart_measure_field_ids": dashboard_item_id.chart_measure_field_ids.mapped(
                            "name"
                        ),
                        "bar_line_field_id": dashboard_item_id.bar_line_field_id.name
                        if dashboard_item_id.bar_line_field_id
                        else False,
                        "is_bar_line": dashboard_item_id.is_bar_line,
                        "display_order": dashboard_item_id.display_order,
                        "chart_groupby_field": dashboard_item_id.chart_groupby_field.name
                        if dashboard_item_id.chart_groupby_field
                        else False,
                        "chart_sub_groupby_field": dashboard_item_id.chart_sub_groupby_field.name,
                        "chart_sort_by_field": dashboard_item_id.chart_sort_by_field.name
                        if dashboard_item_id.chart_sort_by_field
                        else False,
                        "chart_sort_by_order": dashboard_item_id.chart_sort_by_order,
                        "record_limit": dashboard_item_id.record_limit,
                        "dashboard_grid_config_id": dashboard_item_id.dashboard_grid_config_id.name
                        if dashboard_item_id.dashboard_grid_config_id
                        else False,
                        "chart_preview_bits": dashboard_item_id.chart_preview_bits,
                        "b_trend_field_id": dashboard_item_id.b_trend_field_id.name
                        if dashboard_item_id.b_trend_field_id
                        else False,
                        "b_measure_type": dashboard_item_id.b_measure_type,
                        "b_measure_field_id": dashboard_item_id.b_measure_field_id.name
                        if dashboard_item_id.b_measure_field_id
                        else False,
                        "b_show_val": dashboard_item_id.b_show_val,
                        # "chart_preview_data": dashboard_item_id.chart_preview_data,
                        "company_id": dashboard_item_id.company_id.name
                        if dashboard_item_id.company_id
                        else False,
                        "kpi_target": dashboard_item_id.kpi_target,
                        "model_name": dashboard_item_id.model_name,
                        "color_theme": dashboard_item_id.color_theme.name
                        if dashboard_item_id.color_theme
                        else False,
                        "query": dashboard_item_id.query,
                        "stats_value_by_qry": dashboard_item_id.stats_value_by_qry,
                        "x_axis": dashboard_item_id.x_axis,
                        "bar_line_measure": dashboard_item_id.bar_line_measure,
                        "y_axis": dashboard_item_id.y_axis,
                        "dashboard": dashboard_item_id.bits_dashboard_id.name,
                        "item_domain": dashboard_item_id.item_domain,
                        "is_limit_record": True
                        if dashboard_item_id.is_limit_record
                        else False,
                        "item_type": dashboard_item_id.item_type,
                        "is_query": True if dashboard_item_id.is_query else False,
                        "v_records_per_pag": dashboard_item_id.v_records_per_page,
                        "onclick_action": True
                        if dashboard_item_id.onclick_action
                        else False,
                        "statistics_with_trend": True
                        if dashboard_item_id.statistics_with_trend
                        else False,
                        "display_data_type": dashboard_item_id.display_data_type,
                        "statistics_field": dashboard_item_id.statistics_field.name,
                        "show_currency": True
                        if dashboard_item_id.show_currency
                        else False,
                        "media_option": dashboard_item_id.media_option,
                        "icon_bits": dashboard_item_id.icon_bits,
                        "display_style": dashboard_item_id.display_style,
                        "background_color": dashboard_item_id.background_color,
                        "font_color": dashboard_item_id.font_color,
                        "icon_color": dashboard_item_id.icon_color,
                        "is_border": True if dashboard_item_id.is_border else False,
                        "border_position": dashboard_item_id.border_position,
                        "border_color": dashboard_item_id.border_color,
                        "legend_position": dashboard_item_id.legend_position,
                        "show_legend": dashboard_item_id.show_legend,
                        "lable_position": dashboard_item_id.lable_position,
                        "show_lable": dashboard_item_id.show_lable,
                        "lable_format": dashboard_item_id.lable_format,
                        "stats_chart_y_by_qry": dashboard_item_id.stats_chart_y_by_qry,
                        "stats_chart_x_by_qry": dashboard_item_id.stats_chart_x_by_qry,
                        "icon_background":dashboard_item_id.icon_background if dashboard_item_id.icon_background else '#fff',
                        "embade_code":dashboard_item_id.embade_code if dashboard_item_id else '',
                    }
                )

            filter_data = []
            for filter_id in rec.filter_ids:
                filter_data.append(
                    {
                        "name": filter_id.name,
                        "model": {
                            "name": filter_id.model_id.name,
                            "model": filter_id.model_id.model,
                        },
                        "field_id": filter_id.field_id.name,
                        "active": True if filter_id.active else False,
                        "dashboard_id": filter_id.dashboard_id.id,
                    }
                )

            data = {
                "name": rec.name,
                "menu_name": rec.menu_name,
                "is_main_menu": rec.is_main_menu,
                "d_icon_bits": rec.d_icon_bits,
                "menu_sequence": rec.menu_sequence,
                "parent_menu": {
                    "name": rec.parent_menu_id.name,
                    "path": rec.parent_menu_id.complete_name,
                    "parent_id": rec.parent_menu_id.parent_id.name,
                },
                "dashboard_item_ids": dashboard_data,
                "default_time_frame": rec.default_time_frame,
                "default_color_theme": rec.default_color_theme.name,
                "default_view_mode": rec.default_view_mode,
                "active": True if rec.active else False,
                "grid_config_id": False,
                "grid_config": rec.grid_config,
                "time_frame": rec.time_frame,
                "company_id": rec.company_id.name,
                "start_date": str(rec.start_date) if rec.start_date else False,
                "end_date": str(rec.end_date) if rec.end_date else False,
                "filter_ids": filter_data,
                "group_ids": rec.group_ids.mapped("id"),
            }
            main_data.update({rec.name: data})
        json_data = json.dumps(main_data, indent=4)
        binary_data = base64.b64encode(json_data.encode("utf-8"))

        record = self.env["ir.attachment"].create(
            {
                "name": "dashboard.json",
                "type": "binary",
                "datas": binary_data,
                "public": True,
            }
        )
        return {
            "type": "ir.actions.act_url",
            "url": "web/content/?model=ir.attachment&id="
            + str(record.id)
            + "&filename_field=name&field=datas&download=true&name="
            + record.name,
            "target": "self",
        }

    def get_grid_config(self):
        if len(self):
            return self.sudo().grid_config

    def open_form_view(self):
        action = {
            "type": "ir.actions.client",
            "id": self.client_action_id.id,
            "tag": "bits_dashboard_action",
            "context": {
                "params": {
                    "dashboard_id": self.id,
                    "default_color_theme": self.default_color_theme.id,
                    "default_time_frame": self.default_time_frame,
                    "default_view_mode": self.default_view_mode,
                }
            },
        }

        return action
