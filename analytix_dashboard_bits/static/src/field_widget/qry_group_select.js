/** @odoo-module **/

import { Component, onWillStart, useEffect, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { archParseBoolean } from "@web/views/utils";
import { _t } from "@web/core/l10n/translation";

export class XAxis extends Component {
  setup() {
    super.setup();
    this.state = useState({ chart_groups: {} });
    onWillStart(async () => {
      this.onrender();  
    });

    useEffect(() => {
      this.onrender();
    })
  }

  async onrender() {
    const record = this.props.record.data;
    if (record.res_query_bits) {
      let data;
      try {
        data = JSON.parse(record.res_query_bits);
      } catch (err) {
        data = {};
      }
      if (data.fields.length) {
        this.generate_xaxis_strings(this.props);
      }
    }
  }

  onChange(ev) {
    this.props.record.update({[this.props.name]: ev.target.value});
    this.onrender();
  }
  generate_xaxis_strings(props) {
    var self = this;
    self.state.chart_groups = {};
    var query_result = JSON.parse(props.record.data.res_query_bits);
    if (props.name === "y_axis") {
      query_result.fields.forEach(function (key) {
        if (key.type === "numeric") {
          var name =
            key.name.charAt(0).toUpperCase() +
            key.name.replaceAll("_", " ").slice(1);
          self.state.chart_groups[key.name] = name;
        }
      });
    } else {
      query_result.fields.forEach(function (key) {
        self.state.chart_groups[key.name] = key.name.replace("_", " ");
      });
    }
  }
}

XAxis.template = "XaxisBits";

export const xAxis = {
  component: XAxis,
  displayName: _t("X Axis"),
  supportedTypes: ["char"],
  extractProps: ({ attrs, options }) => ({
      isPassword: archParseBoolean(attrs.password),
      dynamicPlaceholder: options.dynamic_placeholder || false,
      dynamicPlaceholderModelReferenceField:
          options.dynamic_placeholder_model_reference_field || "",
      autocomplete: attrs.autocomplete,
      placeholder: attrs.placeholder,
  }),
};

registry.category("fields").add("x_axis_bits", xAxis);