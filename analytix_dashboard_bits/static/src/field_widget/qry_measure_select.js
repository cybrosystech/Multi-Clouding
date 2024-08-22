/** @odoo-module **/

import { Component, onWillStart, useEffect, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { TagsList } from "@web/core/tags_list/tags_list";
import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { archParseBoolean } from "@web/views/utils";
import { _t } from "@web/core/l10n/translation";

export class YAxis extends Component {
  setup() {
    super.setup();
    this.state = useState({
      chart_groups: {},
      isUlAvailable: "",
      sources: [{ options: [] }],
    });
    onWillStart(async () => {
      await this.onRender();
    });

    useEffect(() => {
      this.onRender();
    })
  }

  async onRender() {
    const record = this.props.record.data;
    if (record.res_query_bits) {
      let data;
      try {
        data = JSON.parse(record.res_query_bits);
      } catch (err) {
        data = {};
      }
      if (data.fields.length) {
        this.generate_yaxis_strings(this.props);
      }
    } else {
    }
  }

  getTagProps(record) {
    return {
      id: record.id,
      text: record.text,
      colorIndex: 0,
      onDelete: !this.props.readonly
        ? () => this.deleteTag(record.id)
        : undefined,
      onKeydown: () => {},
    };
  }

  get tags() {
    try {
      const value = JSON.parse(this.props.record.data[this.props.name]);
      const arr = Object.entries(value).map((ele) => {
        return { id: ele[0], text: ele[1] };
      });
      return arr.map((record) => this.getTagProps(record));
    } catch (err) {
      return [];
    }
  }

  generate_yaxis_strings(props) {
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
        } else if(props.record.data.item_type == "list_view" && key.type === "string") {
          var name =
            key.name.charAt(0).toUpperCase() +
            key.name.replaceAll("_", " ").slice(1);
          self.state.chart_groups[key.name] = name;
        }
      });
    }
    if (props.value) {
      const val = JSON.parse(props.value);
      Object.keys(val).map((ele) => {
        delete self.state.chart_groups[ele];
      });
    }
    try {
      const arr = Object.entries(this.state.chart_groups).map((ele) => {
        return { value: ele[0], label: ele[1] };
      });
      this.state.sources[0].options = arr;
    } catch (err) {
      this.state.sources.options = [];
    }
  }

  deleteTag(record) {
    const newJson = JSON.parse(this.props.record.data[this.props.name]);
    delete newJson[record];
    this.props.record.update({[this.props.name]:JSON.stringify(newJson)});
  }

  onSelect(ev) {
    if (ev.value == -1) return;
    if (this.props.record.data[this.props.name].length == 0) {
      const d = {};
      d[ev.value] = ev.label;
      this.props.record.update({[this.props.name]:JSON.stringify(d)});
    } else {
      let newJson = JSON.parse(this.props.record.data[this.props.name]);
      newJson[ev.value] = ev.label;
      this.props.record.update({[this.props.name]:JSON.stringify(newJson)});
    }
  }
}

YAxis.template = "YaxisBits";
YAxis.components = { TagsList, AutoComplete };

export const yAxis = {
  component: YAxis,
  displayName: _t("Y Axis"),
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

registry.category("fields").add("y_axis_bits", yAxis);
