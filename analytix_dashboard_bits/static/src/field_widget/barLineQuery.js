odoo.define("analytix_dashboard_bits.barLineQuery", function (require) {
  var registry = require("web.field_registry");
  var AbstractField = require("web.AbstractField");
  var core = require("web.core");
  var QWeb = core.qweb;
  var BarLineQuery = AbstractField.extend({
    resetOnAnyFieldChange: true,
    supportedFieldTypes: ["char"],
    events: _.extend({}, AbstractField.prototype.events, {
      "click .o_delete_measure": "onRemoveMeasure",
      "click .o_measure_selector": "onFocusedMeasure",
      "click .measure_item": "onAddMeasure",
    }),
    init: function () {
      this.chart_measures = "";
      this._super.apply(this, arguments);
    },
    _render: function () {
      var self = this;
      self.$el.empty();
      var field = self.recordData;
      if (field.y_axis) {
        if (!this.value) {
          var y_axis = JSON.parse(field.y_axis);
          if (Object.keys(y_axis).length) {
            if (
              field.item_type !== "list_view" &&
              field.item_type !== "kpi" &&
              field.item_type !== "statistics"
            ) {
              self.generate_yaxis_strings();
              var $yaxis = $(
                QWeb.render("YaxisBits", {
                  measure_list: {},
                  mode: self.mode,
                })
              );
              self.$el.append($yaxis);
              // if (this.mode == 'edit') self.set_measure_value();
            }
          } else {
            this.$el.append("Data is missing");
          }
        } else {
          self.generate_yaxis_strings();
          var measure_values = JSON.parse(this.value);
          var $yaxis = $(
            QWeb.render("YaxisBits", {
              measure_list: measure_values,
              mode: self.mode,
            })
          );
          self.$el.append($yaxis);
        }
      } else {
        this._setValue("");
        this.$el.append("Invalid query string");
      }
    },
    generate_yaxis_strings: function () {
      var self = this;
      self.chart_measures = {};
      try {
        self.chart_measures = JSON.parse(self.recordData.y_axis);
        const value = JSON.parse(this.value);
        let newVal = {};
        Object.keys(value).forEach((ele) => {
          if (Object.keys(self.chart_measures).includes(ele)) {
            newVal[ele] = self.chart_measures[ele];
          }
        });
        this._setValue(JSON.stringify(newVal));
      } catch (err) {}
      // if (self.name === "y_axis"){
      //     query_result.fields.forEach(function(key){
      //         if(key.type === "numeric") {
      //             var name = key.name.charAt(0).toUpperCase() + key.name.replaceAll('_',' ').slice(1);
      //             self.chart_measures[key.name] = name;
      //         }
      //     });
      // }
    },

    // set_measure_value: function(e){
    //     var value = JSON.stringify(this.chart_measures);
    //     this._setValue(value);
    // },
    onRemoveMeasure: function (ev) {
      var item_to_remove = $(ev.currentTarget).data("measure");
      var value = JSON.parse(this.value);
      delete value[item_to_remove];
      this._setValue(JSON.stringify(value));
    },
    onFocusedMeasure: function (ev) {
      var self = this;
      this.generate_yaxis_strings();
      var curr_vals = this.value ? JSON.parse(this.value) : {};
      var measures_to_select = this.chart_measures;
      if (curr_vals) {
        measures_to_select = {};
        Object.keys(this.chart_measures).forEach(function (key) {
          if (!_.contains(Object.keys(curr_vals), key)) {
            measures_to_select[key] = self.chart_measures[key];
          }
        });
      }
      var $dropdownview = $(
        QWeb.render("MeasureItems", {
          measure_list: measures_to_select,
        })
      );
      $(".o_measure_items").html($dropdownview);
    },
    onAddMeasure: function (ev) {
      var $target = $(ev.currentTarget);
      var measure = $target.data("measure");
      var value = {};
      try {
        value = JSON.parse(this.value);
      } catch (err) {}
      value[measure] = $target.html();
      this._setValue(JSON.stringify(value));
    },
  });
  registry.add("bar_line_query", BarLineQuery);
  return BarLineQuery;
});
