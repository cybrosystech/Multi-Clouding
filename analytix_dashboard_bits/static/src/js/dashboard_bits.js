/** @odoo-module **/

import {
  Component,
  onWillStart,
  onMounted,
  useState,
  useRef,
  onWillUnmount,
  onWillDestroy,
  status,
  xml,
} from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { session } from "@web/session";
// var datepicker = require("web.datepicker");
import { _t } from "@web/core/l10n/translation";
import { renderToElement } from "@web/core/utils/render";
import Dialog from "@web/legacy/js/core/dialog";
// var Domain = require("web.Domain");
import { makeContext } from "@web/core/context";
import { View } from "@web/views/view";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { DateTimeInput } from "@web/core/datetime/datetime_input";
import {isMobileOS } from "@web/core/browser/feature_detection";
var config = {}

function get_time_frames() {
  return {
    default: "Default",
    today: "Today",
    yesterday: 'Yesterday',
    next_day: "Next Day",
    next_week: "Next Week",
    next_month: "Next Month",
    next_year: "Next Year",
    this_week: "This Week",
    this_month: "This Month",
    this_year: "This Year",
    last_week: "Last Week",
    last_month: "Last Month",
    last_two_months: "Last 2 Months",
    last_three_months: "Last 3 Months",
    last_year: "Last Year",
    last_24_hr: "Last 24 Hr",
    last_10: "Last 10 Days",
    last_30: "Last 30 Days",
    last_60: "Last 60 Days",
    last_90: "Last 90 Days",
    last_365: "Last 365 Days",
    custom: "Custom Range",
  };
}

const { DateTime } = luxon;

