$(document).ready(function () {
  var data = $(".grid-stack-bits").data();
  var base_url = window.location.origin;
  var dashboard_data = {};
  var Grid = false;
  QWeb.add_template(
    "/analytix_dashboard_bits/static/src/xml/statistics_items_bits.xml"
  );
  QWeb.add_template(
    "/analytix_dashboard_bits/static/src/xml/kpi_items_bits.xml"
  );
  QWeb.add_template(
    "/analytix_dashboard_bits/static/src/xml/listview_items_bits.xml"
  );
  $.ajax({
    type: "POST",
    dataType: "json",
    url: base_url + "/dashboard/" + data.dashboard_id + "/data",
    contentType: "application/json; charset=utf-8",
    data: JSON.stringify({ jsonrpc: "2.0", method: "call", params: data }),
    success: function (data) {
      dashboard_data = data.result;
      load_dashboard(data.result);
    },
    error: function (data) {},
  });
  function load_dashboard(result) {
    var visual_options = {
      staticGrid: true,
      float: false,
      styleInHead: true,
      cellHeight: 100,
      verticalMargin: 8,
    };
    var $gridstackContainer = $(".grid-items-container-bits .grid-stack");
    Grid = GridStack.init(visual_options, $gridstackContainer[0]);
    if (result.default_view_mode && result.default_view_mode == "dark") {
      $(".o_content.embed").addClass("dark_mode_bits");
    } else {
      $(".o_content.embed").removeClass("dark_mode_bits");
    }
    render_visuals(result.dashboard_items, result.grid_config);
  }
  function render_visuals(items, config) {
    var grid_config = JSON.parse(config);
    if (!grid_config) {
      grid_config = {};
    }
    Object.keys(items).forEach((key) => {
      var ItemElement;
      const item = items[key];
      if (!item.display_type) {
        return;
      }
      if (
        _.contains(
          ["statistics", "statistics_with_trend_bits"],
          item.display_type
        )
      ) {
        render_statistics(item, grid_config);
      } else if (_.contains(["kpi"], item.display_type)) {
        render_kpi_view(item, grid_config);
      } else if (_.contains(["list_view"], item.display_type)) {
        render_list_view(item, grid_config);
      } else if (_.contains(["map"], item.display_type)) {
        render_map_view(item, grid_config);
      } else if (_.contains(["default_base_view"], item.display_type)) {
        return;
      } else {
        render_chart_view(item, grid_config);
      }
    });
    // for s style 9
    var style_9 = $(".statistics-container.style_9");
    _.each(style_9, function (elem) {
      var bgcolor = $(elem).data("color");
      if (bgcolor) {
        $(elem).attr(
          "style",
          "background:radial-gradient(circle at right top," +
            bgcolor +
            " 0%, #ffffff 20%, #ffffff 100%);"
        );
      }
    });
    // var bgcolor = $('.statistics-container.style_9').attr('style').split(':')[1];
    // $('.statistics-container.st yle_9').css({
    //     "style":"background:radial-gradient(circle at right top,"+ bgcolor +" 0%, #ffffff 20%, #ffffff 100%);"
    // })

    $(".btn-pager").click(function (e) {
      var $target = $(e.currentTarget);
      var target_event = $target.data("event");
      var curr_list = $target
        .parent()
        .find(".records-count-bits")
        .data("count");
      var item_id = parseInt($target.data("itemid"));
      var model = $target.data("model");
      var $item = $target.parents(".grid-stack-item-content");
      this.page;
      var order_by = $target;
      $.ajax({
        type: "POST",
        dataType: "json",
        url: base_url + "/get/" + item_id + "/list",
        contentType: "application/json; charset=utf-8",
        data: JSON.stringify({
          jsonrpc: "2.0",
          method: "call",
          params: {
            model: model,
            target_event: target_event,
            curr_list: curr_list,
            order_by: order_by,
            dashboard_id: dashboard_data.dashboard_id,
          },
        }),
        success: function (data) {
          var result = data.result;
          var list_items = QWeb.render("MoreItemsBits", {
            item: result,
            isArray: (obj) => Array.isArray(obj),
          });
          $item.find("#list_body").empty().append(list_items);
          $target.parent().find(".records-count-bits").data().count =
            result.curr_list;
          $target
            .parent()
            .find(".records-count-bits")
            .html(result.list_numbers);

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
        },
        error: function (data) {},
      });
    });
    $(".sortable-itlems-list").click(function (e) {
      var $current = $(e.currentTarget);
      var index = $current.index();
      var rows = [];
      var thClass = $current.hasClass("asc") ? "desc" : "asc";
      $current.parent().find("th").removeClass("asc desc");
      $current.addClass(thClass);
      $(e.currentTarget)
        .parents("table")
        .find("tbody tr")
        .each(function (index, row) {
          rows.push($(row).detach());
        });

      rows.sort(function (a, b) {
        var aValue = $(a).find("td").eq(index).text();
        var bValue = $(b).find("td").eq(index).text();
        return aValue > bValue ? 1 : aValue < bValue ? -1 : 0;
      });

      if ($current.hasClass("desc")) {
        rows.reverse();
      }
      $.each(rows, function (index, row) {
        $(e.currentTarget).parents("table").find("tbody").append(row);
      });
    });
  }
  function render_statistics(item, grid_config) { 
    if (!item.item_data.statistics_with_trend) {
      if (!item.statistics_data || !item.display_type) {
        return;
      }
      var ItemElement = $(
        QWeb.render("StatisticsItemBits", {
          item: item,
        })
      );
      $(ItemElement)
        .find(".grid-stack-item-content")
        .prepend(this.$item_header);
      // ----------------------------------------------------------------
      // Statistics item
      // ----------------------------------------------------------------
      if (item.item_data.id in grid_config) {
        Grid.addWidget(ItemElement[0], {
          id: item.item_data.id,
          x: grid_config[item.item_data.id]["x"],
          y: grid_config[item.item_data.id]["y"],
          w: grid_config[item.item_data.id]["w"],
          h: grid_config[item.item_data.id]["h"],
          autoPosition: grid_config[item.item_data.id]["autoPosition"],
          minW: grid_config[item.item_data.id]["minW"],
          maxW: grid_config[item.item_data.id]["maxW"],
          minH: grid_config[item.item_data.id]["minH"],
          maxH: grid_config[item.item_data.id]["maxH"],
        });
      } else {
        Grid.addWidget(ItemElement[0], {
          id: item.item_data.id,
          x: 0,
          y: 0,
          w: 4,
          h: 2,
          autoPosition: true,
          minW: 2,
          maxW: null,
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
        QWeb.render("StatisticsItem_WithTrendbits", {
          item: item["item_data"],
          botton_vals: item["bottom_values"],
          statistics_data: item["statistics_data"],
          trend_display_style: item["trend_display_style"],
          trend_primary_color: item["trend_primary_color"],
          apply_background: item["apply_background"],
        })
      );
      // ItemElement.find(".grid-stack-item-content").prepend(this.$item_header);
      if (item.item_data.id in grid_config) {
        Grid.addWidget(ItemElement[0], {
          id: item.item_data.id,
          x: grid_config[item.item_data.id]["x"],
          y: grid_config[item.item_data.id]["y"],
          w: grid_config[item.item_data.id]["w"],
          h: grid_config[item.item_data.id]["h"],
          autoPosition: grid_config[item.item_data.id]["autoPosition"],
          minW: 2,
          maxW: null,
          minH: item.item_data.trend_display_style == "style_3" ? 1 : 2,
          maxH: 3,
        });
      } else {
        Grid.addWidget(ItemElement[0], {
          id: item.item_data.id,
          x: 0,
          y: 0,
          w: 4,
          h: 3,
          autoPosition: true,
          minW: 2,
          maxW: null,
          minH: 2,
          maxH: 4,
        });
      }
      var ctx = $("#" + item.item_data.id + "_" + item.item_data.item_type)[0];
      if (item.center_values_options) {
        if (item.item_data.trend_display_style == "style_1") {
          var Chart = echarts.init(ctx, null, {
            height: 130,
          });
        } else {
          var Chart = echarts.init(ctx);
        }
        if (item.center_values_options && item.center_values_options.options) {
          Chart.setOption(item.center_values_options.options);
          // this.charts.push(Chart);
        }
      }
    }
  }
  function render_kpi_view(item, config) {
    var ItemElement = $(
      QWeb.render("KpiItemsBits", {
        item: item["item_data"],
        kpi_config: item["kpi_config"],
      })
    );
    // $(ItemElement).find(".grid-stack-item-content").prepend($item_header);
    if (item.item_data.id in config) {
      Grid.addWidget(ItemElement[0], {
        id: item.item_data.id,
        x: config[item.item_data.id]["x"],
        y: config[item.item_data.id]["y"],
        w: config[item.item_data.id]["w"],
        h: config[item.item_data.id]["h"],
        autoPosition: config[item.item_data.id]["autoPosition"],
        minW: 2,
        maxW: null,
        minH: config[item.item_data.id]["minh"],
        maxH: 3,
      });
    } else {
      Grid.addWidget(ItemElement[0], {
        id: item.item_data.id,
        x: 0,
        y: 0,
        w: 3,
        h: 2,
        autoPosition: true,
        minW: 2,
        maxW: null,
        minH: 2,
        maxH: 2,
      });
    }
    var ctx = $("#" + item.item_data.id + "_" + item.item_data.item_type)[0];
    if (item.kpi_config.kpi_display_style == "style_3") {
      init_kpi_s3(ItemElement);
    } else {
      var Chart = echarts.init(ctx, null, {
        width: 175,
        height: 175,
      });
      Chart.setOption(item.kpi_config.progress_chart_options);
    }
  }
  function init_kpi_s3(element) {
    var $progress = element.find(".progress-per");
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
  function render_list_view(item, grid_config) {
    if (!item.list_view_data) {
      return;
    }
    var ItemElement = $(
      QWeb.render("list_view_item_bits", {
        item: item,
        isArray: (obj) => Array.isArray(obj),
      })
    );
    // ItemElement.find(".grid-stack-item-content").prepend($item_header);
    if (item.item_data.id in grid_config) {
      Grid.addWidget(ItemElement[0], {
        id: item.item_data.id,
        x: grid_config[item.item_data.id]["x"],
        y: grid_config[item.item_data.id]["y"],
        w: grid_config[item.item_data.id]["w"],
        h: grid_config[item.item_data.id]["h"],
      });
    } else {
      Grid.addWidget(ItemElement[0], {
        id: item.item_data.id,
        x: 0,
        y: 0,
        w: 4,
        h: 4,
        autoPosition: true,
        minW: 2,
        maxW: 12,
        minH: 2,
        maxH: 12,
      });
    }
  }
  function render_map_view() {}
  function render_chart_view(item, grid_config) {
    var ItemElement =
      `<div class="echart-item grid-stack-item gsi_` +
      item.item_data.id +
      `" data-stack-id="` +
      item.item_data.id +
      `">
                                <div class="` +
      item.item_data.item_type +
      ` grid-stack-item-content shadow"
                                    id="` +
      item.item_data.id +
      `_` +
      item.item_data.item_type +
      `">
                                </div>
                            </div>`;

    if (item.item_data.id in grid_config) {
      Grid.addWidget(ItemElement, {
        id: item.item_data.id,
        x: grid_config[item.item_data.id]["x"],
        y: grid_config[item.item_data.id]["y"],
        w: grid_config[item.item_data.id]["w"],
        h: grid_config[item.item_data.id]["h"],
      });
    } else {
      Grid.addWidget(ItemElement, {
        id: item.item_data.id,
        x: 0,
        y: 0,
        w: 4,
        h: 3,
        autoPosition: true,
        minW: 2,
        maxW: 5,
        minH: 2,
        maxH: 5,
      });
    }
    var ctx = $("#" + item.item_data.id + "_" + item.item_data.item_type)[0];
    var Chart = echarts.init(ctx, dashboard_data.default_view_mode);
    // ItemElement.find(".grid-stack-item-content").prepend(this.$item_header);
    try {
      Chart.setOption(item.options);
    } catch (e) {
      $(".grid-stack-item-content > div")[1].remove();
      $(".grid-stack-item-content").append("<div/>");
    }
  }
  function render_view(dashboard_view, grid_config = {}) {
    let $PreviewBord = $(
      QWeb.render("custom_view_bits", { node: dashboard_view })
    );
    $PreviewBord.find(".grid-stack-item-content").prepend(this.$item_header);
    if (dashboard_view.id in grid_config) {
      this.Grid.addWidget($PreviewBord[0], {
        id: dashboard_view.id,
        x: grid_config[dashboard_view.id].x,
        y: grid_config[dashboard_view.id].y,
        w: grid_config[dashboard_view.id].w,
        h: grid_config[dashboard_view.id].h,
        autoPosition: true,
        minW: grid_config[dashboard_view.id].minW,
        maxW: grid_config[dashboard_view.id].maxW,
        minH: grid_config[dashboard_view.id].minH,
        maxH: grid_config[dashboard_view.id].maxH,
      });
    } else {
      this.Grid.addWidget($PreviewBord[0], {
        id: dashboard_view.id,
        x: 0,
        y: 0,
        w: 4,
        h: 3,
        autoPosition: true,
        minW: 2,
        maxW: 5,
        minH: 2,
        maxH: 5,
      });
    }
    _createController({
      $node: $PreviewBord.find(
        `.oe_action[data-id=action_${dashboard_view.action_id}_${dashboard_view.id}] .oe_content`
      ),
      actionID: dashboard_view.action_id,
      context: dashboard_view.context_to_save,
      domain: Domain.prototype.stringToArray(dashboard_view.domain, {}),
      viewType: dashboard_view.view_mode,
    });
  }
  async function _createController(params) {
    var self = this;
    var action = {};
    await $.ajax({
      type: "POST",
      dataType: "json",
      url: base_url + "/web/action/load",
      contentType: "application/json; charset=utf-8",
      data: JSON.stringify({
        jsonrpc: "2.0",
        method: "call",
        params: {
          action_id: params.actionID,
        },
      }),
      success: function (data) {
        action = data;
      },
    });
    if (!action) {
      // the action does not exist anymore
      return $(
        '<h2 class="error-text text-center" style="margin-top: 20px">Action not found.</h2>'
      ).appendTo(params.$node);
    }
    var evalContext = new Context(session.user_context, params.context).eval();
    if (evalContext.group_by && evalContext.group_by.length === 0) {
      delete evalContext.group_by;
    }
    // tz and lang are saved in the custom view
    // override the language to take the current one
    var rawContext = new Context(action.context, evalContext, {
      lang: session.user_context.lang,
    });
    var context = pyUtils.eval("context", rawContext, evalContext);
    var domain =
      params.domain ||
      pyUtils.eval("domain", action.domain || "[]", action.context);

    action.context = context;
    action.domain = domain;
    // When creating a view, `action.views` is expected to be an array of dicts, while
    // '/web/action/load' returns an array of arrays.
    action._views = action.views;
    action.views = $.map(action.views, function (view) {
      return { viewID: view[0], type: view[1] };
    });

    var viewType = params.viewType || action._views[0][1];
    var view = _.find(action._views, function (descr) {
      return descr[1] === viewType;
    }) || [false, viewType];
    const viewsInfo = await self.loadViews(action.res_model, context, [view]);
    var viewInfo = viewsInfo[viewType];
    var xml = new DOMParser().parseFromString(viewInfo.arch, "text/xml");
    var key = xml.documentElement.getAttribute("js_class");
    var View = viewRegistry.get(key || viewType);

    const searchQuery = {
      context: context,
      domain: domain,
      groupBy:
        typeof context.group_by === "string" && context.group_by
          ? [context.group_by]
          : context.group_by || [],
      orderedBy: context.orderedBy || [],
    };

    if (View.prototype.searchMenuTypes.includes("comparison")) {
      searchQuery.timeRanges = context.comparison || {};
    }

    var view = new View(viewInfo, {
      action: action,
      hasSelectors: false,
      modelName: action.res_model,
      searchQuery,
      withControlPanel: false,
      withSearchPanel: false,
    });
    const controller = await view.getController(self);
    return controller.appendTo(params.$node);
  }
});
