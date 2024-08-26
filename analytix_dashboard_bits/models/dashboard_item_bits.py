from odoo import models, fields, api, _
import json
import datetime
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from odoo.tools.safe_eval import safe_eval
import base64
from odoo.exceptions import ValidationError
from odoo.addons.advanced_web_domain_widget.models.domain_prepare import prepare_domain_v2
# import pandas as pd
# from sqlalchemy import create_engine
from psycopg2 import ProgrammingError
import re
import ast
from odoo.tools import config
from odoo.tools import frozendict
# import numpy

axis_chart_type = ['bar', 'line', 'statistics']
radius_axis_chart_type = ['polar']

regex_field_agg = re.compile(r'(\w+)(?::(\w+)(?:\((\w+)\))?)?')


def convert_frozendict(data):
    if isinstance(data, dict):
        new_data = {}
        for key, value in data.items():
            # Convert frozendict key to string
            if isinstance(key, frozendict):
                key = str(dict(key))
            # Recursively convert frozendict values
            if isinstance(value, frozendict):
                value = dict(value)
            elif isinstance(value, dict):
                value = convert_frozendict(value)
            new_data[key] = value
        return new_data
    return data

def remove_space(string):
    ns = ""
    if string:
        for i in string:
            if not i.isspace():
                ns += i
    return ns


def human_format(num):
    magnitude = 0
    if not isinstance(num, int) and not isinstance(num, float):
        return num
    while abs(num) >= 1000:
        magnitude += 1
        num /= 1000.0
    if isinstance(num, int):
        return '%s %s' % (num, ['', 'K', 'M', 'G', 'T', 'P'][magnitude])
    else:
        return '%.2f%s' % (num, ['', 'K', 'M', 'G', 'T', 'P'][magnitude])


def get_percentage(current, previous):
    if current == previous:
        return 0
    try:
        return format(((previous - current) / previous) * 100, '.3f')
    except ZeroDivisionError:
        return 0


def serialize_datetime(obj):
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()


def get_common_domain(domain=None):
    if domain is None:
        domain = []
    common_domain = ("[('name', '!=', 'id'), ('store', '=', True), ('model_id', '=', model_id), "
                     "('ttype', 'not in', ['many2many', 'one2many', 'binary']),")

    if domain:
        common_domain += domain

    return common_domain + "]"