class DashboardControllerBits extends Component {
  setup() {
    super.setup();
    this.rpc = useService("rpc");
    this.orm = useService("orm");
    this.state = useState({});
    this.action = useService("action");
    this.notification = useService("notification");
    this.el = useRef("el");
    this.grid = useRef("grid");
    this.notification = useService("notification");
    this.busService = this.env.services.bus_service;

    onWillStart(async () => {
      this.state.dashboard_data = [];
      this.state.charts = [];
      this.state.viewData = [];
      this.state.dashboard_id = this.props.action?.context?.params?.dashboard_id
        ? this.props.action?.context?.params?.dashboard_id
        : this.props?.action?.params?.dashboard_id;
      this.state.visual_options = {
        staticGrid: true,
        float: false,
        styleInHead: true,
        cellHeight: 100,
        verticalMargin: 8,
      };
      this.state.editMode = false;
      if (this.props.action?.context?.params?.default_color_theme) {
        this.state.color_theme =
          this.props.action?.context?.params?.default_color_theme;
      } else {
        if (
          this.props?.action?.params &&
          this.props?.action?.params?.default_color_theme
        ) {
          this.state.color_theme =
            this.props?.action?.params?.default_color_theme;
        } else {
          this.state.color_theme = false;
        }
      }
      document.addEventListener("click", (ev) => {
        $("body *").removeClass("show");
      });
      this.state.time_frame = this.props.action?.context?.params
        ?.default_time_frame
        ? this.props.action?.context?.params?.default_time_frame
        : this.props?.action?.params?.default_time_frame
        ? this.props?.action?.params?.default_time_frame
        : "default";
      this.state.view_mode = this.props.action?.context?.params
        ?.default_view_mode
        ? this.props.action?.context?.params?.default_view_mode
        : this.props?.action?.params?.default_view_mode
        ? this.props?.action?.params?.default_view_mode
        : false;

      this.state.all_time_frames = get_time_frames();
      this.state.is_filter = false;
      this.state.all_color_themes = {};

      // this.state.$from_date = new datepicker.DateWidget(this);

      // this.state.$to_date = new datepicker.DateWidget(this);
      this.state.from_date = DateTime.now();
      this.state.to_date = DateTime.now();
      this.state.applied_filters = [];
      this.state.filter_data = {};
      this.state.fav_filters = [];
      this.state.isAdded = false;
      this.busService.addEventListener(
        "notification",
        this._onNotification.bind(this)
      );
    });
    onMounted(async () => {
      // Load data
      if (this.state.dashboard_id) {
        let defs = [];
        defs.push(this.loadFavFilters());
        defs.push(this.loadDashboardData());
        defs.push(this.load_theme_data());
        await Promise.all(defs);
        await this.on_attach_callback();
      }
      document.documentElement.style.setProperty(
        "--dash_primary_color",
        this.state.dashboard_data.default_theme_paletts[0]
      );
      document.documentElement.style.setProperty(
        "--dash_secondary_color",
        this.state.dashboard_data.default_theme_paletts[1]
      );
      document
        .getElementById("body_container_bits")
        .addEventListener("click", this.handleOnclickEvents.bind(this));
      // Select the target node
      const target = document.getElementById("default_view");

      // Create an observer instance
      const observer = new MutationObserver(this.onMutation.bind(this));

      // Configuration of the observer
      const obs_config = { childList: true, subtree: true };

      // Start observing the target node for configured mutations
      observer.observe(target, obs_config);
    });

    onWillUnmount(() => {
      document
        .getElementById("body_container_bits")
        .removeEventListener("click", this.handleOnclickEvents.bind(this));
    });
    onWillDestroy(() => {
      this.busService.removeEventListener(
        "notification",
        this._onNotification.bind(this)
      );
    });
  }
  onClickHome(e){
    this.action.doAction({
      // name: _t(name),
      type: "ir.actions.client", 
      tag: "bits_all_dashboard_action",   
    });
  }
  handleOnclickEvents(ev) {
    if (ev.target.classList.contains("item_menu_dropdown_bits")) {
      // Perform your action when the button is clicked
      this.toggleDropdownClass(ev);
    } else if (ev.target.classList.contains("edit_item_bits")) {
      this.onClickEditItem(ev);
    } else if (ev.target.classList.contains("export_item_bits")) {
      this.onClickExportItem(ev);
    } else if (ev.target.classList.contains("duplicate_item_bits")) {
      this.onClickDupicateItem(ev);
    } else if (ev.target.classList.contains("delete_item_bits")) {
      this.onClickDeleteItem(ev);
    } else if (ev.target.classList.contains("oe_close")) {
      this.deleteCustomView(ev);
    } else if (ev.target.classList.contains("pg-v")) {
      this.onClickPager(ev);
    } else if (ev.target.classList.contains("sortable-itlems-list")) {
      this.onClickSort(ev);
    } else if (
      ev.target.classList.contains("statistics-bits") ||
      $(ev.target).parents(".statistics-bits").length > 0
    ) {
      this.onClickStatistics(ev);
    }
  }
  onMutation(mutation) {
    const target = $(document.getElementById("default_view")).clone();
    target.find(".o_control_panel").remove();
    const children = target.children();
    let grid_config = JSON.parse(this.state.dashboard_data.grid_config);
    for (let i = 0; i < children.length; i++) {
      const data = this.state.viewData[i];
      if (grid_config?.[data.node.id]) {
        this.Grid.addWidget(children[i], {
          id: data.node.id,
          x: grid_config[data.node.id].x,
          y: grid_config[data.node.id].y,
          w: grid_config[data.node.id].w,
          h: grid_config[data.node.id].h,
          autoPosition: grid_config[data.node.id]["autoPosition"],
          minW: grid_config[data.node.id].minW,
          maxW: grid_config[data.node.id].maxW,
          minH: grid_config[data.node.id].minH,
          maxH: grid_config[data.node.id].maxH,
        });
      } else {
        this.Grid.addWidget(children[i], {
          id: data.node.id,
          x: 0,
          y: 0,
          w: 6,
          h: 4,
          autoPosition: true,
          minW: 3,
          maxW: 12,
          minH: 3,
          maxH: 12,
        });
      }
    }
    this.state.isAdded = true;
  }
  // @deprecated
  async _onNotification(notifications) {
    if (
      this.state &&
      this?.__owl__?.component &&
      status(this.__owl__.component) != "destroyed"
    ) {
      var self = this;
      if (notifications?.detail?.length) {
        var type = notifications?.detail[0]?.type;
        var updates = notifications?.detail[0]?.payload.updates;
        if (!updates) {
          return;
        }
        if (
          updates.dashboard_ids.includes(this.state.dashboard_id) &&
          [
            "model_update_notify",
            "item_update_notify",
            "ditem_create_notify",
            "theme_add_nitify",
          ].includes(type)
        ) {
          //   this.fetch_item_data(updates, notifications)
          self.loadDashboardData().then(() => {
            self.on_attach_callback();
          });
        } else if (type == "theme_add_nitify") {
          self.loadDashboardData().then(() => {
            self.on_attach_callback();
          });
        }
      }
    }
  }
  async on_attach_callback() {
    if ($(".grid-items-container-bits .grid-stack").length > 0) {
      $(".grid-items-container-bits .grid-stack").empty();
    }
    this.state.viewData = [];
    this._load_analytics();
    this.initLayoutMode();
  }
  loadFavFilters() {
    var self = this;
    var user_id = session.uid;
    return this.orm
      .call(
        "dashboard.bits",
        "get_fav_filtrer_data",
        [this.state.dashboard_id, user_id],
        { context: self.prepareContex() }
      )
      .then(function (result) {
        self.state.fav_filters = result;
        if (result.length > 0) {
          result.forEach(function (res) {
            if (res.is_active && res.filters_value.length > 0) {
              res.filters_value.forEach(function (val) {
                self.state.applied_filters.push(val);
              });
            }
          });
        }
      });
  }
  loadDashboardData() {
    try {
      var self = this;
      return this.orm
        .call(
          "dashboard.bits",
          "get_dashboard_data",
          [this.state.dashboard_id],
          { context: self.prepareContex() }
        )
        .then(function (result) {
          self.state.dashboard_data = result;
          if (self.state.dashboard_data.default_from_date)
            self.state.from_date = DateTime.fromISO(
              self.state.dashboard_data.default_from_date
            );
          if (self.state.dashboard_data.default_to_date)
            self.state.to_date = DateTime.fromISO(
              self.state.dashboard_data.default_to_date
            );
        });
    } catch (e) {
      return e;
    }
  }
  load_theme_data() {
    var self = this;
    this.orm.call("dashboard.themes", "get_themes", []).then(function (result) {
      self.state.all_color_themes = result;
    });
  }
  async fetch_items_data(updates, notifications = false) {
    var self = this;
    var notify = notifications;
    var items = notify[0].payload.updates;
    if (!items.length) {
      return;
    }
    var item_ids = items.map((i) => {
      return i.item_id;
    });
    return await this.orm
      .call("dashboard.item.bits", "prepare_items_data", [item_ids], {
        context: self.prepareContex(),
      })
      .then(function (result) {
        items.forEach((value, index) => {
          if (self.dashboard_id != value.dashboard_id) {
            return;
          }
          self.state.dashboard_data.dashboard_items[value.item_id] =
            result[index][value.item_id];
        });
        self.on_attach_callback();
      });
  }
  async fetch_item_data(updates, notifications = false) {
    var self = this;
    var item_id = updates.item_id;
    return await await this.orm
      .call("dashboard.bits", "get_grid_config", [this.dashboard_id])
      .then(async function (config) {
        self.state.dashboard_data.grid_config = config;
        return await self.orm
          .call("dashboard.item.bits", "prepare_item_data", [item_id], {
            context: self.prepareContex(),
          })
          .then(function (result) {
            if (!result.item_data) {
              return;
            }
            self.state.dashboard_data.dashboard_items[item_id] = result;
            self.on_attach_callback();
          });
      });
  }
  async get_grid_config() {
    return await this.orm.call(
      "dashboard.bits",
      "search_read",
      [[this.dashboard_id]],
      {
        fields: ["grid_config"],
      }
    );
  }
  prepareContex() {
    var context = {
      time_frame: this.state.time_frame,
      from_date: this.state.from_date.toISODate(),
      to_date: this.state.to_date.toISODate(),
      color_theme: this.state.color_theme,
      filters: this.state.applied_filters,
      view_mode: this.state.view_mode,
    };
    return Object.assign(context, {});
  }
  _load_analytics() {
    var self = this;
    var $gridstackContainer = $(this.el.el).find(
      ".grid-items-container-bits .grid-stack"
    );
    if (this.Grid) {
      this.Grid.removeAll();
    }
    this.Grid = GridStack.init(
      this.state.visual_options,
      $gridstackContainer[0]
    );
    this.DisableEditMode();
    if (
      this.state.view_mode &&
      this.state.view_mode == "dark" &&
      $(document).find(".container_bits").length > 0
    ) {
      $(".o_action .o_content").addClass("dark_mode_bits");
    } else {
      $(".o_action .o_content").removeClass("dark_mode_bits");
    }
    var dashboard_items = this.state.dashboard_data.dashboard_items;
    // custom_views
    this._render_visuals(dashboard_items);
    this.Grid.on("resize", function (event, elem) {
      self.resize_chart();
    });
  }
  initLayoutMode() {}
  // custom_view
  async _render_view(dashboard_view, grid_config = {}) {
    if(!dashboard_view){
      return;
    }
    try {
      this._createController({
        node: dashboard_view,
        actionID: dashboard_view.action_id,
        context: dashboard_view.context_to_save,
        domain: JSON.parse(dashboard_view.domain),
        viewType: dashboard_view.view_mode,
      });
    } catch (err) {
      console.log(err);
    }
  }

  async _createController(params) {
    let result = await this.rpc("/web/action/load", {
      action_id: params.actionID,
    });
    if (!result) {
      // action does not exist
      this.isValid = false;
      // this.state.viewData.push({ node: params.node, value: false });
      return;
    }
    const viewMode = params.viewType || result.views[0][1];
    const formView = result.views.find((v) => v[1] === "form");
    if (formView) {
      this.formViewId = formView[0];
    }
    let viewProps = {
      resModel: result.res_model,
      type: viewMode,
      display: { controlPanel: false },
      selectRecord: (resId) => this.selectRecord(result.res_model, resId),
    };
    const view = result.views.find((v) => v[1] === viewMode);
    if (view) {
      viewProps.viewId = view[0];
    }
    const searchView = result.views.find((v) => v[1] === "search");
    viewProps.views = [
      [viewProps.viewId || false, viewMode],
      [(searchView && searchView[0]) || false, "search"],
    ];

    if (params.context) {
      viewProps.context = makeContext([params.context, { lang: session.user_context.lang }]);
      if ("group_by" in viewProps.context) {
        const groupBy = viewProps.context.group_by;
        viewProps.groupBy = typeof groupBy === "string" ? [groupBy] : groupBy;
      }
      if ("comparison" in viewProps.context) {
        const comparison = viewProps.context.comparison;
        if (
          comparison !== null &&
          typeof comparison === "object" &&
          "domains" in comparison &&
          "fieldName" in comparison
        ) {
          // Some comparison object with the wrong form might have been stored in db.
          // This is why we make the checks on the keys domains and fieldName
          viewProps.comparison = comparison;
        }
      }
    }
    if (params.domain) {
      viewProps.domain = params.domain;
    }
    if (viewMode === "list") {
      viewProps.allowSelectors = false;
    }
    this.state.viewData.push({ node: params.node, value: viewProps });
  }

  selectRecord(resModel, resId) {
    this.action.doAction({
      type: "ir.actions.act_window",
      res_model: resModel,
      views: [[this.formViewId, "form"]],
      res_id: resId,
    });
  }
  deleteCustomView(ev) {
    const dataID = $(ev.target).parent().parent().attr("data-id").split("_");
    const id = dataID[2];
    this.orm
      .call("dashboard.bits", "remove_custom_view", [this.dashboard_id, id])
      .then((res) => {
        if (res) {
          $(ev.target).parent().parent().parent().parent().remove();
        }
      });
  }