class DashboardItemBits(models.Model):
    _name = "dashboard.item.bits"
    _description = "For dashboard items."

    # BASIC Options
    name = fields.Char('Name', help="Name of the dashboard")
    default_time_frame = fields.Selection(string='Dashboard time frame', related="bits_dashboard_id.default_time_frame",
                                          help="Dashboard will load the data based on default time frame.")
    model_id = fields.Many2one('ir.model', string='Select Model', help="Select the model to generate analysis.")
    item_title = fields.Char('Item Title', compute='_compute_title', store=True, help="Item title.")
    # to remove
    statistics_item_title = fields.Char('Statistics Item Title', help="Statistics item title")
    item_type = fields.Selection([('statistics', 'Statistics'),
                                  ('kpi', 'KPI Progress'),
                                  ('list_view', 'List View'),
                                  ('line', 'Line Chart'),
                                  ('bar', 'Bar Chart'),
                                  ('pie', 'Pie Chart'),
                                  ('radar', 'Radar Chart'),
                                  ('funnel', 'Funnel Chart'),
                                  ('embade_iframe', 'Embade Iframe'),
                                  ('default_base_view', 'Default Base View')
                                  ], string="Dashboard Item",
                                 help="Select the item type to display on dashboard.")

    display_data_type = fields.Selection([('sum', 'Sum'), ('count', 'Count'), ('avg', 'Average')],
                                         string="Data Display Type", required=True, default='sum',
                                         help="Select data display type. calculation will show based on data display type.")

    # Custom view
    view_data = fields.Char("Dashboard action view data")

    # Statistics
    statistics_with_trend = fields.Boolean('With Trend Chart', help='Enable to make trend chart with statastics data.')
    statistics_field = fields.Many2one('ir.model.fields',
                                       domain=get_common_domain("('ttype', 'in', ['integer', 'float', 'monetary']),"),
                                       string="Statistics Field",
                                       help="Analysis data will calculate from selected field values.")

    display_style = fields.Selection(
        [('style_1', 'Style 1'), ('style_2', 'Style 2'), ('style_3', 'Style 3'), ('style_4', 'Style 4'),
         ('style_5', 'Style 5'), ('style_6', 'Style 6'), ('style_7', 'Style 7'), ('style_8', 'Style 8'),
         ('style_9', 'Style 9')], default='style_1', string="Statistics Display Style",
        help='Select the display style to display statistics on dashboard.')

    trend_display_style = fields.Selection([('style_1', 'Style 1'), ('style_2', 'Style 2'), ('style_3', 'Style 3')],
                                           default='style_1', string="Trend Display Style",
                                           help='Select trend chart style to display on dashboard.')
    trend_primary_color = fields.Char('Primary Color', help='Select trend chart primary color.')
    apply_background = fields.Boolean('Apply On Background', help='Enable to apply primary color on background.')

    is_border = fields.Boolean("Add Border", default=False, help='Enable to set border on statistics.')
    border_position = fields.Selection(
        [("left", "Left"), ("right", "Right"), ("top", "Top"), ("bottom", "Bottom")],
        default="left", string="Border Position", help='Select border position')
    border_color = fields.Char("Border Color", help='set border color')
    background_color = fields.Char("Background Color", help='Set background color')
    font_color = fields.Char("Font Color", help='Set font color')
    icon_color = fields.Char("Icon Color", help='Set icon color')
    media_option = fields.Selection(
        [("image_bits", "Image"), ("fontawesome_bits", "Font Awesome Icon")],
        default="fontawesome_bits", string="Media Option",
        help='Select media option. 1)Image :To set image as icon. 2) Font Awesome Icon :To set  ')
    icon_bits = fields.Char("Select Icon")
    icon_image = fields.Binary("Image Icon", help='Select the image to set on statistics item.')
    onclick_action = fields.Boolean("Click Action", help="Enable to set onclick action on statistics item.")
    action_id = fields.Many2one("ir.actions.act_window", domain="[('name','!=','Apps Store')]",
                                help="Select the action to perform action on clicking statistics item.")

    # kpi
    kpi_display_style = fields.Selection([('style_1', 'Style 1'), ('style_2', 'Style 2'), ('style_3', 'Style 3')],
                                         default='style_1', string="Display Style", help="Select KPI display style")
    kpi_primary_color = fields.Char('Primary Color', help="Select KPI primary color")

    # Line
    is_smooth_line = fields.Boolean('Set Smooth Line', help="Enable to make smooth line on chart")
    is_area_style = fields.Boolean('Set Line Area', help="Enable to set area on line.")

    # Bar
    is_background = fields.Boolean('Set Background', help="Enable to set background on chart.")
    horizontal_chart = fields.Boolean('Make Horizontal Chart', help="Enable to make horizontal chart.")
    bar_stack = fields.Boolean('Make Bar Stack Chart', help="Enable to make bar stack chart.")
    is_polar = fields.Boolean('Make Polar Chart', help="Enable to make polar chart")
    circular_chart = fields.Boolean('Make Circular Polar', help="Enable to make circular chart.")

    # Pie
    doughnut_chart = fields.Boolean('Make Doughnut Chart', help="Enable to make doughnut chart.")
    half_pie = fields.Boolean("Make Half Pie", help="Enable to make half-pie chart.")

    # List view
    list_view_style = fields.Selection(
        [('style_1', 'Style 1'), ('style_2', 'Style 2'), ('style_3', 'Style 3'), ('style_4', 'Style 4')],
        default='style_1', string="List View Style", help="Select listview style to show on dashboard.")

    list_view_field_ids = fields.Many2many('ir.model.fields', 'dashboard_item_id_field_id_rel', 'dashboard_item_id',
                                           'field_id', 'List View Fields', domain=get_common_domain(), copy=True,
                                           help="Select list view style to show on dashboard.")
    show_record_edit_button = fields.Boolean('Show Edit Button',
                                             help="Enable to show edit button on the list view records.")
    records_per_page = fields.Integer(compute="_compute_record_page",
                                      help="Enter the number to show records per page on list view.")
    v_records_per_page = fields.Selection([('10', '10'), ('20', '20'), ('30', '30'), ('40', '40'), ('50', '50')],
                                          string='Records Per Page', default='10',
                                          help="Select the records to show on list view.")
    chart_measure_field_ids = fields.Many2many('ir.model.fields', 'chart_measure_field_fields_id_rel',
                                               'chart_measure_field_id', 'field_id',
                                               domain=get_common_domain(
                                                   "('ttype', 'in', ['integer', 'float', 'monetary']),"),
                                               string="Measure", copy=True, help="Select field to measure Y axis data")

    bar_line_field_id = fields.Many2one('ir.model.fields', domain="[('id', 'in', chart_measure_field_ids)]",
                                        string="Bar/Line", help='Select fields to make line chart with bar chart.')
    is_bar_line = fields.Boolean("Make Bar/Line Chart", compute="_compute_is_bar_line",
                                 help="Enable to make bar/line chart.")

    display_order = fields.Selection(
        [('ascending', 'Ascending'), ('descending', 'Descending')], string="Data Display Order",
        help='Select order to show data.')

    chart_groupby_field = fields.Many2one('ir.model.fields', domain=get_common_domain(), string="Group By(X axis)",
                                          help="Select field to show data group by on chart.")
    chart_sub_groupby_field = fields.Many2one('ir.model.fields', domain=get_common_domain(), string="Sub Group By",
                                              help="Select field to show data sub-group by on chart.")
    chart_sort_by_field = fields.Many2one('ir.model.fields', domain=get_common_domain(), string="Sort By",
                                          help="Select field by which you want to sort the records.")
    chart_sort_by_order = fields.Selection([('ASC', 'Ascending'), ('DESC', 'Descending')], string="Sort Order",
                                           help="Select order by which you want to sort the records.")
    dashboard_grid_config_id = fields.Many2one('dashboard.gird.config', 'Grid Configuration')
    # hidden fields
    bits_dashboard_id = fields.Many2one('dashboard.bits', 'Dashboard', default=lambda self: self._context[
        'bits_dashboard_id'] if 'bits_dashboard_id' in self._context else False,
                                        help='Select dashboard in which you want to show this item.')

    # is_data_limit = fields.Boolean('dashboard')
    # records_limit = fields.Integer('Record Limit', default=0)

    # ------- Statistics view fields

    chart_preview_bits = fields.Char('Chart Preview')

    b_trend_field_id = fields.Many2one('ir.model.fields', string="Trend Field",
                                       domain=get_common_domain(
                                           "('model_id', '=', model_id), ('ttype', 'in', ['selection', 'many2one'])"),
                                       help="Select field to show data value in bottom of trend")
    b_measure_type = fields.Selection([('sum', 'Sum'), ('count', 'Count')], default='count', required=True,
                                      string="Trend Calc Type", help="Select calculation type perform to get data.")
    b_measure_field_id = fields.Many2one('ir.model.fields', domain=get_common_domain(
        "('ttype', 'in', ['integer', 'float', 'monetary']),"), string="Select Calc Field",
                                         help='Select the field by you want to calculate the data and show under the trend.')

    # b_show_val = fields.Char(string="Show vals", widget='custom_dropdown_dynamic')
    b_show_val = fields.Char(string='Select Field Value', help="Select trend field's value to show under the trend")

    chart_preview_data = fields.Char('Chart Preview Data', compute="_compute_chart_preview", store=True)
    company_id = fields.Many2one("res.company", related="bits_dashboard_id.company_id")

    show_currency = fields.Boolean("Display Currency")
    kpi_target = fields.Float("Set Target", help="enter target value to set target on specified model's value.")

    model_name = fields.Char(related="model_id.model", string="Select Model Name",
                             help="Select model for which you want to generate analysist.")
    item_domain = fields.Char(string="Data Filter", help="Define domain conditions to filter out data.")
    is_limit_record = fields.Boolean("Set Record Limit",
                                     help='By enabaling this, The entered limit will considered as you want to fetch entered limit data.')
    record_limit = fields.Integer("Records Limit",
                                  help="Defines the limit to retrieve the data. The entered limit will considered as you want to fetch entered limit data.")

    color_theme = fields.Many2one("dashboard.themes", string="Set Default Color Theme",
                                  related="bits_dashboard_id.default_color_theme")

    is_query = fields.Boolean(string="Fetch Records By Query", help="Enable to get records through the sql query.")
    query = fields.Text('Enter Query', help="The entered query will fetch the records from the database.")
    res_query_bits = fields.Char(compute='_compute_query_res', string="Query Result")
    x_axis = fields.Char("Group By(X axis)", help="Select group-by field to make group by of fetched records in chart.")
    y_axis = fields.Char("Measure(Y axis)", help="Select measure field to set measures in chart.")
    stats_value_by_qry = fields.Char("Statistics Value",
                                     help="Select the field of statistics value from you have searched in the query.")
    stats_chart_x_by_qry = fields.Char("Measure(Y axis)",
                                       help="Select group-by field to make group-by from fetched data in chart.")
    stats_chart_y_by_qry = fields.Char("Group By(X axis)",
                                       help="Select measer field to set measure from fetched data in chart.")
    bar_line_measure = fields.Char(string="Bar/line measure", help="Select fields to make line chart with bar chart.")
    lable_format = fields.Char("Label format", default="{value} {c}",
                               help="Enter the formate to show on measure(Y axis). Ex.{value}{c} here 'value' will show the comming value on axis and 'c' will show the currency if the field will monetory, Otherwise you can directely add monetory value($, INR, EUR, etc) after the value like {value} INR.")
    show_lable = fields.Boolean('Show lable', help="Enable to show the lable on the chart.")
    lable_position = fields.Selection(
        [('top', 'Top'), ('bottom', 'Bottom'), ('inner', 'Inner'), ('right', 'Right'), ('left', 'Left'),
         ('center', 'Center'), ('inside', 'Inside')], string='Label Position', default="inner",
        help="Select lable position to set lable on the chart.")
    show_legend = fields.Boolean('Show Groups', help="Enable to show groups of chart data in the chart.")
    legend_position = fields.Selection([('top', 'Top'), ('bottom', 'Bottom'), ('right', 'Right'), ('left', 'Left')],
                                       string='Groups Position', default="bottom",
                                       help="Select groups position to show groups on the chart")
    icon_background = fields.Char("Icon Background Color")
    embade_code = fields.Char("Embade Code",
                              help="Add embade iframe code(youtube, vimo, website, tutorials, etc) to load source.")

    @api.onchange('kpi_target')
    def _onchange_kpi_target(self):
        for rec in self:
            if rec.kpi_target and rec.kpi_target < 0:
                rec.kpi_target = abs(rec.kpi_target)

    @api.onchange('res_query_bits')
    def _onchange_query(self):
        for rec in self:
            rec.x_axis = False
            rec.y_axis = False

    @api.depends('v_records_per_page')
    def _compute_record_page(self):
        for rec in self:
            if rec.v_records_per_page:
                rec.records_per_page = int(rec.v_records_per_page)
            else:
                rec.records_per_page = 10

    @api.depends('chart_measure_field_ids')
    def _compute_is_bar_line(self):
        for rec in self.sudo():
            if rec.item_type in ['line', 'bar'] and len(rec.chart_measure_field_ids) > 1:
                f = True
            else:
                f = False

            rec.is_bar_line = f

    @api.depends('item_type', 'chart_measure_field_ids', 'display_data_type', 'chart_groupby_field',
                 'list_view_style', 'list_view_field_ids', 'doughnut_chart', 'half_pie', 'circular_chart', 'is_polar',
                 'horizontal_chart', 'is_background', 'is_area_style', 'is_smooth_line', 'icon_bits', 'icon_image',
                 'icon_color', 'font_color', 'background_color', 'border_color', 'display_style', 'statistics_field',
                 'statistics_with_trend', 'border_position', 'is_border', 'trend_display_style', 'lable_format',
                 'trend_primary_color', 'kpi_display_style', 'apply_background', 'bar_line_field_id',
                 'query', 'is_query', 'x_axis', 'y_axis', 'statistics_item_title', 'kpi_target', 'bar_line_measure',
                 'item_domain', 'b_show_val', 'display_order', 'records_per_page', 'bar_stack', 'stats_value_by_qry',
                 'kpi_primary_color', 'chart_sub_groupby_field', 'stats_chart_x_by_qry', 'stats_chart_y_by_qry',
                 'is_limit_record', 'record_limit', 'b_measure_type', 'b_measure_field_id', 'show_currency',
                 'show_lable', 'icon_background', "embade_code",
                 'lable_position', 'show_legend', 'legend_position')
    def _compute_chart_preview(self):
        if self._context.get('ignore_read'):
            self.chart_preview_data = False
        else:
            for rec in self.sudo():
                chart_preview_data = False
                item_dict = {}

                if rec.item_type and rec.is_query or rec.model_id:
                    # data = rec.sudo().with_context(limit=True).prepare_item_data()
                    data = rec.sudo().prepare_item_data()
                    if data:
                        item_dict.update(data)
                        item_dict = convert_frozendict(item_dict)
                        chart_preview_data = json.dumps(item_dict, default=str)

                rec.chart_preview_data = chart_preview_data

    @api.model
    def prepare_items_data(self, item_ids):
        items_data = []
        for item_id in item_ids:
            item = self.sudo().browse(item_id)
            items_data.append({item.id: item.sudo().prepare_item_data()})
        return items_data

    def get_item_domain(self):
        domain = self.bits_dashboard_id.prepare_date_domain()

        if self.item_domain:
            new_domain = []
            for domm in safe_eval(self.item_domain):
                if "date_filter" in domm:
                    date_domain = prepare_domain_v2(domm)
                    for dom in date_domain:
                        new_domain.append(dom)
                elif len(domm) and any(field in domm[0].split('.') for field in ['user_id', 'user_ids']):
                    if domm[1] in ['in', 'not in'] and 0 in domm[2]:
                        user_id = self.env.user.sudo().id
                        domm[2].remove(0)
                        domm[2].append(user_id)
                    new_domain.append(domm)
                else:
                    new_domain.append(domm)
            domain += new_domain
            # domain += safe_eval(self.item_domain)

        filter_obj = self.env['dashboard.filter.bits']
        ctx_filter = self._context.get('filters')
        if ctx_filter is not None:
            for rec in ctx_filter:
                filter_id = filter_obj.sudo().browse(rec.get('fid'))
                if filter_id.model_id.model == self.sudo().model_id.model:
                    x = safe_eval(rec.get('filter_domain'))
                    if rec.get('apply_filter_rec_ids', []):
                        x = list(x[0])
                        x[2] = rec.get('apply_filter_rec_ids')
                        x = [x]
                    domain += x

        return domain

    def get_item_past_domain(self):
        domain_2 = self.bits_dashboard_id.with_context(previous_data=True).prepare_date_domain()

        if self.item_domain:
            new_domain = []
            for domm in safe_eval(self.item_domain):
                if "date_filter" in domm:
                    date_domain = prepare_domain_v2(domm)
                    for dom in date_domain:
                        new_domain.append(dom)
                elif len(domm) and any(field in domm[0].split('.') for field in ['user_id', 'user_ids']):
                    if domm[1] in ['in', 'not in'] and 0 in domm[2]:
                        user_id = self.env.user.sudo().id
                        domm[2].remove(0)
                        domm[2].append(user_id)
                    new_domain.append(domm)
                else:
                    new_domain.append(domm)
            domain_2 += new_domain
        return domain_2

    def prepare_item_data(self):
        item_dict = {}
        theme_id = self._context.get('color_theme')
        color_pallate = []
        if theme_id:
            color_pallate = self.color_theme.browse(theme_id).get_color_palette()
        else:
            color_pallate = self.color_theme.get_color_palette()

        if self.view_data:
            data = json.loads(self.view_data)
            data['context_to_save'] = str(data['context_to_save'])
            data['domain'] = str(data['domain'])
            data['id'] = self.id

            item_dict['display_type'] = 'default_base_view'
            item_dict['action'] = data

            return item_dict

        read = self.sudo()._origin.with_context(ignore_read=True).read()
        if not len(read):
            read = [{
                'name': self.sudo().name,
                'item_title': self.sudo().item_title,
                'item_type': self.sudo().item_type,
                'statistics_with_trend': self.sudo().statistics_with_trend,
                'display_style': self.sudo().display_style,
                'trend_display_style': self.sudo().trend_display_style,
                'kpi_display_style': self.sudo().kpi_display_style,
                'list_view_style': self.sudo().list_view_style,
            }]
        item_dict = {'item_data': read and read[0] or read, 'display_type': self.item_type, 'title': self.item_title}

        if self.item_type == 'statistics':
            item_dict.update(self.prepare_statistics())

        elif self.item_type == 'list_view':
            item_dict.update({
                'display_type': self.item_type,
                'show_edit_button': self.show_record_edit_button,
                'list_view_data': convert_frozendict(self.prepare_list_view_data()),
                'primary_color': color_pallate[0]
            })
            if item_dict['item_data']:
                item_dict['item_data'].update({
                    'list_view_style': self.list_view_style,
                    'name': self.name,
                })

        elif self.item_type == 'kpi':
            item_dict.update(self.prepare_kpi())

        else:
            # ch-201123
            if self.is_query or self.sudo().chart_groupby_field and self.display_data_type:
                item_dict.update(self.get_item_chart(item_dict, self.get_item_domain()))

        return item_dict

    @api.onchange('display_data_type')
    def onchange_display_data_type(self):
        for rec in self.sudo():
            rec.statistics_field = False

    @api.depends('name')
    def _compute_title(self):
        for rec in self:
            rec.item_title = rec.name
            rec.statistics_item_title = rec.name

    @api.onchange("query", "y_axis")
    def onchange_query_axis(self):
        for rec in self:
            if not rec.query and not rec.y_axis:
                rec.bar_line_measure = ''

    @api.onchange("b_trend_field_id")
    def onchange_query_axis(self):
        for rec in self:
            rec.b_show_val = ''

    @api.onchange('model_id')
    def onchange_model_id(self):
        for rec in self.sudo():
            rec.chart_measure_field_ids = False
            rec.chart_groupby_field = False
            rec.chart_sort_by_field = False
            rec.list_view_field_ids = False
            rec.statistics_field = False
            rec.show_currency = False
            rec.b_measure_field_id = False
            rec.b_trend_field_id = False
            rec.item_domain = ''

    @api.onchange('item_type')
    def onchange_item_type(self):
        for rec in self.sudo():
            rec._compute_is_bar_line()
            rec.statistics_with_trend = False
            rec.statistics_field = False
            rec.is_smooth_line = False
            rec.is_area_style = False
            rec.circular_chart = False
            rec.is_polar = False
            rec.horizontal_chart = False
            rec.is_background = False
            rec.doughnut_chart = False
            rec.half_pie = False
            rec.show_currency = False

    @api.model_create_multi
    def create(self, vals_list):
        records = super(DashboardItemBits, self).create(vals_list)
        for record in records:
            grid = {}
            if record.bits_dashboard_id.grid_config:
                grid = json.loads(record.bits_dashboard_id.grid_config)

            grid = record.get_grid_config(grid)
            # grid['item_'+str(record.id)]['autoPosition'] = True
            # rendering RuntimeError
            record.bits_dashboard_id.grid_config = json.dumps(grid)
            # notify dashboard after new record is created
            online_partner = self.env['res.users'].sudo().search([]).filtered(
                lambda x: x.im_status in ['leave_online', 'online']).mapped(
                "partner_id").ids
            updates = {'dashboard_ids': [record.bits_dashboard_id.id], 'item_id': record.id}
            notification = [[(self._cr.dbname, 'res.partner', partner_id), 'ditem_create_notify',
                             {'type': 'NotifyUpdates', 'updates': updates}] for partner_id in online_partner]
            self.env['bus.bus']._sendmany(notification)
        return records

    def write(self, vals):
        res = super(DashboardItemBits, self).write(vals)
        if any(element in vals.keys() for element in ['item_type', 'kpi_display_style', 'statistics_with_trend']):
            for rec in self:
                grid = {}
                if rec.bits_dashboard_id.grid_config:
                    grid = json.loads(rec.bits_dashboard_id.grid_config)

                grid = rec.get_grid_config(grid)

                # rendering RuntimeError
                rec._origin.bits_dashboard_id.grid_config = json.dumps(grid)
        return res

    def get_grid_config(self, grid):
        last_config = {}
        if grid:
            if not grid.get('item_'+str(self.id)):
                last_config = {'x': 0,'y':0}
            else:
                last_config = grid['item_'+str(self.id)]
        else:
            return {}

        if self.item_type == 'statistics':
            if self.statistics_with_trend:
                if self.trend_display_style == "style_3":
                    grid['item_'+str(self.id)] = {
                        "id": self.id,
                        "x": last_config.get('x'), "y": last_config.get('y'), "w": 2, "h": 2, "minH": 3, "maxH": 3,
                        "minW": 2, "maxW": 6,
                    }
                else:
                    grid['item_'+str(self.id)] = {
                        "id": self.id,
                        "x": last_config.get('x'), "y": last_config.get('y'), "w": 3, "h": 3, "minH": 3, "maxH": 3,
                        "minW": 2, "maxW": 6,
                    }
            else:
                if self.display_style == "style_5":
                    grid['item_'+str(self.id)] = {
                        "id": self.id,
                        "x": last_config.get('x'), "y": last_config.get('y'), "w": 3, "h": 3, "minH": 2, "maxH": 4,
                        "minW": 2, "maxW": 3,
                    }
                else:
                    grid['item_'+str(self.id)] = {
                        "id": self.id,
                        "x": last_config.get('x'), "y": last_config.get('y'), "w": 3, "h": 2, "minH": 2, "maxH": 3,
                        "minW": 2, "maxW": 3,
                    }

        elif self.item_type in ["line", "bar"]:
            grid['item_'+str(self.id)] = {
                "id": self.id,
                "x": last_config.get('x'), "y": last_config.get('y'), "w": 5, "h": 6, "minH": 3, "maxH": 10, "minW": 3,
                "maxW": 12,
            }
        elif self.item_type == "kpi":
            if self.kpi_display_style in ["style_1", "style_3"]:
                grid['item_'+str(self.id)] = {
                    "id": self.id,
                    "x": last_config.get('x'), "y": last_config.get('y'), "w": 3, "h": 2, "minH": 2, "maxH": 2,
                    "minW": 2, "maxW": 6
                }
            elif self.kpi_display_style == "style_2":
                grid['item_'+str(self.id)] = {
                    "id": self.id,
                    "x": last_config.get('x'), "y": last_config.get('y'), "w": 2, "h": 3, "minH": 3, "maxH": 5,
                    "minW": 2, "maxW": 5
                }

        elif self.item_type == "list_view":
            grid['item_'+str(self.id)] = {
                "id": self.id,
                "x": last_config.get('x'), "y": last_config.get('y'), "w": 5, "h": 6, "minH": 3, "maxH": 8, "minW": 3,
                "maxW": 12,
            }

        elif self.item_type == "funnel":
            grid['item_'+str(self.id)] = {
                "id": self.id,
                "x": last_config.get('x'), "y": last_config.get('y'), "w": 3, "h": 4, "minH": 3, "maxH": 12, "minW": 2,
                "maxW": 6,
            }

        elif self.item_type == "default_base_view":
            grid['item_'+str(self.id)] = {
                "id": self.id,
                "x": last_config.get('x'), "y": last_config.get('y'), "w": 6, "h": 4, "minH": 3, "maxH": 24, "minW": 3,
                "maxW": 12,
            }
        else:
            grid['item_'+str(self.id)] = {
                "id": self.id,
                "x": last_config.get('x'), "y": last_config.get('y'), "w": 4, "h": 4, "minH": 3, "maxH": 8, "minW": 3,
                "maxW": 12,
            }

        return grid

    @api.model
    def copy_dashboard_item_bits(self, item_id):
        selected_dashboard_id = self.env.context.get('selected_dashboard_id')
        new_item_obj = False
        if item_id and selected_dashboard_id:
            new_item_obj = self.browse(item_id).copy({'bits_dashboard_id': selected_dashboard_id})
        return new_item_obj.id

    @api.model
    def move_dashboard_item_bits(self, item_id):
        selected_dashboard_id = self.env.context.get('selected_dashboard_id')
        new_item_obj = False
        if item_id and selected_dashboard_id:
            item_obj = self.browse(item_id)
            new_item_obj = item_obj.copy({'bits_dashboard_id': selected_dashboard_id})
            item_obj.unlink()
        return new_item_obj.id

    @api.model
    def unlink_item_bits(self, item_id):
        # selected_dashboard_id = self.env.context.get('selected_dashboard_id')
        item_obj = False
        if item_id:
            item_obj = self.sudo().browse(item_id).unlink()
            self.env.cr.commit()
        return item_obj

    @api.depends('query')
    def _compute_query_res(self):
        for record in self:
            if record.is_query and record.query:
                query_str = record.query
                new_env = self.pool.cursor()
                try:
                    new_env.execute("with c_query as (" + query_str + ")" +
                                    " select * from c_query limit %(limit)s",
                                    {'limit': 5})

                    fields = []
                    records = new_env.dictfetchall()
                    if records:
                        for field in new_env.description:
                            f_dict = {'name': field.name}
                            if type(records[0][field.name]).__name__ == 'float' or type(
                                    records[0][field.name]).__name__ == 'int':
                                f_dict['type'] = 'numeric'
                            else:
                                f_dict['type'] = 'string'
                            fields.append(f_dict)
                    elif record.item_type == "list_view":
                        for field in env_fetch.description:
                            f_dict = {'name': field.name, 'type': 'numeric'}
                            fields.append(f_dict)

                except ProgrammingError as e:
                    if e.args[0] == 'no results to fetch':
                        raise ValidationError(_("You can only read the Data from Database"))
                    else:
                        raise ValidationError(_(e))
                except Exception as e:
                    if type(e).__name__ == 'KeyError':
                        raise ValidationError(_(
                            'Wrong date variables, Please use ks_start_date and ks_end_date in custom query'))
                    raise ValidationError(_(e))
                finally:
                    new_env.close()

                for res in records:
                    for key in res:
                        if type(res[key]).__name__ == 'datetime':
                            res[key] = res[key].strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                        elif type(res[key]).__name__ == 'date':
                            res[key] = res[key].strftime(DEFAULT_SERVER_DATE_FORMAT)
                record.res_query_bits = json.dumps({'fields': fields, 'records': records})

            else:
                record.res_query_bits = ''

    def _get_chart_data(self, domain=None):
        self.ensure_one()

        if domain is None:
            domain = []

        chart_measure_field = []
        chart_measure_field_ids = []
        chart_measure_field_with_type = []

        if self.display_data_type == "count":
            if not self.sudo().chart_sort_by_field:
                chart_measure_field_with_type.append('count:count(id)')
            elif self.sudo().chart_sort_by_field:
                if not self.sudo().chart_sort_by_field.ttype == "datetime":
                    chart_measure_field_with_type.append(self.sudo().chart_sort_by_field.name + ':' + 'sum')
                else:
                    chart_measure_field_with_type.append(self.sudo().chart_sort_by_field.name)

        else:

            for res in self.sudo().chart_measure_field_ids:
                chart_measure_field.append(res.name)
                chart_measure_field_ids.append(res.id)
                chart_measure_field_with_type.append(res.name + ':sum')

        chart_group_by_field = self.sudo().chart_groupby_field.name
        chart_domain = domain
        # chart_domain = self.convert_into_proper_domain(rec.domain, rec, domain)

        orderby = self.sudo().chart_sort_by_field.name if self.sudo().chart_sort_by_field else "id"
        if self.chart_sort_by_order:
            orderby = orderby + " " + self.chart_sort_by_order

        if self._context.get('limit'):
            limit = 100
        else:
            limit = self.record_limit if self.is_limit_record and self.record_limit > 0 else 5000

        try:
            chart_record = self.env[self.sudo().model_id.model].sudo().read_group(chart_domain,
                                                                                  list(
                                                                                      set(chart_measure_field_with_type + [
                                                                                          chart_group_by_field])),
                                                                                  chart_group_by_field,
                                                                                  orderby=orderby,
                                                                                  limit=limit,
                                                                                  lazy=False)
        except Exception:
            chart_record = {}

        labels = []
        datasets = {}
        max_lst = []
        for line in chart_record:
            label = line[chart_group_by_field]
            labels.append(str(label[1]) if isinstance(label, tuple) else label)

        if self.display_data_type == "count":
            if not self.sudo().chart_sort_by_field:
                temp = []
                for line in chart_record:
                    temp.append(line['count'])
                datasets.update({'count': temp})

        else:

            for field in self.sudo().chart_measure_field_ids:
                temp = []
                for line in chart_record:
                    temp.append(line[field.name])

                if temp:
                    max_lst.append(max(temp))

                datasets.update({field.name: temp})

        return {
            'labels': labels,
            'datasets': datasets,
            'max_lst': max_lst
        }

    def prepare_query(self):
        func = self.display_data_type
        domain = self.get_item_domain()

        obj = self.env[self.sudo().model_id.model].sudo()
        if self.is_limit_record and self.record_limit > 0:
            domain = [('id', 'in', obj.search(domain, limit=self.record_limit).ids)]
        else:
            res_ids = obj.search(domain).ids
            if res_ids and len(res_ids) == 1:
                domain = [('id', '=', res_ids[0])]
            else:
                domain = [('id', 'in', res_ids)]

        query = obj._where_calc(domain)

        fields = self.sudo().chart_measure_field_ids.mapped('name')
        group_by = self.sudo().chart_groupby_field.mapped('name') + self.sudo().chart_sub_groupby_field.mapped('name')
        annotated_group_by = [obj._read_group_process_groupby(gb, query) for gb in group_by]
        order = ','.join([g for g in group_by])
        group_by_fields = [g['field'] for g in annotated_group_by]

        aggregated_fields = []

        fnames = []  # list of fields to flush
        if func == 'count':
            select_terms = f"COUNT({obj._table}.id) AS count,"

        else:
            select_terms = ""
            for fspec in fields:
                match = regex_field_agg.match(fspec)
                name, func_2, fname = match.groups()
                fname = fname or name

                fnames.append(fname)
                if fname in group_by_fields:
                    continue

                aggregated_fields.append(name)
                expr = obj._field_to_sql(obj._table, fname, query)
                expr = self.env.cr.mogrify(expr).decode()
                x = expr.replace('"', '')
                select_terms += f"{func}({x}) AS {name},"

        for gb in annotated_group_by:
            x = gb['qualified_field'].replace('"', '')
            select_terms += f"{x} AS {gb['groupby']}, "

        select_terms = select_terms[:-2]
        obj._flush_search(domain, fields=fnames + group_by_fields)

        group_by_terms, orderby_terms = obj.with_context(skip_m2o=True)._read_group_prepare(order, aggregated_fields,
                                                                                            annotated_group_by, query)
        from_clause, where_clause, where_clause_params = query.get_sql()

        from_clause = from_clause.replace('"', '')
        where_clause = where_clause.replace('"', '')
        lst = []
        for x in group_by_terms:
            lst.append(x.replace('"', ''))

        group_by_terms = lst

        for i in where_clause_params:
            if not isinstance(i, tuple) and not isinstance(i, list) and not isinstance(i, dict) and not isinstance(i,
                                                                                                                   bool) and not isinstance(
                i, int) and not i.isdigit() and isinstance(i, str):
                where_clause = where_clause.replace('%s', "'" + i + "'", 1)
            else:
                where_clause = where_clause.replace('%s', str(i), 1)

        prefix_terms = lambda prefix, terms: (prefix + " " + ",".join(terms)) if terms else ''
        prefix_term = lambda prefix, term: ('%s %s' % (prefix, term)) if term else ''

        query = """
            SELECT %(select)s
            FROM %(from)s
            %(where)s
            %(group_by)s
            %(orderby)s
        """ % {
            'select': select_terms,
            'from': from_clause,
            'where': prefix_term('WHERE', where_clause),
            'group_by': prefix_terms('GROUP BY', group_by_terms),
            'orderby': prefix_terms('ORDER BY', group_by_terms),
        }

        return query

    def get_new_value(self, field_x, old_val):
        new_val = {}
        if field_x.ttype in ['many2one'] and field_x.relation:
            obj = self.env[field_x.relation].sudo()

            for i in old_val:
                if isinstance(i, int):
                    rec = obj.browse(i)
                    if hasattr(rec, "name"):
                        field = getattr(rec, "name")
                    else:
                        field = rec.display_name
                    new_val.update({i: field})

        elif field_x.ttype in ['selection'] and field_x.selection:
            new_val = dict(ast.literal_eval(field_x.selection))

        return new_val

    def update_value(self, df):
        try:
            df = df.fillna(0)

            old_val = []
            gb_name = self.sudo().chart_groupby_field
            if gb_name:
                old_val = list(set(df[gb_name.name]))
            if old_val:
                old_val = [int(i) if isinstance(i, float) else i for i in old_val]
            new_val = self.get_new_value(gb_name, old_val)

            if new_val:
                df[gb_name.name] = df[gb_name.name].replace(new_val)

            if self.sudo().chart_sub_groupby_field:
                gb_name = self.sudo().chart_sub_groupby_field
                old_val = list(set(df[gb_name.name]))
                new_val = self.get_new_value(gb_name, old_val)
                if new_val:
                    df[gb_name.name] = df[gb_name.name].replace(new_val)

        except Exception as e:
            print(e)
        return df

    def get_data_in_pandas(self):
        if self.is_query:
            query = self.query
        else:
            query = self.prepare_query()

        if query:
            try:
                self._cr.execute(query)
                return self._cr.dictfetchall()
                # db_host = config['db_host']
                # db_port = config['db_port']
                # db_user = config['db_user']
                # db_password = config['db_password']
                # db_name = self._cr.dbname
                #
                # engine = create_engine(f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}")
                # df = []
                # with engine.connect() as conn:
                #     df = pd.read_sql_query(query, con=conn.connection)
                #     # df = pd.read_sql_query(query, engine)
                #
                #     df = df.loc[:, ~df.columns.duplicated()].copy()
                #     df = df.fillna(0)
                #
                #     if not self.is_query:
                #         df = self.update_value(df)
                #
                #     for rec in df.keys().tolist():
                #         if len(df.get(rec)) > 0 and isinstance(df.get(rec)[0], dict):
                #             for index, val in enumerate(df.get(rec)):
                #                 if isinstance(val, dict):
                #                     for v in val.values():
                #                         df.loc[index, rec] = v
                #                         break

                # return df

            except Exception as e:
                print(e)
                return []
        else:
            return []

    def prepare_chart(self, data):
        series = []
        labels = []
        mex = 0
        theme_id = self._context.get('color_theme')
        if theme_id:
            color_palate = self.color_theme.browse(theme_id).get_color_palette()
        else:
            color_palate = self.color_theme.get_color_palette()

        lable_format = self.lable_format
        if lable_format:
            currency_id = self.env.company.currency_id
            lable_format = lable_format.replace("{c}", currency_id.symbol) if currency_id.symbol else lable_format

        if self.is_query:
            fields = list(json.loads(self.y_axis).keys()) if self.y_axis else False
            group_by = self.x_axis
            sub_group_by = False

        else:
            if self.display_data_type == 'count':
                fields = ['count']
            else:
                fields = self.sudo().chart_measure_field_ids.mapped('name')

            group_by = self.sudo().chart_groupby_field.name
            sub_group_by = self.sudo().chart_sub_groupby_field.name

        if not self.is_query and self.model_id and self.sudo().chart_groupby_field.ttype in ['many2one']:
            mod_obj = self.env[self.sudo().chart_groupby_field.relation]
            for i in data:
                if isinstance(i, dict) and self.sudo().chart_groupby_field.name in i:
                    i[self.sudo().chart_groupby_field.name] = mod_obj.browse(
                        i[self.sudo().chart_groupby_field.name]).display_name

        if fields and group_by:
            if self.item_type in ['line', 'bar'] or self.statistics_with_trend:
                bar_line_field_ids = self.sudo().bar_line_field_id.mapped('name')
                labels = [i[group_by] for i in data]
                # if group_by == 'product_name':
                    # labels = [i[group_by].get('en_US') for i in data]

                uniq_sub_group_by = []
                if sub_group_by:
                    uniq_sub_group_by = list(set([i[sub_group_by] for i in data]))

                if uniq_sub_group_by:
                    for f in fields:
                        for rec in uniq_sub_group_by:
                            x = list(filter(lambda v: v[sub_group_by] == rec, data))
                            lst = []
                            for sgb in labels:
                                g_res = list(filter(lambda v: v[group_by] == sgb, x))
                                if g_res:
                                    g_res = round(sum(list(map(lambda g: g[f], g_res))), 2)
                                    if g_res and g_res > mex:
                                        mex = g_res
                                    lst.append(g_res)
                                else:
                                    lst.append(0)

                            if self.item_type == 'line' or self.statistics_with_trend:
                                item_type = 'line' if f not in bar_line_field_ids else 'bar'
                                if self.is_query and self.bar_line_measure and f == self.bar_line_measure:
                                    item_type = 'bar'
                            else:
                                item_type = 'bar' if f not in bar_line_field_ids else 'line'
                                if self.is_query and f == self.bar_line_measure:
                                    item_type = 'line'

                            temp = {
                                'name': f.replace('_', ' ').title() + " " + str(rec),
                                'type': item_type,
                                'label': {
                                    'show': True if not self.statistics_with_trend and self.item_type in ['bar',
                                                                                                          'line'] and self.show_lable and self.lable_position else False,
                                    'position': self.lable_position,
                                },
                                'emphasis': {
                                    'focus': 'series'
                                },
                                'data': lst
                            }
                            if self.bar_line_measure:
                                temp['label'].update({
                                    'show': False
                                })

                            if self.item_type == 'bar' and not self.bar_line_measure:
                                temp['label'].update({'rotate': 90 if not self.horizontal_chart else 0})

                            if self.bar_stack:
                                temp.update({'stack': f})

                            if self.is_smooth_line:
                                temp.update({'smooth': True})

                            if self.is_area_style:
                                temp.update({'areaStyle': {}})

                            if self.is_polar:
                                temp.update({
                                    'coordinateSystem': 'polar',
                                    'label': {
                                        'show': True,
                                        'position': 'middle',
                                        'formatter': '{c}'
                                    }
                                })

                            if self.is_background:
                                temp.update({'showBackground': True})

                            series.append(temp)

                else:
                    for f in fields:
                        # lst_data = [round(i[f], 2) for i in data]
                        lst_data = []
                        for i in data:
                            if i[f]:
                                lst_data.append(round(i[f], 2))
                        # lst_data = list(data[f].values.round(2))

                        if lst_data and max(lst_data) > mex:
                            mex = max(lst_data)

                        if self.item_type == 'line' or self.statistics_with_trend:
                            item_type = 'line' if f not in bar_line_field_ids else 'bar'
                            if self.is_query and self.bar_line_measure and f == self.bar_line_measure:
                                item_type = 'bar'
                        else:
                            item_type = 'bar' if f not in bar_line_field_ids else 'line'
                            if self.is_query and self.bar_line_measure and f == self.bar_line_measure:
                                item_type = 'line'

                        temp = {
                            'name': f.replace('_', ' ').title(),
                            'type': item_type,
                            'label': {
                                'show': True if not self.statistics_with_trend and self.item_type in ['bar',
                                                                                                      'line'] and self.show_lable and self.lable_position else False,
                                'position': self.lable_position,
                            },
                            'emphasis': {
                                'focus': 'series'
                            },
                            'data': lst_data
                        }

                        if self.bar_stack:
                            temp.update({'stack': 'total'})

                        if self.is_smooth_line:
                            temp.update({'smooth': True})

                        if self.is_area_style:
                            temp.update({'areaStyle': {}})

                        if self.is_polar:
                            temp.update({
                                'coordinateSystem': 'polar',
                            })

                        if self.is_background:
                            temp.update({'showBackground': True})

                        series.append(temp)

            elif self.item_type in ['pie']:
                c = 80
                f_len = len(fields)
                co = 1
                for f in fields:
                    s = 0
                    t = []

                    for d in data:
                        s += d[f]
                        if d[f] and mex < d[f]:
                            mex = d[f]
                        t.append({'value': d[f], 'name': d[group_by]})

                    # for d in data.iterrows():
                    #     d = dict(d[1])
                    #     if not d[f]:
                    #         continue
                    #     s += d[f]
                    #     if d[f] and mex < d[f]:
                    #         mex = d[f]
                    #     t.append({'value': d[f], 'name': d[group_by]})

                    if self.half_pie:
                        t.append({
                            'value': s,
                            'itemStyle': {
                                'color': 'none',
                                'decal': {
                                    'symbol': 'none'
                                },
                                'borderWidth': 0,
                            },
                            'label': {
                                'show': False,
                            },
                        })

                    temp = {
                        'name': f.replace('_', ' ').title(),
                        'type': self.item_type,
                        'startAngle': 180,
                        'label': {
                            'show': True if self.show_lable and self.lable_position else False,
                            'formatter': '{b}',
                            'position': self.lable_position,
                            'overflow': 'break',
                            'fontSize': 12,
                            'backgroundColor': '#fff',
                            'color': '#000',
                            'borderRadius': 4,
                            'padding': 4
                        },
                        'labelLine': {
                            'length': 10
                        },
                        'data': t
                    }
                    if self.show_legend and self.legend_position == 'top':
                        temp.update({
                            'top': '20%'
                        })
                    elif self.show_legend and self.legend_position == 'bottom':
                        temp.update({
                            'bottom': '15%'
                        })
                    elif self.show_legend and self.legend_position == 'left':
                        temp.update({
                            'left': '20%'
                        })
                    elif self.show_legend and self.legend_position == 'right':
                        temp.update({
                            'right': '20%'
                        })

                    if self.doughnut_chart:
                        temp.update({'itemStyle': {
                            'borderRadius': 10,
                            'borderColor': '#fff',
                            'borderWidth': 2
                        }})
                        doughnut_chart = [str(c - 20 + 3) + '%', str(c) + '%']
                    else:
                        if co == f_len:
                            doughnut_chart = ['0%', str(c) + '%']
                        else:
                            doughnut_chart = [str(c - 20 + 3) + '%', str(c) + '%']
                            co += 1

                    temp.update({'radius': doughnut_chart})
                    if self.half_pie:
                        temp.update({'center': ['50%', '70%']})

                    if c > 20:
                        c -= 20

                    series.append(temp)

            elif self.item_type in ['radar']:
                temp = {}
                maax = 0

                for d in data:
                    for f in fields:
                        t = temp.get(f, [])
                        t.append(d[f])
                        temp.update({f: t})

                        if d[f] > maax:
                            maax = d[f]

                    t_group_by = d[group_by]

                    if not isinstance(t_group_by, str):
                        t_group_by = str(t_group_by)

                    t_sub_group_by = sub_group_by

                    if t_sub_group_by and d.get(t_sub_group_by, False):
                        t_sub_group_by = d[t_sub_group_by]
                        if not isinstance(t_sub_group_by, str):
                            t_sub_group_by = str(t_sub_group_by)

                        t_group_by += " " + t_sub_group_by

                    labels.append({'name': t_group_by, 'max': maax})

                for label in labels:
                    label.update({'max': maax})

                da = []
                for key, value in temp.items():
                    da.append({'name': key, 'value': value})

                series.append({
                    'name': self.name,
                    'type': 'radar',
                    'data': da
                })

            elif self.item_type in ['funnel']:
                for f in fields:
                    t = []
                    for d in data:

                        t_group_by = group_by
                        t_group_by = d[t_group_by]

                        if not isinstance(t_group_by, str):
                            t_group_by = str(t_group_by)

                        t_sub_group_by = sub_group_by

                        if t_sub_group_by and d.get(t_sub_group_by, False):
                            t_sub_group_by = d[t_sub_group_by]

                            if not isinstance(t_sub_group_by, str):
                                t_sub_group_by = str(t_sub_group_by)

                            t_group_by += " " + t_sub_group_by

                        if d[f] and mex < d[f]:
                            mex = d[f]

                        t.append({'value': d[f], 'name': t_group_by})

                    series.append({
                        'name': self.name,
                        'type': 'funnel',
                        'left': '0%',
                        'right': '20%',
                        'width': '80%',
                        'maxSize': '80%',
                        'avoidLabelOverlap': True,
                        'gap': 2,
                        'label': {
                            'position': 'inside',
                            'formatter': '{c}%',
                            'overflow': 'break',
                        },
                        'data': t
                    })

        option = {
            'color': color_palate,
            'title': {
                'text': self.name,
                'top': "1%",
                'left': "1%",
                'textStyle': {
                    'fontSize': '18',
                },
            },
            'legend': {
                'show': True if not self.statistics_with_trend else False,
                'orient': 'horizontal',
                'bottom': 'bottom',
                'type': 'scroll',
                'selectedMode': False if self.half_pie else True
            },
            'tooltip': {
                'trigger': 'item' if self.item_type in ['pie', 'radar', 'funnel'] else 'axis',
                'axisPointer': {
                    'type': 'cross',
                    'animation': False,
                    'label': {
                        'borderWidth': 1,
                        'shadowBlur': 0,
                        'shadowOffsetX': 0,
                        'shadowOffsetY': 0,
                    }
                },
            },
            'grid': {
                'left': '30px',
                'right': '30px',
                'bottom': '50px',
                'top': '50px',
                'containLabel': True,
            },
            'dataZoom': [
                {
                    'type': 'inside',
                },
            ],
            'toolbox': {
                'bottom': True,
                'show': True,
                'top': 35,
                'right': 5,
                'orient': 'vertical',
                'feature': {
                    'saveAsImage': {'show': True},
                    'restore': {'show': True if self.item_type in ['line', 'bar'] else False},
                }
            },
            'series': series
        }

        if self.item_type in ['pie']:
            if self.show_legend:
                leg_conf = self.get_pie_legend_conf()
                option['legend'] = leg_conf
            else:
                option['legend'].update({'show': False})

        # if labels:
        #     tmp = []
        #     for x in labels:
        #         tmp.append(str(x)[:19])

        #     labels = tmp

        if self.item_type in axis_chart_type and not self.is_polar:
            x_Axis = 'xAxis' if not self.horizontal_chart else 'yAxis'
            y_Axis = 'xAxis' if self.horizontal_chart else 'yAxis'

            # xAxis
            option.update({x_Axis: {
                'type': 'category',
                'data': labels,
                'boundaryGap': False if self.item_type == 'line' and not self.bar_line_field_id else True,
            }})

            option.update({y_Axis: {
                'type': 'value',
                'axisLabel': {
                    'formatter': lable_format
                }
            }})

        if self.item_type in ['radar']:
            radar = {'indicator': labels}
            if self.circular_chart:
                radar.update({'shape': 'circle'})
            option['radar'] = radar

        if self.is_polar:
            option.update({
                'polar': {
                    'radius': '80%'
                }
            })

            radius_axis = 'radiusAxis' if not self.circular_chart else 'angleAxis'
            angle_axis = 'radiusAxis' if self.circular_chart else 'angleAxis'

            option.update({
                radius_axis: {
                    'max': mex
                },
            })

            option.update({
                angle_axis: {
                    'type': 'category',
                    'data': labels,
                },
            })

        return option

    def get_item_chart(self, data, domain=None):
        if self.item_type not in ['list_view', 'statistics', 'kpi', 'embade_iframe', 'default_base_view']:
            data = self.get_data_in_pandas()
            # if not isinstance(data, list) and not data.empty:
            if data:
                option = self.prepare_chart(data)
                return {'options': option}
        return {}

    def prepare_chart_data(self, datasets, measure, labels):
        prepare_data = []
        if self.item_type in ['pie', 'funnel']:
            measure_d = datasets[measure]
            for index, value in enumerate(measure_d):
                prepare_data.append({'value': value, 'name': labels[index]})

            if self.item_type == 'pie' and self.half_pie:
                prepare_data.append({
                    'value': sum(measure_d),
                    'borderWidth': 0,
                    'itemStyle': {
                        'color': 'none',
                        'decal': {
                            'symbol': 'none'
                        },

                    }
                })

        elif self.item_type in ['radar']:
            prepare_data.append({
                'value': datasets[measure],
                'name': self.sudo().chart_measure_field_ids.filtered(lambda x: x.name == measure).field_description
            })

        else:
            prepare_data = datasets[measure]

        chart_data = {
            'data': prepare_data,
        }

        if self.item_type == 'line' or self.statistics_with_trend:
            if self.sudo().bar_line_field_id and self.sudo().bar_line_field_id.name == measure:
                chart_data.update({'type': 'bar'})
            else:
                chart_data.update({'type': 'line'})

            if self.is_smooth_line:
                chart_data.update({'smooth': True})

            if self.is_area_style:
                chart_data.update({'areaStyle': {}})

        if self.item_type == 'bar':
            if self.sudo().bar_line_field_id and self.sudo().bar_line_field_id.name == measure:
                chart_data.update({'type': 'line'})
            else:
                chart_data.update({'type': 'bar'})

            if self.bar_stack:
                chart_data.update({'stack': 'total'})

            if self.is_background:
                chart_data.update({'showBackground': True})

            if self.is_polar:
                chart_data.update({
                    'coordinateSystem': 'polar',
                    'emphasis': {
                        'focus': 'series'
                    }
                })

            if not self.bar_stack and not self.is_polar:
                chart_data.update({
                    'type': 'bar',
                    'label': {
                        'show': True,
                        'fontSize': 12,
                        'color': '#fff',
                        'position': 'inside',
                        'rich': {
                            'name': {}
                        },
                    }
                })
        if self.item_type == 'pie':
            chart_data.update({
                'name': self.sudo().chart_measure_field_ids.filtered(lambda x: x.name == measure).field_description,
                'type': 'pie',
                'startAngle': 180,
                'radius': '50%',
                'avoidLabelOverlap': True,
                'label': {
                    'show': True if self.show_lable and self.lable_position else False,
                    'position': self.lable_position,
                    'overflow': 'break',
                },
                'tooltip': {
                    'trigger': 'item',
                    'formatter': "{a} <br/>{b}: {c} ({d}%)"
                },
                'emphasis': {
                    'lable': {
                        'overflow': 'break',
                    },
                    'itemStyle': {
                        'shadowBlur': 10,
                        'shadowOffsetX': 0,
                        'shadowColor': 'rgba(0, 0, 0, 0.5)'
                    }
                },
                'itemStyle': {
                    'borderRadius': 5,
                    'borderColor': '#fff',
                    'borderWidth': 2
                },
            })

            if self.half_pie:
                chart_data.update({
                    'radius': ['40%', '70%'],
                    'center': ['50%', '70%'],
                })

            if self.doughnut_chart:
                if self._context.get('multiple_axis'):
                    x_count = self._context.get('multiple_axis_count', 1)
                    if x_count < 0:
                        x_count = 1
                    x_count = 20 * x_count
                    chart_data.update({'radius': [str(x_count - 20 + 3) + '%', str(x_count) + '%']})
                else:
                    chart_data.update({'radius': ['50%', '70%']})

        if self.item_type == 'radar':
            chart_data.update({
                'type': 'radar',
                'avoidLabelOverlap': False,
            })

        if self.item_type == 'funnel':
            chart_data.update({
                'name': 'Funnel',
                'type': 'funnel',
                'left': '15%',
                'right': '15%',
                'width': '70%',
                'maxSize': '70%',
                'avoidLabelOverlap': True,
                'gap': 2,
                'label': {
                    'position': 'inside',
                    'formatter': '{c}%',
                    'color': '#fff',
                    'overflow': 'truncate',
                },
                'itemStyle': {
                    'borderColor': '#fff',
                    'borderWidth': 2
                },
                'emphasis': {
                    'label': {
                        'position': 'right',
                        'formatter': '{b}Actual: {c}%',
                        'fontSize': 14
                    }
                },
            })

        return chart_data

    def get_data_from_query(self):
        try:
            if self.query:
                self._cr.execute(self.query)
                return self._cr.dictfetchall()
            else:
                return []
        except:
            return []

    def get_value_from_domain(self, domain=None):
        if domain is None:
            domain = []

        statistics_field = self.sudo().statistics_field

        if self.sudo().model_id:
            if self._context.get('limit'):
                statistics = self.env[self.sudo().model_id.model].sudo().search(domain, limit=100)
            elif self.is_limit_record and self.record_limit > 0:
                statistics = self.env[self.sudo().model_id.model].sudo().search(domain, limit=self.record_limit)
            else:
                statistics = self.env[self.sudo().model_id.model].sudo().search(domain)

            if statistics:
                if self.display_data_type == 'sum' and statistics_field and statistics_field.ttype not in ['many2one']:
                    statistics = sum(statistics.mapped(statistics_field.name))
                elif self.display_data_type == 'avg' and statistics_field and statistics_field.ttype not in [
                    'many2one']:
                    statistics = sum(statistics.mapped(statistics_field.name)) / len(statistics)
                elif self.display_data_type == 'count':
                    statistics = len(statistics)
                else:
                    statistics = 0
            else:
                statistics = 0

            return statistics if statistics else 0

        return 0

    def prepare_statistics(self):
        domain = self.get_item_domain()

        vals = {
            'name': self.name, 'action_id': self.action_id.xml_id or False, 'item_type': self.item_type,
            'statistics_item_title': self.statistics_item_title,
            'display_style': self.display_style, 'is_border': self.is_border, 'border_color': self.border_color,
            'border_position': self.border_position, 'background_color': self.background_color,
            'font_color': self.font_color, 'icon_color': self.icon_color, 'icon_bits': self.icon_bits,
            'media_option': self.media_option, 'field_description': self.sudo().statistics_field.field_description,
            'icon_image_url': 'web/image/dashboard.item.bits/' + str(self.id) + '/icon_image',
            'icon_background': self.icon_background
        }

        statistics = 0
        try:
            data = self.get_data_in_pandas()
        except:
            data = []

        if self.is_query:
            if self.stats_value_by_qry:
                x_axis = remove_space(self.stats_value_by_qry).split(",")
                # if not isinstance(data, list) and not data.empty:
                try:
                    statistics = float(sum([d[x_axis[0]] for d in data]))
                except Exception as e:
                    print(e)

        else:
            statistics = self.get_value_from_domain(domain)

        if statistics and not self.is_query:
            domain_2 = self.get_item_past_domain()
            statistics_past = self.get_value_from_domain(domain_2)

            if statistics_past:
                percentage = get_percentage(statistics_past, statistics)
                if percentage:
                    vals['is_positive'] = False if float(percentage) < 0 else True
                    percentage = str(percentage) + '% Then Last '
                    default_time_frame = self.bits_dashboard_id.default_time_frame
                    if 'week' in default_time_frame:
                        percentage += 'Week'
                    elif 'month' in default_time_frame:
                        percentage += 'Month'
                    elif 'year' in default_time_frame:
                        percentage += 'Year'
                    else:
                        percentage += 'Days'
                vals['percentage_string'] = percentage

        if statistics is None:
            statistics = 0

        statistics = human_format(statistics)
        if self.show_currency and self.company_id:
            currency_id = self.company_id.currency_id
            if currency_id:
                if currency_id.position == 'after':
                    statistics += currency_id.symbol
                else:
                    statistics = currency_id.symbol + str(statistics)

        vals['statistics'] = statistics

        if self.onclick_action and self.action_id:
            vals['onclick_action'] = self.onclick_action
            vals['action'] = {
                'id': self.action_id.id,
                'name': self.action_id.display_name,
                'res_model': self.action_id.res_model,
                'type': self.action_id.type,
                'xml_id': self.action_id.xml_id
            }

        state_data = {'title': self.item_title, 'statistics_data': vals}

        if self.statistics_with_trend:
            # (self.is_query and not isinstance(data, list)) and

            bottom_values = {}
            if (self.is_query and not isinstance(data, list)
                    and self.trend_display_style == 'style_1' and self.stats_chart_y_by_qry and self.stats_chart_x_by_qry != self.stats_chart_y_by_qry):
                if self.stats_chart_x_by_qry and self.stats_chart_y_by_qry:
                    df = data[[self.stats_chart_x_by_qry, self.stats_chart_y_by_qry]]
                    df.rename(columns={self.stats_chart_x_by_qry: 'value', self.stats_chart_y_by_qry: 'lable'},
                              inplace=True)
                    bottom_values = list(df.to_dict(orient='index', into=dict).values())
                    bottom_values = bottom_values[:5]

            elif not self.is_query and self.trend_display_style == 'style_1':
                bottom_values = self.prepare_bottom_values(domain)

            state_data.update({
                'display_type': 'statistics_with_trend_bits',
                'trend_primary_color': self.trend_primary_color,
                'apply_background': self.apply_background,
                'trend_display_style': self.trend_display_style,
                'bottom_values': bottom_values,
            })

            option = self.prepare_chart(data)
            state_data['center_values_options'] = {'options': self.update_options(option)}

        return state_data

    def prepare_kpi(self):
        domain = self.get_item_domain()

        kpi_value = 0
        if self.is_query:
            if self.query and self.stats_value_by_qry:
                data = self.get_data_in_pandas()
                if not isinstance(data, list) and not data.empty and self.stats_value_by_qry:
                    x_axis = remove_space(self.stats_value_by_qry).split(",")
                    if not data.empty and x_axis:
                        try:
                            kpi_value = float(data[x_axis[0]].to_list()[0])
                        except Exception as e:
                            print(e)

        else:
            kpi_value = self.get_value_from_domain(domain)

        if kpi_value:
            kpi_value = round(kpi_value, 2)
            percentage = round(((kpi_value or 1) * 100) / (self.kpi_target or 1), 2)

        else:
            percentage = 0

        return {
            'kpi_config': {
                'progres_recentage': percentage,
                'kpi_field': self.item_title if self.item_title else self.sudo().statistics_field.display_name,
                'kpi_display_style': self.kpi_display_style,
                'kpi_primary_color': self.kpi_primary_color,
                'kpi_target': self.kpi_target,
                'kpi_value': human_format(kpi_value),
                'apply_background': self.apply_background,
                'font_color': self.font_color,
                'progress_chart_options': self.get_progress_chart(percentage)
            }
        }

    def get_progress_chart(self, value=0):
        if self.kpi_display_style == "style_3":
            options = {
                'graphic': {
                    'elements': [
                        {
                            'type': 'group',
                            'left': 'center',
                            'top': 'center',
                            'children': [
                                {
                                    'type': 'rect',
                                    'shape': {
                                        'x': 0,
                                        'y': 0,
                                        'width': 500,
                                        'height': 13,
                                        'r': [15, 15, 15, 15]
                                    },
                                    'style': {
                                        'fill': '#E5E5E5'
                                    }
                                },
                                {
                                    'type': 'rect',
                                    'shape': {
                                        'x': 0,
                                        'y': 0,
                                        'width': value * 5,
                                        'height': 13,
                                        'r': [15, 15, 15, 15]
                                    },
                                    'style': {
                                        'fill': '#3874CB'
                                    },
                                    'keyframeAnimation': {
                                        'duration': 5000,
                                        'loop': True,
                                        'keyframes': [
                                            {
                                                'percent': 10,
                                                'scaleX': 0,
                                            },
                                            {
                                                'percent': 1,
                                                'scaleX': 1,
                                            }
                                        ]
                                    }
                                }
                            ]
                        }
                    ]
                }
            }
        else:
            options = {
                'color': self.font_color,
                'series': [
                    {
                        "type": "gauge",
                        "startAngle": 90,
                        "endAngle": -270,
                        "min": 0,
                        "max": value if value > 100 else 100,
                        "pointer": {"show": False},
                        "progress": {
                            "show": True,
                            "overlap": False,
                            "roundCap": True,
                            "clip": False,
                            "itemStyle": {"borderWidth": 1, "borderColor": "#464646"},
                        },
                        'axisLine': {
                            'lineStyle': {
                                'width': 12
                            }
                        },
                        'splitLine': {
                            'show': False,
                            'distance': 0,
                            'length': 10
                        },
                        'axisTick': {
                            'show': False
                        },
                        'axisLabel': {
                            'show': False,
                            'distance': 50
                        },
                        'data': self.gaugeData(value),
                        'title': {
                            'fontSize': 14
                        },
                        'detail': {
                            'fontSize': 14,
                            'color': 'inherit',
                            'borderColor': 'inherit',
                            'borderRadius': 20,
                            'borderWidth': 0,
                            'formatter': '{value}%'
                        }
                    }
                ],
            }
        return options

    def gaugeData(self, value=0):
        return [{
            'value': value,
            'name': 'Completed',
            'title': {
                'offsetCenter': ['0%', '-10%']
            },
            'detail': {
                'valueAnimation': True,
                'offsetCenter': ['0%', '20%']
            }
        }]

    def prepare_bottom_values(self, domain=None):
        if domain is None:
            domain = []

        chart_record = []

        if self.b_show_val:
            b_show_val = json.loads(self.b_show_val)
            if b_show_val:
                values = list(map(lambda x: int(x.get('id')), b_show_val))

                if self.sudo().b_trend_field_id.ttype == 'selection':
                    values = self.env['ir.model.fields.selection'].sudo().browse(values).mapped('value')

                domain.append((self.sudo().b_trend_field_id.name, 'in', values))

            if self.sudo().b_trend_field_id:
                obj = self.env[self.sudo().model_id.model].sudo()
                if self.is_limit_record and self.record_limit > 0:
                    domain = [('id', 'in', obj.search(domain, limit=self.record_limit).ids)]

                if self.b_measure_type == 'count':
                    chart_record = obj.read_group(domain, ['count:count(id)'], [self.sudo().b_trend_field_id.name],
                                                  lazy=False, limit=self.record_limit)
                elif self.sudo().b_measure_field_id:
                    chart_record = obj.read_group(domain, [self.sudo().b_measure_field_id.name + ':' + 'sum'],
                                                  [self.sudo().b_trend_field_id.name], lazy=False,
                                                  limit=self.record_limit)

        vals_dict = []
        for i, rec in enumerate(chart_record):
            vals_dict.append({
                'lable': str(
                    rec.get(self.sudo().b_trend_field_id.name)[
                        1] if self.sudo().b_trend_field_id.ttype == 'many2one' and isinstance(
                        rec.get(self.sudo().b_trend_field_id.name), tuple) else
                    rec.get(self.sudo().b_trend_field_id.name)),
                'value': human_format(
                    rec.get('count') if self.b_measure_type == 'count' else rec.get(
                        self.sudo().b_measure_field_id.name)),
            })

        return vals_dict

    def prepare_list_view_data(self):
        try:
            data = {
                'is_previous': False,
                'records_per_page': self.records_per_page,
                'list_data': [],
                'pager': False,
                'is_next': False
            }

            if self.is_query:
                list_data = self.get_data_in_pandas()
                # list_data = self.get_data_from_query()
                if not isinstance(list_data, list):
                    if not list_data.empty and self.y_axis:
                        try:
                            list_data = list(list_data.to_dict(orient='index', into=dict).values())
                        except Exception as e:
                            print(e)
                    else:
                        list_data = []

                if list_data:
                    data.update({
                        'list_data': list_data[0:self.records_per_page],
                        'pager': True if len(list_data) > self.records_per_page else False,
                        'is_next': True if len(list_data) > self.records_per_page else False
                    })

                if self.y_axis:
                    y_axis = json.loads(remove_space(self.y_axis))

                    fields_list = []
                    field_names = []
                    for key, value in y_axis.items():
                        fields_list.append(key)
                        field_names.append([key, value])

                    data.update({
                        'fields': field_names,
                        'list_length': len(list_data)
                    })

            else:
                data.update({'model_id': self.sudo().model_id.model})
                offset = 0

                fields_list = []
                field_names = []

                for f in self.sudo().list_view_field_ids:
                    fields_list.append(f.name)
                    field_names.append([f.name, f.field_description])

                domain = self.get_item_domain()
                order = self.display_order
                list_data = []
                if self.sudo().model_id and self.bits_dashboard_id.default_time_frame:
                    if not self.env[self.sudo().model_id.model].sudo()._fields.get("create_date"):
                        new_domain = []
                        for domm in safe_eval(self.item_domain):
                            if "date_filter" in domm:
                                date_domain = prepare_domain_v2(domm)
                                for dom in date_domain:
                                    new_domain.append(dom)
                            else:
                                new_domain.append(domm)

                    list_data = self.env[self.sudo().model_id.model].sudo().search_read(domain, fields_list,
                                                                                        offset=offset,
                                                                                        order=f'{fields_list[0] if fields_list and len(fields_list) > 0 else "display_name"} {"desc" if order and order == "descending" else "asc"}')
                    
                    new_list_data = []
                    for data in list_data:
                        new_list_data.append(convert_frozendict(data))

                    list_data = new_list_data
                if len(list_data) > self.records_per_page:
                    data.update({
                        'list_data': list_data[offset:self.records_per_page],
                        'pager': True,
                        'is_next': True
                    })
                else:
                    data.update({
                        'list_data': list_data,
                        'pager': False,
                        'is_next': False
                    })

                data.update({
                    'fields': field_names,
                    'list_length': len(list_data)
                })

            return data
        except ValueError as e:
            raise e
        except ProgrammingError as e:
            raise e
        except Exception as e:
            raise e

    def update_options(self, options):
        if options:
            del (options['title'])
            del (options['toolbox'])
            options.update({
                'grid': {'left': '0px', 'right': '0px', 'bottom': '0px', 'top': '0px'},
                'tooltip': {'trigger': 'axis', 'axisPointer': {'type': 'cross', 'label': {
                    'backgroundColor': self.trend_primary_color or '#484848'}}},
            })
            if self.trend_primary_color:
                options.update({'color': [self.trend_primary_color, '#4848448']})

            if isinstance(options['yAxis'], list):
                for res in options['yAxis']:
                    res.update({'boundaryGap': False, 'show': False, })
            else:
                options['yAxis'].update({'boundaryGap': False, 'show': False, })
            options['xAxis'].update({'boundaryGap': False, 'show': False, })

            if type(options['series']) != dict:
                for sr in range(0, len(options['series'])):
                    if len(options['series']):
                        options['series'][sr].update({
                            'label': True if not self.statistics_with_trend else False,
                            'smooth': self.is_smooth_line,
                            'areaStyle': {'opacity': 0 if self.trend_display_style == 'style_3' else 0.2, },
                        })
            else:
                options['series'].update({
                    'label': False,
                    'smooth': self.is_smooth_line,
                    'areaStyle': {'opacity': 0 if self.trend_display_style == 'style_3' else 0.2, },
                })
        return options

    def export_xlsx_item_data(self, item_id):
        if type(item_id) == int:
            dashboard_item_record = self.sudo().search([('id', '=', item_id)])
        else:
            dashboard_item_record = self.sudo()
        main_data = {}
        for rec in dashboard_item_record:
            data = {
                "name": rec.name,
                "model": {"name": rec.model_id.name, "model": rec.model_id.model},
                "item_title": rec.item_title,
                "statistics_item_title": rec.statistics_item_title,
                "view_data": rec.view_data,
                "trend_display_style": rec.trend_display_style,
                "trend_primary_color": rec.trend_primary_color,
                "apply_background": rec.apply_background,
                "action_id": rec.action_id.id,
                "kpi_display_style": rec.kpi_display_style,
                "kpi_primary_color": rec.kpi_primary_color,
                "is_smooth_line": rec.is_smooth_line,
                "is_area_style": True if rec.is_area_style else False,
                "is_background": rec.is_background,
                "horizontal_chart": rec.horizontal_chart,
                "bar_stack": rec.bar_stack,
                "is_polar": rec.is_polar,
                "circular_chart": rec.circular_chart,
                "doughnut_chart": rec.doughnut_chart,
                "half_pie": rec.half_pie,
                "list_view_style": rec.list_view_style,
                "list_view_field_ids": rec.list_view_field_ids.mapped("name"),
                "show_record_edit_button": rec.show_record_edit_button,
                "records_per_page": rec.records_per_page,
                "chart_measure_field_ids": rec.chart_measure_field_ids.mapped("name"),
                "bar_line_field_id": rec.bar_line_field_id.name if rec.bar_line_field_id else False,
                "is_bar_line": rec.is_bar_line,
                "display_order": rec.display_order,
                "chart_groupby_field": rec.chart_groupby_field.name if rec.chart_groupby_field else False,
                "chart_sub_groupby_field": rec.chart_sub_groupby_field.name,
                "chart_sort_by_field": rec.chart_sort_by_field.name if rec.chart_sort_by_field else False,
                "chart_sort_by_order": rec.chart_sort_by_order,
                "record_limit": rec.record_limit,
                "dashboard_grid_config_id": rec.dashboard_grid_config_id.id if rec.dashboard_grid_config_id else False,
                # "grid_config":json.dumps(grid_config.get(item)),
                "chart_preview_bits": rec.chart_preview_bits,
                'b_trend_field_id': rec.b_trend_field_id.name if rec.b_trend_field_id else False,
                "b_measure_type": rec.b_measure_type,
                "b_measure_field_id": rec.b_measure_field_id.name if rec.b_measure_field_id else False,
                "b_show_val": rec.b_show_val,
                # "chart_preview_data": rec.chart_preview_data,
                "company_id": rec.company_id.name if rec.company_id else False,
                "kpi_target": rec.kpi_target,
                "model_name": rec.model_name,
                "color_theme": rec.color_theme.name if rec.color_theme else False,
                "query": rec.query,
                "stats_value_by_qry": rec.stats_value_by_qry,
                "x_axis": rec.x_axis,
                "bar_line_measure": rec.bar_line_measure,
                "y_axis": rec.y_axis,
                "dashboard": rec.bits_dashboard_id.name,
                "item_domain": rec.item_domain,
                "is_limit_record": True if rec.is_limit_record else False,
                "item_type": rec.item_type,
                "is_query": True if rec.is_query else False,
                "v_records_per_page": rec.v_records_per_page,
                "onclick_action": True if rec.onclick_action else False,
                "statistics_with_trend": True if rec.statistics_with_trend else False,
                "display_data_type": rec.display_data_type,
                "statistics_field": rec.statistics_field.name,
                "show_currency": True if rec.show_currency else False,
                "media_option": rec.media_option,
                "icon_bits": rec.icon_bits,
                "display_style": rec.display_style,
                "background_color": rec.background_color,
                "font_color": rec.font_color,
                "icon_color": rec.icon_color,
                "is_border": True if rec.is_border else False,
                "border_position": rec.border_position,
                "border_color": rec.border_color,
                "legend_position": rec.legend_position,
                "show_legend": rec.show_legend,
                "lable_position": rec.lable_position,
                "show_lable": rec.show_lable,
                "lable_format": rec.lable_format,
                "stats_chart_y_by_qry": rec.stats_chart_y_by_qry,
                "stats_chart_x_by_qry": rec.stats_chart_x_by_qry,
                "icon_background": rec.icon_background,
                "embade_code": rec.embade_code
            }
            main_data.update({rec.name: data})
        json_data = json.dumps(main_data, indent=4)
        binary_data = base64.b64encode(json_data.encode('utf-8'))

        record = self.env['ir.attachment'].create({
            'name': 'dashbord_item.json',
            'type': 'binary',
            'datas': binary_data,
        })

        return {
            'type': 'ir.actions.act_url',
            'url': "web/content/?model=ir.attachment&id=" + str(
                record.id) + "&filename_field=name&field=datas&download=true&name=" + record.name,
            'target': 'self',
        }

    def get_dropdown_options(self, field_id, search):
        options = []
        if not field_id:
            return []
        b_trend_field_id = self.env['ir.model.fields'].sudo().browse(field_id)
        if b_trend_field_id:
            domain = []
            if search:
                domain.append(('name', 'ilike', search))

            if b_trend_field_id.ttype == 'many2one':
                for rec in self.env[b_trend_field_id.relation].sudo().search(domain, limit=5):
                    options.append([rec.id, rec.display_name])

            elif b_trend_field_id.ttype == 'selection':
                ids = b_trend_field_id.selection_ids.ids
                domain.append(('id', 'in', ids))
                for rec in self.env['ir.model.fields.selection'].sudo().search(domain, limit=5):
                    options.append([rec.id, rec.display_name])

        return options

    def get_pie_legend_conf(self):
        res = {}
        if self.legend_position == 'top':
            res.update({
                'show': True,
                'type': 'scroll',
                'orient': 'horizontal',
                'top': 25,
                'scroll': True,
            })
        elif self.legend_position == 'bottom':
            res.update({
                'show': True,
                'type': 'scroll',
                'orient': '',
                'bottom': 'bottom',
                'scroll': True,
            })
        elif self.legend_position == 'left':
            res.update({
                'show': True,
                'type': 'scroll',
                'orient': '',
                'left': 20,
                'top': 60,
                'scroll': True,
            })
        elif self.legend_position == 'right':
            res.update({
                'show': True,
                'type': 'scroll',
                'orient': '',
                'bottom': 'center',
                'top': 60,
                'right': 10,
                'scroll': True,
            })
        return res