  _render_visuals(dashboard_items) {
    var self = this;
    var grid_config = this.state.dashboard_data.grid_config;
    if (!grid_config) {
      grid_config = {};
    }
    console.log(grid_config)
    let sorted_grid_keys = this._sort_grid_data(grid_config);
    sorted_grid_keys.forEach((key) => {
      let item = dashboard_items[key];
      if (!item || !item.display_type) {
        return;
      }
      // Custom view
      if (self.state.dashboard_data.has_group_admin_bits) {
        if (item.display_type == "default_base_view") {
          this.$item_header = $(renderToElement("GridItemCustomHeader", {}));
        } else {
          this.$item_header = $(
            renderToElement("GridItemHeader", {
              item: item,
            })
          );
        }
      }
      if (
        ["statistics", "statistics_with_trend_bits"].includes(item.display_type)
      ) {
        this.render_statistics(item, grid_config);
      } else if (["kpi"].includes(item.display_type)) {
        this.render_kpi_view(item, grid_config);
      } else if (["list_view"].includes(item.display_type)) {
        this.render_list_view(item, grid_config);
      } else if (["geo_map"].includes(item.display_type)) {
        this.render_map_view(item, grid_config);
      } else if (["embade_iframe"].includes(item.display_type)) { 
        this._render_iframe(item, grid_config); 
      } else if (["default_base_view"].includes(item.display_type)) {
        this._render_view(item.action, grid_config);
      } else {
        this.render_chart_view(item, grid_config);
      }
    });
  }
  _sort_grid_data(config){
    let sorted_conf = Object.entries(config).sort(
      (a, b) => a[1].y - b[1].y || a[1].x - b[1].x
    );
    let sorted_keys = []; 
    sorted_conf.forEach((i)=> sorted_keys.push(i[0]));
    let d_items_keys = Object.keys(this.state.dashboard_data.dashboard_items)
    d_items_keys.forEach((item_key) => {
      if(!sorted_keys.includes(item_key)){
        sorted_keys.push(item_key);
      }
    });  
    return sorted_keys
  }
  prepare_position_object(grid_config, item) {
    // @depricated
    let autoPosition = isMobileOS()?true:false;
    let config_obj = grid_config['item_'+ item.item_data.id] ? grid_config['item_'+ item.item_data.id] : grid_config[item.item_data.id];
    // ----------------------------------------------------------------
    return {
      id: item.item_data.id,
      x: config_obj["x"],
      y: config_obj["y"],
      w: config_obj["w"],
      h: config_obj["h"],
      autoPosition: autoPosition?true:config_obj["autoPosition"],
      minW: config_obj["minW"],
      maxW: config_obj["maxW"],
      minH: config_obj["minH"],
      maxH: config_obj["maxH"],
    };
  }
  render_statistics(item, grid_config) {
    if (!item.item_data.statistics_with_trend) {
      if (!item.statistics_data || !item.display_type) {
        return;
      }
      var ItemElement = $(
        renderToElement("StatisticsItemBits", {
          item: item,
        })
      );
      ItemElement.find(".grid-stack-item-content").prepend(this.$item_header);
      // ----------------------------------------------------------------
      // Statistics item
      // ----------------------------------------------------------------
      let grid_id = "item_"+String(item.item_data.id)
      if (grid_id in grid_config) {
        this.Grid.addWidget(
          ItemElement[0],
          this.prepare_position_object(grid_config, item)
        );
      } else {
        this.Grid.addWidget(ItemElement[0], {
          id: item.item_data.id,
          x: 0,
          y: 0,
          w: 3,
          h: 2,
          autoPosition: true,
          minW: 2,
          maxW: 3,
          minH: 2,
          maxH: 2,
        });
      }
    } else {
      // ----------------------------------------------------------------
      // Statistics with trens item
      // ----------------------------------------------------------------
      if (
        !item.center_values_options ||
        !item.statistics_data ||
        !item.bottom_values
      ) {
        return;
      }
      var ItemElement = $(
        renderToElement("StatisticsItem_WithTrendbits", {
          item: item["item_data"],
          botton_vals: item["bottom_values"],
          statistics_data: item["statistics_data"],
          trend_display_style: item["trend_display_style"],
          trend_primary_color: item["trend_primary_color"],
          apply_background: item["apply_background"],
        })
      );
      ItemElement.find(".grid-stack-item-content").prepend(this.$item_header);
      let grid_id = "item_"+String(item.item_data.id);
      if (grid_id in grid_config) {
        this.Grid.addWidget(
          ItemElement[0],
          this.prepare_position_object(grid_config, item)
        );
      } else {
        this.Grid.addWidget(ItemElement[0], {
          id: item.item_data.id,
          x: 0,
          y: 0,
          w: 3,
          h: 3,
          autoPosition: true,
          minW: 2,
          maxW: 6,
          minH: 3,
          maxH: 3,
        });
      }
      var ctx = ItemElement.find(
        "#" + item.item_data.id + "_" + item.item_data.item_type
      )[0];
      if (item.center_values_options) {
        if (item.item_data.trend_display_style == "style_1") {
          var Chart = echarts.init(ctx, this.view_mode, {
            height: 125,
          });
        } else {
          var Chart = echarts.init(ctx, this.view_mode);
        }
        if (item.center_values_options && item.center_values_options.options) {
          Chart.setOption(item.center_values_options.options);
          this.state.charts.push(Chart);
        }
      }
    }
  }
  render_kpi_view(item, grid_config) {
    if (item.kpi_config && !item.kpi_config.kpi_display_style) {
      return false;
    }
    var ItemElement = $(
      renderToElement("KpiItemsBits", {
        item: item["item_data"],
        kpi_config: item["kpi_config"],
      })
    );
    ItemElement.find(".grid-stack-item-content").prepend(this.$item_header);
    let grid_id = "item_"+String(item.item_data.id);
    if (grid_id in grid_config) {
      this.Grid.addWidget(
        ItemElement[0],
        this.prepare_position_object(grid_config, item)
      );
    } else {
      this.Grid.addWidget(ItemElement[0], {
        id: item.item_data.id,
        x: 0,
        y: 0,
        w: 3,
        h: 2,
        autoPosition: true,
        minW: 2,
        maxW: 3,
        minH: 2,
        maxH: 3,
      });
    }
    var ctx = ItemElement.find(
      "#" + item.item_data.id + "_" + item.item_data.item_type
    )[0];
    if (item.kpi_config.kpi_display_style == "style_3") {
      this.init_kpi_s3(ItemElement);
    } else {
      var Chart = echarts.init(ctx, null, {
        width: 175,
        height: 175,
      });
      Chart.setOption(item.kpi_config.progress_chart_options);
      this.state.charts.push(Chart);
    }
  }
  init_kpi_s3(ItemElement) {
    var $progress = ItemElement.find(".progress-per");
    var per = parseFloat($progress.attr("per"));
    if (per > 100) {
      $progress.css({ width: "100%" });
    } else {
      $progress.css({ width: per + "%" });
    }
    var animatedValue = 0;
    var startTime = null;
    function animate(timestamp) {
      if (!startTime) startTime = timestamp;
      var progress = timestamp - startTime;
      var stepPercentage = progress / 1000;

      if (stepPercentage < 1) {
        animatedValue = per * stepPercentage;
        $progress.attr("per", Math.floor(animatedValue) + "%");
        requestAnimationFrame(animate);
      } else {
        animatedValue = per;
        $progress.attr("per", Math.floor(animatedValue) + "%");
      }
    }
    requestAnimationFrame(animate);
  }
  render_list_view(item, grid_config) {
    var self = this;
    if (!item.list_view_data) {
      return;
    }
    var ItemElement = $(
      renderToElement("list_view_item_bits", {
        item: item,
        primary_color: this.color_theme,
        isArray: (obj) => Array.isArray(obj),
      })
    );
    ItemElement.find(".grid-stack-item-content").prepend(this.$item_header);
    let grid_id = "item_"+String(item.item_data.id);
    if (grid_id in grid_config) {
      this.Grid.addWidget(
        ItemElement[0],
        this.prepare_position_object(grid_config, item)
      );
    } else {
      this.Grid.addWidget(ItemElement[0], {
        id: item.item_data.id,
        w: 5,
        h: 6,
        x: 0,
        y: 0,
        autoPosition: true,
        minW: 3,
        maxW: 8,
        minH: 3,
        maxH: 8,
      });
    }
  }
  render_map_view(item, grid_config) {
    var self = this;
    var ItemElement = $(
      renderToElement("CountryMapBits", {
        item: item,
      })
    );
    let grid_id = "item_"+String(item.item_data.id); 
    if (grid_id in grid_config) {
      this.Grid.addWidget(
        ItemElement[0],
        this.prepare_position_object(grid_config, item)
      );
    } else {
      this.Grid.addWidget(ItemElement[0], {
        id: item.item_data.id,
        x: 0,
        y: 0,
        w: 4,
        h: 2,
        autoPosition: true,
        minW: 2,
        maxW: 12,
        minH: 2,
        maxH: 2,
      });
    }
    var ctx = ItemElement.find(
      "#" + item.item_data.id + "_" + item.item_data.item_type
    )[0];
    var Chart = echarts.init(ctx, this.state.view_mode);
    ItemElement.find(".grid-stack-item-content").prepend(this.$item_header);
    // item.options.tooltip.formatter = function (params) {
    //   var value = (params.value + "").split(".");
    //   value =
    //     value[0].replace(/(\d{1,3})(?=(?:\d{3})+(?!\d))/g, "$1,") +
    //     "." +
    //     value[1];
    //   return params.seriesName + "<br/>" + params.name + " : " + value;
    // };
    Chart.setOption(item.options); 
  }
  render_chart_view(item, grid_config) {
    var ItemElement = $(
      renderToElement("GridstackItemBits", {
        item: item["item_data"],
      })
    );
    let grid_id = "item_"+String(item.item_data.id); 
    if (grid_id in grid_config) {
      this.Grid.addWidget(
        ItemElement[0],
        this.prepare_position_object(grid_config, item)
      );
    } else {
      this.Grid.addWidget(ItemElement[0], {
        id: item.item_data.id,
        x: 0,
        y: 0,
        w: 4,
        h: 3,
        autoPosition: true,
        minW: 2,
        maxW: 12,
        minH: 2,
        maxH: 12,
      });
    }
    if (item.group && item.group.length <= 0) {
      $(ItemElement.find(".grid-stack-item-content > div")[1]).remove();
      ItemElement.find(".grid-stack-item-content").append(
        $(renderToElement("NoDataBits"))
      );
      ItemElement.find(".grid-stack-item-content").prepend(this.$item_header);
      return;
    }
    var ctx = ItemElement.find(
      "#" + item.item_data.id + "_" + item.item_data.item_type
    )[0];
    var Chart = echarts.init(ctx, this.state.view_mode);
    ItemElement.find(".grid-stack-item-content").prepend(this.$item_header);
    try {
      Chart.setOption(item.options);
      this.state.charts.push(Chart);
    } catch (e) {
      $(ItemElement.find(".grid-stack-item-content > div")[1]).remove();
      ItemElement.find(".grid-stack-item-content").append(
        $(renderToElement("NoDataBits"))
      );
      ItemElement.find(".grid-stack-item-content").prepend(this.$item_header);
    }
  }
  _render_iframe(item, grid_config){
    var ItemElement = $(
      renderToElement("EmbadeIframe", {
        item: item.item_data,
      })
    ); 
    ItemElement.find(".iframe-header").html(this.$item_header); 
    ItemElement.find('.iframe-body').append(item.item_data.embade_code);
    let grid_id = "item_"+String(item.item_data.id); 
    if (grid_id in grid_config) {
      this.Grid.addWidget(
        ItemElement[0],
        this.prepare_position_object(grid_config, item)
      );
    } else {
      this.Grid.addWidget(ItemElement[0], {
        id: item.item_data.id,
        x: 0,
        y: 0,
        w: 6,
        h: 6,
        autoPosition: true,
        minW: 3,
        maxW: 12,
        minH: 3,
        maxH: 12,
      });
    } 
  }
  resize_chart() {
    if (this.state.charts) {
      this.state.charts.forEach((element) => {
        element.resize();
      });
    }
  }
  // Edit dashboard layout events
  // ----------------------------------------------------------------
  //           EDIT DASHBOAR LAYOUT EVENTS
  // ----------------------------------------------------------------
  onEditGridLayout(ev) {
    this.Grid.setStatic(false);
    this.state.editMode = true;
    $(this.el.el).find(".bf_edit_controls").addClass("d-none");
    $(this.el.el).find(".af_edit_controls").removeClass("d-none");
    if (this.Grid) {
      this.Grid.enable();
    }
  }
  onSaveGridLayout(ev) {
    var configuration = this.get_current_grid_config();
    var model = "dashboard.bits";
    var rec_id = this.state.dashboard_data.dashboard_id;
    this.orm.call(model, "write", [
      rec_id,
      {
        grid_config: JSON.stringify(configuration),
      },
    ]);
    this.state.dashboard_data.grid_config = configuration;
    this.DisableEditMode();
    this.resize_chart();
  }
  toggleDropdownClass(ev) {
    const parent = $(ev.target).parent();
    ev.stopPropagation();
    $("body *").removeClass("show");
    parent.find(".dropdown-menu")?.toggleClass("show");
  }
  onDiscartGridLayout(ev) {
    this.state.editMode = false;
    this.DisableEditMode();
    this.on_attach_callback();
  }
  DisableEditMode(ev) {
    this.Grid.setStatic(true);
    $(this.el.el).find(".bf_edit_controls").removeClass("d-none");
    $(this.el.el).find(".af_edit_controls").addClass("d-none");
    this.Grid.commit();
  }
  get_current_grid_config(ev) {
    var curr_grid_data = document.querySelector(".grid-stack").gridstack.el.gridstack.engine.nodes;
    var configuration = {};
    if (this.state.dashboard_data.grid_config) {
      configuration = this.state.dashboard_data.grid_config;
    }
    Object.keys(curr_grid_data).forEach((element) => {
      configuration['item_'+ String(curr_grid_data[element].id)] = {
        x: curr_grid_data[element]["x"],
        y: curr_grid_data[element]["y"],
        h: curr_grid_data[element]["h"],
        w: curr_grid_data[element]["w"],
        minH: curr_grid_data[element]["minH"] || false,
        maxH: curr_grid_data[element]["maxH"] || false,
        maxW: curr_grid_data[element]["maxW"] || false,
        minW: curr_grid_data[element]["minW"] || false,
      };
    });
    return configuration;
  }
  // ----------------------------------------------------------------
  //           OVER EDIT DASHBOAR LAYOUT EVENTS
  // ----------------------------------------------------------------

  // ----------------------------------------------------------------
  //           LIST VIEW EVENTS START
  // ----------------------------------------------------------------
  onClickPager(e) {
    var self = this;
    var $target = $(e.target);
    var target_event = $target.data("event");
    var curr_list = $target.parent().find(".records-count-bits").data("count");
    var item_id = parseInt($target.data("itemid"));
    var model = $target.data("model");
    var $item = $target.parents(".grid-stack-item-content");
    this.page;
    var order_by = $target;
    this.orm
      .call("dashboard.bits", "prepare_more_list_data", [
        item_id,
        {
          model: model,
          target_event: target_event,
          curr_list: curr_list,
          order_by: order_by,
        },
        this.dashboard_id,
      ])
      .then(function (result) {
        var list_items = $(
          renderToElement("MoreItemsBits", {
            item: result,
            isArray: (obj) => Array.isArray(obj),
          })
        );
        $item.find("#list_body").replaceWith(list_items);
        $target.parent().find(".records-count-bits").data().count =
          result.curr_list;
        $target.parent().find(".records-count-bits").html(result.list_numbers);

        if (result.is_next) {
          if (!$target.parent().find(".btn-next.pager").length) {
            $target.parent().find(".btn-next").addClass("pager");
          }
        } else {
          if (!result.is_next) {
            $target.parent().find(".btn-next").removeClass("pager");
          }
        }

        if (result.is_previous) {
          if (!$target.parent().find(".btn-previous.pager").length) {
            $target.parent().find(".btn-previous").addClass("pager");
          }
        } else {
          if (!result.is_previous) {
            $target.parent().find(".btn-previous").removeClass("pager");
          }
        }
      });
  }
  onClickSort(e) {
    var $current = $(e.target);
    var index = $current.index();
    var rows = [];
    var thClass = $current.hasClass("asc") ? "desc" : "asc";
    $current.parent().find("th").removeClass("asc desc");
    $current.addClass(thClass);

    $(e.target)
      .parents("table")
      .find("tbody tr")
      .each(function (index, row) {
        rows.push($(row).detach());
      });

    rows.sort(function (a, b) {
      var aValue = $(a).find("td").eq(index).text();
      var bValue = $(b).find("td").eq(index).text();
      if(Number(aValue) && Number(bValue))
        return Number(aValue) > Number(bValue) ? 1 : Number(aValue) < Number(bValue) ? -1 : 0;
      return aValue > bValue ? 1 : aValue < bValue ? -1 : 0;
    });

    if ($current.hasClass("desc")) {
      rows.reverse();
    }
    $.each(rows, function (index, row) {
      $(e.target).parents("table").find("tbody").append(row);
    });
  }
  // ----------------------------------------------------------------
  //           OVER LIST VIEW EVENTS
  // ----------------------------------------------------------------
  async onClickDatesApply(ev) {
    var $target = $(ev.target);
    // this.from_date = $target.parents('.date_picker_container').find('input.from_date').val();
    // this.to_date = $target.parents('.date_picker_container').find('input.to_date').val();
    if (this.state.from_date && this.state.to_date) {
      var d_start_date = this.state.from_date.toISODate();
      var d_end_date = this.state.to_date.toISODate();

      await this.orm.call("dashboard.bits", "write", [
        [this.state.dashboard_id],
        {
          default_start_date: d_start_date,
          default_end_date: d_end_date,
        },
      ]);
    }
    if (this.state.from_date && this.state.to_date) {
      this.loadDashboardData().then(() => {
        this.on_attach_callback();
      });
    }
  } 
  AddItemButton(ev) {
    this.action.doAction({
      name: _t("Dashboard Item"),
      type: "ir.actions.act_window",
      res_model: "dashboard.item.bits",
      view_mode: "form",
      views: [[false, "form"]],
      context: {
        bits_dashboard_id: this.state.dashboard_id || false,
      },
    });
  }
  // HEADER EVENTS:
  async onSelectTimeframe(ev) {
    var $target = $(ev.target);
    var Tframe = $target.data("date-format");
    this.state.time_frame = Tframe;
    $target
      .parents(".time_range_filter")
      .find("#date_filter_selection_bits")
      .html($target.text());
    var $range_ele = $target
      .parents(".time_range_filter")
      .find(".date_picker_container");
    if (Tframe == "custom") {
      if ($range_ele.hasClass("d-hidden")) {
        $range_ele.toggleClass("d-hidden");
      }
    } else {
      $range_ele.addClass("d-hidden");
    }
    if (this.state.time_frame != "custom") {
      this.loadDashboardData().then(() => {
        this.on_attach_callback();
      });
    }
  }
  async onSelectColorTheme(ev) {
    ev.preventDefault();
    var $target = $(ev.target);
    var colorTheme = $target.data("color-theme");
    this.state.color_theme = colorTheme;
    $target
      .parents(".color_theme_bits")
      .find("#color_theme_selection_bits")
      .html($target.text());
    this.loadDashboardData().then(() => {
      this.on_attach_callback();
    });
  }
  async onSelectViewMode(ev) {
    var $target = $(ev.target);
    var viewMode = $target.data("view-mode");
    this.state.view_mode = viewMode;
    $target
      .parents(".view_mode_switch")
      .find("#view_mode_selection_bits")
      .html($target.text());
    $(".grid-items-container-bits .grid-stack").addClass("grid-stack");
    await this.on_attach_callback();
  }
  saveViewMode(ev) {
    var $target = $(ev.target);
    var mode = $target.data("curr-mode");
    if (mode) {
      this.orm.call("dashboard.bits", "write", [
        [this.state.dashboard_id],
        { default_view_mode: mode },
      ]);
    }
  }
  onDefaultTimeFrame(ev) {
    var $target = $(ev.target);
    var tframe = $target.data("curr-mode");
    var d_start_date = $(".date_picker_bits")
      .find(".date_range_input_bits.from_date")
      .val();
    var d_end_date = $(".date_picker_bits")
      .find(".date_range_input_bits.to_date")
      .val();
    if (tframe) {
      this.orm.call("dashboard.bits", "write", [
        this.state.dashboard_id,
        {
          default_time_frame: tframe,
          default_start_date: d_start_date,
          default_end_date: d_end_date,
        },
      ]);
    }
  }
  async onDefaultColorTheme(ev) {
    var $target = $(ev.target);
    var ctheme = $target.data("curr-mode");
    if (ctheme) {
      await this.orm.call("dashboard.bits", "write", [
        this.state.dashboard_id,
        { default_color_theme: ctheme },
      ]);
    }
    this.loadDashboardData().then(() => {
      this.on_attach_callback();
    });
  }
  // custome filter evnets
  onInputFocusOut(ev) {
    $(ev.target).val("");
    $(ev.target).parent().find(".c_filters_container_bits").removeClass("show");
  }
  async onClickCustomfilter(ev) {
    this.toggleDropdownClass(ev);
    // ev.preventDefault();
    var self = this;
    var $target_data = $(ev.target).data();
    var target = $(ev.target);
    this.state.is_filter = false;
    if ($target_data.ttype == "relational") {
      if (
        !Object.keys(self.state.filter_data).includes(
          String($target_data.filter_id)
        )
      ) {
        this.orm
          .call($target_data.target_model, "fields_get")
          .then(function (fields) {
            var fields = [];
            if (Object.keys(fields).includes("name")) {
              fields = ["name"];
            } else {
              fields = ["display_name"];
            }
            var kwargs = { fields: fields };
            self.orm
              .call($target_data.target_model, "search_read", [], { ...kwargs })
              .then(function (result) {
                self.state.filter_data[$target_data.filter_id] = result;
              });
          });
      }
    } else {
      if (
        !Object.keys(self.state.filter_data).includes(
          String($target_data.filter_id)
        )
      ) {
        this.orm
          .call($target_data.target_model, "fields_get")
          .then(function (result) {
            var selections = result[$target_data.field].selection;
            self.state.filter_data[$target_data.filter_id] = selections;
          });
      }
    }
    this.state.is_filter = true;
  }
  onClickCustomfilterInput(ev) {
    var self = this;
    var $target_data = $(ev.target).data();
    var target = $(ev.target);
    var input_str = target.val();
    if ($target_data.ttype != "selection") {
      this.state.is_filter = false;
      var filtered_data = self.state.filter_data[$target_data.filter_id];
      if (input_str.trim().length < 0) {
        filtered_data = self.state.filter_data[$target_data.filter_id].slice(
          0,
          10
        );
      } else {
        filtered_data = filtered_data.filter((obj) =>
          obj.name
            ? obj.name.toLowerCase().includes(input_str)
            : obj.display_name.toLowerCase().includes(input_str)
        );
      }
      this.state.is_filter = true;
    } else {
      target.val("");
    }
  }
  async onClickFilterValue(ev) {
    var self = this;
    var $target = $(ev.target);
    var $targetInput = $(ev.target).parents(".filter-bits").find("input");
    var ttype = $target.data("ttype");
    var filterId = $targetInput.data("filter_id");
    var t_model_id = $targetInput.data("target_model");
    var rec_id = $target.data().rid;
    var filter = this.state.dashboard_data.filters.filter((f) => {
      return f.target_field_model == t_model_id;
    });
    if (!filter.length) {
      return;
    } else {
      filter = filter[0];
    }
    // changed fid to model
    if (
      ttype == "relational" &&
      this.state.applied_filters.length &&
      this.state.applied_filters.filter((el) => {
        return el.model_id == t_model_id;
      }).length
    ) {
      this.state.applied_filters.forEach(async function (element) {
        var curr_elem = element;
        if (curr_elem.model_id == t_model_id) {
          var field_name = $target.data("value");

          if (!curr_elem.apply_filter_rec_ids.includes(rec_id)) {
            curr_elem.apply_filter_rec_ids.push(rec_id);
            curr_elem.field_names.push($target.data("value"));
            curr_elem.filter_name = filter.target_field_name + " in " + curr_elem.field_names.join(",");
          }
        }
        self.state.applied_filters[
          self.state.applied_filters.indexOf(element)
        ] = curr_elem;
      });
    } else {
      if (ttype == "relational") {
        var field_id = $target.data("rid");
        this.state.applied_filters.push({
          uid: Date.now(),
          fid: filterId,
          filter_name:
            filter.target_field_name + " in " + $target.data("value"),
          model_id: filter.target_field_model,
          filter_domain:
            "[('" + filter.target_field_tname + "','in',[" + rec_id + "])]",
          apply_filter_field: filter.target_field_tname,
          apply_filter_rec_ids: [rec_id],
          field_names: [$target.data("value")],
          filter_field_type: "relational",
        });
      } else {
        var field_value = $target.data("sid");
        if (
          this.state.applied_filters.length &&
          this.state.applied_filters.filter((el) => {
            return el.model_id == filterId;
          }).length
        ) {
          this.state.applied_filters.forEach(async function (element) {
            var curr_elem = element;
            if (curr_elem.model_id == filterId) {
              self.state.applied_filters[
                self.state.applied_filters.indexOf(element)
              ] = {
                uid: Date.now(),
                fid: filterId,
                model_id: filter.target_field_model,
                filter_name:
                  filter.target_field_name + " = " + $target.data("value"),
                filter_domain:
                  "[('" +
                  filter.target_field_tname +
                  "','=','" +
                  field_value +
                  "')]",
                filter_field_type: "selection",
              };
            }
          });
        } else {
          this.state.applied_filters.push({
            uid: Date.now(),
            fid: filterId,
            model_id: filter.target_field_model,
            filter_name:
              filter.target_field_name + " = " + $target.data("value"),
            filter_domain:
              "[('" +
              filter.target_field_tname +
              "','=','" +
              field_value +
              "')]",
            filter_field_type: "selection",
          });
        }
      }
    }
    this.state.applied_filters = this.state.applied_filters.filter(
      (obj, index, self) =>
        index === self.findIndex((o) => o["filter_name"] === obj["filter_name"])
    );
    this.loadDashboardData().then(() => {
      this.on_attach_callback();
    });
  }
  async onClickFacetRemove(ev) {
    var self = this;
    var $target = $(ev.target);
    this.state.applied_filters = this.state.applied_filters.filter((flt) => {
      return flt.uid != parseInt($target.data().uid);
    });
    self.loadDashboardData().then(() => {
      self.on_attach_callback();
    });
  }
  async onClickFavoriteFilterSave(ev) {
    var self = this;
    var user_id = session.uid;
    if (!this.state.applied_filters.length) {
      this.notification.add("Opps! No any filters applied.", {
        type: "info",
      });
      return false;
    }
    var $parent = $(ev.target).parents(".dropdown-item");
    var fname = $parent.find(".input-filter-bits").val();
    var use_default = $parent.find(".user-default-bits").val();
    // made empty when default use set true

    // ---------------
    var dashboard_id = this.state.dashboard_id;
    await this.orm
      .call("favorite.filter.bits", "create", [
        {
          name: fname,
          dashboard_id: dashboard_id,
          is_active: use_default == "on" ? true : false,
          filter_value: this.state.applied_filters,
          user_id: user_id,
        },
      ])
      .then(async function (result) {
        if (use_default == "on") {
          self.state.applied_filters = [];
        }
        self.loadFavFilters().then(() => {
          self.loadDashboardData().then(() => {
            self.on_attach_callback();
          });
        });
      });
  }
  async onClickFavoriteApply(ev) {
    var self = this;
    this.state.applied_filters = [];
    var filterId = $(ev.target).data("filter_id");
    await this.orm
      .call("favorite.filter.bits", "write", [[filterId], { is_active: 1 }])
      .then(async function (result) {
        self.loadFavFilters().then(() => {
          self.loadDashboardData().then(() => {
            self.on_attach_callback();
          });
        });
      });
  }
  async onClickFavoriteRemove(ev) {
    ev.stopPropagation();
    this.state.applied_filters = [];
    var self = this;
    var filterId = $(ev.target).data("fvid");
    await this.orm.call("favorite.filter.bits", "unlink", [[filterId]]);
    await self.loadFavFilters();
    this.loadDashboardData().then(() => {
      this.on_attach_callback();
    });
  }
  onClickToggleSidebar() {
    $(".mob_filter_bits").toggleClass("d-hidden");
  }
  // ----------------------------------------------------------------
  // Item events
  onClickEditItem(ev) {
    var rec_id = $(ev.target).data("stack-id");
    // var model_id = $(ev.target).data("model_id");
    this.action.doAction({
      title: "",
      name: _t("Dashboard Item"),
      type: "ir.actions.act_window",
      views: [[false, "form"]],
      res_model: "dashboard.item.bits",
      res_id: rec_id,
      flags: {
        mode: "edit",
      },
      target: "current",
      context: {
        create: false,
      },
    });
  }
  async onClickExportItem(e) {
    var rec_id = $(e.target).parents(".grid-stack-item").data("stack-id");

    const res = await this.rpc("/export/dashboard/item", {
      item_id: rec_id,
    });
    this.action.doAction(res);
  }
  onClickDupicateItem(e) {
    var self = this;
    var rec_id = $(e.target).data("stack-id");
    var $content = $(
      renderToElement("DashboardsSelection", {
        dashboards: this.state.dashboard_data.dashboards,
        record_id: rec_id,
      })
    );
    var dialog = new Dialog(this, {
      title: _t("Copy Item"),
      $content: $content,
      size: "medium",
      buttons: [
        {
          text: _t("Copy"),
          classes: "btn-primary",
          close: true,
          click() {
            var item_id = $(".ds_selection_bits").data("item_id");
            var selected_dashboard = $(".ds_selection_bits").val();
            self.doCopyrecord(selected_dashboard, item_id);
            dialog.close();
          },
        },
        {
          text: _t("Move"),
          classes: "btn-primary",
          close: true,
          click() {
            var item_id = $(".ds_selection_bits").data("item_id");
            var selected_dashboard = $(".ds_selection_bits").val();
            self.doMoverecord(selected_dashboard, item_id);
            dialog.close();
            dialog.close();
          },
        },
      ],
    });
    dialog.open();
  }
  async doCopyrecord(selected_dashboard, item_id) {
    await this.orm.call(
      "dashboard.item.bits",
      "copy_dashboard_item_bits",
      [item_id],
      {
        context: {
          selected_dashboard_id: parseInt(selected_dashboard),
        },
      }
    );
  }
  async doMoverecord(selected_dashboard, item_id) {
    var self = this;
    await this.orm
      .call("dashboard.item.bits", "move_dashboard_item_bits", [item_id], {
        context: {
          selected_dashboard_id: parseInt(selected_dashboard),
        },
      })
      .then(async function () {
        self.loadDashboardData().then(() => {
          self.on_attach_callback();
        });
      });
  }
  async onClickDeleteItem(e) {
    var self = this;
    var rec_id = $(e.target).data("stack-id");
    var dialog = new Dialog(this, {
      title: _t("Delete Item"),
      $content: "<h3>Are you sure you want to delete?</h3>",
      size: "medium",
      buttons: [
        {
          text: _t("Yes"),
          classes: "btn-primary",
          close: true,
          click: async function () {
            self.doDeleteItem(rec_id);
          },
        },
        {
          text: _t("No"),
          classes: "btn-primary",
          close: true,
        },
      ],
    });
    dialog.open();
  }
  async doDeleteItem(rec_id) {
    var self = this;
    // removed direct unlink method bcase of delete
    await this.orm
      .call("dashboard.item.bits", "unlink_item_bits", [[rec_id]])
      .then(async function () {
        self.loadDashboardData().then(() => {
          self.on_attach_callback();
        });
      });
  }
  onClickStatistics(e) {
    var item_id = $(e.target).parents(".statistics-bits").data("stackId");
    var action_data =
      this.state?.dashboard_data?.dashboard_items[item_id]?.statistics_data
        .action;
    if (action_data && action_data.id) {
      this.action.doAction({
        name: _t(action_data.name),
        type: "ir.actions.act_window",
        res_model: action_data.res_model,
        views: [
          [false, "list"],
          [false, "form"],
        ],
        target: "current",
      });
    }
  }
  onClickToggleDropdown(e) {}
  // ----------------------------------------------------------------
  //           Media Option Events
  // ----------------------------------------------------------------
  // onSlideshowDashboard:function(e) {
  // },
  onCaptureDashboard(e) {
    e.stopPropagation();
    var $dashboard = $(".grid-items-container-bits")[0];
    html2canvas($dashboard, { useCORS: true, allowTaint: false }).then(
      function (canvas) {
        window.jsPDF = window.jspdf.jsPDF;
        var document = new jsPDF("p", "mm", "a4");
        var img = canvas.toDataURL("image/jpeg", 0.9);
        var Props = document.getImageProperties(img);
        var w = document.internal.pageSize.getWidth();
        var h = (Props.height * w) / Props.width;
        var pageHeight = 295;
        var heightLeft = h;
        var position = 0;

        document.addImage(img, "JPEG", 0, 0, w, h, "FAST");
        heightLeft -= pageHeight;
        while (heightLeft >= 0) {
          position = heightLeft - h;
          document.addPage();
          document.addImage(img, "JPEG", 0, position, w, h, "FAST");
          heightLeft -= pageHeight;
        }
        document.save("test.pdf");
      }
    );
  }
  // copy_text: function(){
  // },
  onGenerateShareLink(e) {
    var self = this;
    var $content = "";
    var base_url = window.location.origin;
    this.orm
      .call("dashboard.bits", "get_sharable_link", [this.state.dashboard_id])
      .then(function (result) {
        var link = base_url + result;
        $content = $(
          renderToElement("DashboardEmbadeBits", {
            is_embade: false,
            link: link,
          })
        );
        var dialog = new Dialog(this, {
          title: _t("Dashboard Sharable Link"),
          $content: $content,
          size: "medium",
          buttons: [
            {
              text: _t("Copy"),
              classes: "btn-primary",
              close: false,
              click: async function () {
                if (navigator.clipboard) {
                  var text = $("#link").text();
                  await navigator.clipboard.writeText(text);

                  self.notification.add("Copied Successfully", {
                    title: "Copy Dahboard Link",
                    type: "info",
                    sticky: false,
                  });
                } else {
                  self.notification.add(
                    "Opps! Enable to copy the text. It seems you are using insecure contexts. Use (HTTPS) instead of (HTTP) OR copy the text manually",
                    {
                      title: "Error in copy dahboard link",
                      type: "danger",
                      sticky: false,
                    }
                  );
                }
              },
            },
            {
              text: _t("Close"),
              classes: "btn-primary",
              close: true,
            },
          ],
        });
        dialog.open();
      });
  }
  onEmbadeDashboard(e) {
    var self = this;
    var $content = "";
    var base_url = window.location.origin;
    this.orm
      .call("dashboard.bits", "get_sharable_link", [this.state.dashboard_id])
      .then(function (result) {
        var link = base_url + result;
        $content = $(
          renderToElement("DashboardEmbadeBits", {
            is_embade: true,
            link: link,
          })
        );
        $content
          .find("h3#link")
          .text(
            '<iframe src="' + link + '" width="100%" height="100%"></iframe>'
          );
        var dialog = new Dialog(this, {
          title: _t("Copy the embed dashboard code"),
          $content: $content,
          size: "medium",
          buttons: [
            {
              text: _t("Copy"),
              classes: "btn-primary",
              close: false,
              click: async function () {
                var text = $("#link").text();
                if (navigator.clipboard) {
                  await navigator.clipboard.writeText(text);
                  self.notification.add("Copied Successfully", {
                    title: "Copy Embed Link",
                    type: "info",
                    sticky: false,
                  });
                } else {
                  self.notification.add(
                    "Opps! Enable to copy the text. It seems you are using insecure contexts. Use HTTPS instead of HTTP OR copy text manually",
                    {
                      title: "Copy Embed Link",
                      type: "info",
                      sticky: false,
                    }
                  );
                }
              },
            },
            {
              text: _t("Close"),
              classes: "btn-primary",
              close: true,
            },
          ],
        });
        dialog.open();
      });
  }
  // ----------------------------------------------------------------
  // Dashboard setting events
  onClickEditDasboard(ev) {
    this.action.doAction({
      name: _t("Edit Dashboard"),
      context: { create: false },
      type: "ir.actions.act_window",
      res_model: "dashboard.bits",
      res_id: this.state.dashboard_id,
      flags: { mode: "edit" },
      views: [[false, "form"]],
      target: "new",
    });
  }
  onClickAddDasboardFilter(ev) {
    this.action.doAction({
      name: _t("New Filter"),
      context: { create: false },
      type: "ir.actions.act_window",
      res_model: "dashboard.filter.bits",
      flags: { mode: "edit" },
      views: [[false, "form"]],
      target: "new",
      context: {
        dashboard_id: this.state.dashboard_id || false,
      },
    });
  }
  onClickAddDasboardTheme(ev) {
    this.action.doAction({
      name: _t("New Theme"),
      context: { create: false },
      type: "ir.actions.act_window",
      res_model: "dashboard.themes",
      flags: { mode: "edit" },
      views: [[false, "form"]],
      target: "new",
      context: {
        dashboard_id: this.state.dashboard_id || false,
      },
    });
  }
  async onClickDupDasboard() {
    const res = await this.orm.call(
      "dashboard.bits",
      "duplicate_dashboard",
      [this.state.dashboard_id],
      { context: this.prepareContex() }
    );
    if (res) {
      this.action.doAction(res);
    }
  }
  async onClickImpDasboard(e) {
    this.action.doAction({
      type: "ir.actions.act_window",
      res_model: "import.dashboard",
      view_mode: "form",
      views: [[false, "form"]],
      target: "new",
    });
  }
  async onClickExpDasboard(e) {
    var rec_id = $(e.target).parents(".grid-stack-item").data("stack-id");
    const res = await this.rpc("/export/dashboard", {
      dashboard_id: this.state.dashboard_id,
    });
    this.action.doAction(res);
  }
  async onClickImpItemDasboard(e) {
    this.action.doAction({
      type: "ir.actions.act_window",
      res_model: "import.dashboard.item",
      view_mode: "form",
      context: { dashboard_id: this.state.dashboard_id },
      views: [[false, "form"]],
      target: "new",
    });
  }
  onClickRemoveDasboard() {
    var self = this;
    var $content = $(renderToElement("ConfirmDeleteDashboardDialog"));
    var dialog = new Dialog(this, {
      title: _t("Delete Dashboard"),
      $content: $content,
      size: "medium",
      buttons: [
        {
          text: _t("Delete"),
          classes: "btn-primary",
          close: true,
          click: async function () {
            self.orm
              .call("dashboard.bits", "unlink", [self.state.dashboard_id])
              .then((res) => {
                self.action.doAction(
                  "analytix_dashboard_bits.action_dashboards_view_bits"
                );
              });
          },
        },
        {
          text: _t("Close"),
          classes: "btn-secondary",
          close: true,
        },
      ],
    });

    dialog.open();
  }

  onStartDatechanged(ev) {
    this.state.from_date = ev;
  }

  onEndDatechanged(ev) {
    this.state.to_date = ev;
  }
}

DashboardControllerBits.template = "DashboardControllerBits";
DashboardControllerBits.components = {
  View,
  Dropdown,
  DropdownItem,
  DateTimeInput,
};
registry.category("actions").add("bits_dashboard_action", DashboardControllerBits);
